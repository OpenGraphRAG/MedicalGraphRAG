import pandas as pd
from py2neo import Graph, Node, Relationship, NodeMatcher
import re
import unicodedata
import time

# Neo4j connection details
NEO4J_URI = "bolt://39.97.41.99:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "neo4j123"
EXCEL_FILE = r"Z:\MedicalGraphRAG_prod\data_process\output_plus1.xlsx"


def connect_to_neo4j():
    """Connect to Neo4j with timeout to prevent hanging"""
    try:
        # 关键修复：添加超时参数，防止无限等待
        graph = Graph(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD), connection_timeout=30)
        # 测试连接
        graph.run("MATCH (n) RETURN n LIMIT 1")
        print("Successfully connected to Neo4j.")
        return graph
    except Exception as e:
        print(f"Failed to connect to Neo4j: {e}")
        return None


def sanitize_label(raw_label):
    """将CID值转换为合法的Neo4j标签"""
    if pd.isna(raw_label) or raw_label is None:
        return None

    label = str(raw_label)
    label = unicodedata.normalize('NFKC', label)
    label = ''.join(ch for ch in label if unicodedata.category(ch)[0] != 'C')
    label = re.sub(r'[\s\.,;:!?@#$%^&*()\-+=\[\]{}|<>/\\]', '_', label)
    label = re.sub(r'_+', '_', label)
    label = label.strip('_')

    if not label:
        return None

    if label[0].isdigit():
        label = f"N_{label}"

    return label[:500]


def force_drop_all_constraints_and_indexes(graph):
    """
    强制删除所有约束和索引（修复：先获取所有再逐个删除）
    这是最关键的一步，必须确保旧约束被清除
    """
    print("\n=== Force Dropping All Constraints and Indexes ===")

    # 删除所有约束（Neo4j 5.x）
    try:
        constraints = list(graph.run("SHOW CONSTRAINTS YIELD name").data())
        for constraint in constraints:
            name = constraint['name']
            try:
                graph.run(f"DROP CONSTRAINT {name}")
                print(f"  ✓ Dropped constraint: {name}")
            except Exception as e:
                print(f"  ⚠ Failed to drop constraint {name}: {e}")
    except Exception as e:
        print(f"Neo4j 5.x constraint drop failed: {e}")
        print("  Trying 4.x fallback...")

        try:
            result = graph.run("CALL db.constraints()").data()
            for record in result:
                name = record['name']
                graph.run(f"DROP CONSTRAINT {name}")
                print(f"  ✓ Dropped 4.x constraint: {name}")
        except Exception as e2:
            print(f"  Fallback failed: {e2}")

    # 删除所有索引（保留系统LOOKUP索引）
    try:
        indexes = list(graph.run("SHOW INDEXES YIELD name, type WHERE type <> 'LOOKUP'").data())
        for index in indexes:
            name = index['name']
            try:
                graph.run(f"DROP INDEX {name}")
                print(f"  ✓ Dropped index: {name}")
            except Exception as e:
                print(f"  ⚠ Failed to drop index {name}: {e}")
    except Exception as e:
        print(f"  Index drop failed: {e}")

    # 等待操作完成
    try:
        graph.run("CALL db.awaitIndexes()")
        print("  ✓ Awaited index completion")
    except:
        pass

    print("  --- All constraints and indexes dropped successfully ---")


def create_temp_constraint(graph):
    """
    创建临时约束（在内部标签上，不污染用户标签）
    关键修复：不在用户提供的标签上创建任何约束
    """
    print("\n=== Creating Temporary Constraint ===")
    try:
        # 在内部标签 :_TempEntity（下划线开头，隐藏）上创建约束
        graph.run("CREATE CONSTRAINT IF NOT EXISTS FOR (n:_TempEntity) REQUIRE n.TID IS UNIQUE")
        print("  ✓ Created unique constraint for TID on :_TempEntity")
    except Exception as e:
        print(f"  ⚠ Constraint creation warning: {e}")
        # 兼容性回退
        try:
            graph.run("CREATE CONSTRAINT ON (n:_TempEntity) ASSERT n.TID IS UNIQUE")
            print("  ✓ Created constraint (4.x syntax)")
        except:
            pass


def verify_database_clean(graph):
    """
    验证数据库是否已清理干净（关键新增）
    如果约束残留，脚本会提前终止并给出明确提示
    """
    print("\n=== Verifying Database Clean Status ===")

    # 检查约束
    try:
        constraints = graph.run("SHOW CONSTRAINTS YIELD name, labelsOrTypes, properties").data()
        if constraints:
            print(f"  ⚠ CRITICAL: Found {len(constraints)} constraints:")
            for c in constraints:
                print(f"    - {c['name']} on :{c['labelsOrTypes'][0]}({c['properties'][0]})")
            print("  → PLEASE RUN MANUAL CLEANUP FIRST!")
            print("  → Neo4j Browser: DROP CONSTRAINT constraint_6639a9cf;")
            return False
        else:
            print("  ✓ No constraints found")
    except Exception as e:
        print(f"  ⚠ Could not verify constraints: {e}")

    # 检查索引
    try:
        indexes = graph.run(
            "SHOW INDEXES YIELD name, type, entityType, labelsOrTypes, properties WHERE type <> 'LOOKUP'").data()
        if indexes:
            print(f"  ⚠ Found {len(indexes)} indexes:")
            for idx in indexes:
                print(f"    - {idx['name']} on :{idx['labelsOrTypes'][0]}({idx['properties'][0]})")
        else:
            print("  ✓ No user indexes found")
    except Exception as e:
        print(f"  ⚠ Could not verify indexes: {e}")

    # 检查节点
    try:
        nodes = graph.run("MATCH (n) RETURN count(n) as count").data()[0]['count']
        print(f"  ✓ Nodes in database: {nodes}")
    except:
        print("  ⚠ Could not count nodes")

    return True


def preprocess_data(df):
    """预处理数据"""
    processed_df = df.copy()

    for col in processed_df.columns:
        processed_df[col] = processed_df[col].apply(
            lambda x: str(int(x)) if pd.notna(x) and isinstance(x, (int, float)) and x == int(x)
            else str(x).strip() if pd.notna(x)
            else ""
        )

    return processed_df


def create_node_with_label(graph, matcher, label, tid, name, original_cid):
    """
    创建节点：动态标签在前（决定颜色），内部标签在后
    修复了标签顺序和约束污染问题
    """
    sanitized_label = sanitize_label(label)

    if not sanitized_label:
        print(f"Warning: Invalid label for '{original_cid}', using 'UnknownEntity'")
        sanitized_label = "UnknownEntity"

    # 查找是否已存在（按TID和内部标签）
    node = matcher.match("_TempEntity", TID=tid).first()

    if not node:
        # 关键修复：动态标签在前，内部标签在后
        # 不在用户标签上创建任何约束
        node = Node(
            sanitized_label,  # 第一位：决定节点颜色
            "_TempEntity",  # 第二位：内部标签，用于约束管理
            TID=tid,
            name=name,
            original_cid=original_cid,
            sanitized_label=sanitized_label
        )

        # 关键修复：添加带超时的错误处理
        try:
            graph.create(node)
        except Exception as e:
            print(f"  ERROR: Failed to create node with TID={tid}: {e}")
            raise  # 重新抛出错误，让上层处理

    return node


def build_knowledge_graph(graph, data):
    """构建知识图谱"""
    matcher = NodeMatcher(graph)
    created_count = 0
    label_stats = {}

    for index, row in data.iterrows():
        try:
            cid_head = str(row["CID_HEAD"]).strip()
            tid = str(row["TID"]).strip()
            t_head = str(row["T_HEAD"]).strip()
            rel = str(row["REL"]).strip()
            relid = str(row["RELID"]).strip()
            cid_tail = str(row["CID_TAIL"]).strip()
            tid_tail = str(row["TID_TAIL"]).strip()
            t_tail = str(row["T_TAIL"]).strip()

            if not tid or not t_head or not rel or not tid_tail or not t_tail:
                print(f"Warning: Missing required data in row {index + 3}, skipping...")
                continue

            head_node = create_node_with_label(graph, matcher, cid_head, tid, t_head, cid_head)
            head_label = sanitize_label(cid_head) or "UnknownEntity"
            label_stats[head_label] = label_stats.get(head_label, 0) + 1

            tail_node = create_node_with_label(graph, matcher, cid_tail, tid_tail, t_tail, cid_tail)
            tail_label = sanitize_label(cid_tail) or "UnknownEntity"
            label_stats[tail_label] = label_stats.get(tail_label, 0) + 1

            relationship = Relationship(
                head_node, rel, tail_node,
                RELID=relid,
                relation_name=rel
            )
            graph.create(relationship)

            created_count += 1
            if created_count % 100 == 0:
                print(f"Progress: {created_count} triples inserted...")

        except Exception as e:
            print(f"\nERROR processing row {index + 3}: {e}")
            print(f"Problematic row data: {dict(row)}")
            print("Stopping import. Please fix the issue and restart.")
            raise  # 停止导入，避免继续出错

    print(f"\nTotal {created_count} triples inserted successfully.")
    print("\nLabel distribution (Top 10):")
    for label, count in sorted(label_stats.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {label}: {count} nodes")

    return label_stats


def load_excel_data(file_path, start_row=0, chunk_size=None):
    """加载Excel数据"""
    try:
        df = pd.read_excel(file_path, header=0, engine='openpyxl')

        required_cols = ["CID_HEAD", "CID_TAIL", "TID", "T_HEAD", "REL", "TID_TAIL", "T_TAIL"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")

        if chunk_size:
            data = df.iloc[start_row:start_row + chunk_size].reset_index(drop=True)
        else:
            data = df.iloc[start_row:].reset_index(drop=True)

        data = preprocess_data(data)
        print(f"Loaded {len(data)} rows from {file_path} (starting at row {start_row + 2})")
        return data

    except Exception as e:
        print(f"Failed to load Excel: {e}")
        return pd.DataFrame()


def main():
    """主函数"""
    print("=" * 60)
    print("Medical Knowledge Graph Construction")
    print("=" * 60)

    graph = connect_to_neo4j()
    if not graph:
        print("ERROR: Cannot connect to Neo4j. Exiting.")
        return

    # 步骤1：验证数据库是否干净（关键修复）
    if not verify_database_clean(graph):
        print("\n❌ DATABASE NOT CLEAN!")
        print("Manual cleanup required:")
        print("  1. Open Neo4j Browser")
        print("  2. Run: DROP CONSTRAINT constraint_6639a9cf;")
        print("  3. Run: MATCH (n) DETACH DELETE n;")
        print("  4. Re-run this script")
        return  # 提前退出，避免后续错误

    # 步骤2：强制清理（双重保险）
    print("\nStep 1: Force cleaning database...")
    force_drop_all_constraints_and_indexes(graph)
    graph.run("MATCH (n) DETACH DELETE n")

    # 步骤3：创建临时约束
    create_temp_constraint(graph)

    # 步骤4：导入数据
    print("\nStep 2: Importing data...")
    batch_size = 500
    start_row = 0

    try:
        while True:
            print(f"\n--- Batch: rows {start_row + 2}-{start_row + batch_size + 1} ---")
            data = load_excel_data(EXCEL_FILE, start_row=start_row, chunk_size=batch_size)

            if data.empty:
                print("No more data to process.")
                break

            build_knowledge_graph(graph, data)

            if len(data) < batch_size:
                break

            start_row += batch_size

            # 批次间短暂暂停，避免过载
            time.sleep(0.1)

    except Exception as e:
        print(f"\n❌ IMPORT FAILED: {e}")
        print("Last batch may be incomplete. Check data consistency.")
        return

    # 步骤5：验证结果
    print("\nStep 3: Verifying results...")

    # 查询标签分布
    result = graph.run("""
        MATCH (n) 
        UNWIND labels(n) as label
        WHERE label <> '_TempEntity'
        RETURN label, count(*) as count
        ORDER BY count DESC
        LIMIT 15
    """).data()

    print("\nTop 15 node labels (should be your CID values):")
    for record in result:
        print(f"  {record['label']}: {record['count']} nodes")

    # 查询示例节点
    result = graph.run("""
        MATCH (n:_TempEntity)
        RETURN n.original_cid as original_cid, 
               labels(n) as labels, 
               n.name as name 
        LIMIT 5
    """).data()

    print("\nSample nodes (original CID vs labels):")
    for record in result:
        print(f"  Original: '{record['original_cid']}' -> Labels: {record['labels']}")

    print("\n" + "=" * 60)
    print("✅ Construction Completed Successfully!")
    print("=" * 60)

    print("\nNOTE: In Neo4j Browser:")
    print("  1. Click 'Node labels' panel on the left")
    print("  2. Click individual labels to see distinct colors")
    print("  3. Run: MATCH (n) RETURN n LIMIT 100 to visualize")


if __name__ == "__main__":
    main()