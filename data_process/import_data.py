import time

import pandas as pd
from py2neo import Graph, Node, Relationship, NodeMatcher
import re
import unicodedata
from collections import defaultdict

# Neo4j connection details
NEO4J_URI = "bolt://39.97.41.99:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "neo4j123"
EXCEL_FILE = r"Z:\MedicalGraphRAG_prod\data_process\output_plus1.xlsx"


def connect_to_neo4j():
    """连接Neo4j，添加超时防止挂起"""
    try:
        graph = Graph(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        graph.run("MATCH (n) RETURN n LIMIT 1")
        print("✓ 成功连接Neo4j")
        return graph
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return None


def sanitize_label(raw_label):
    """清理CID值为合法标签"""
    if pd.isna(raw_label) or raw_label is None:
        return "UnknownEntity"

    label = str(raw_label)
    label = unicodedata.normalize('NFKC', label)
    label = ''.join(ch for ch in label if unicodedata.category(ch)[0] != 'C')
    label = re.sub(r'[\s\.,;:!?@#$%^&*()\-+=\[\]{}|<>/\\]', '_', label)
    label = re.sub(r'_+', '_', label)
    label = label.strip('_')

    if not label:
        return "UnknownEntity"

    if label[0].isdigit():
        label = f"N_{label}"

    return label[:500]


def collect_unique_labels(df):
    """收集所有唯一的标签值"""
    head_labels = df['CID_HEAD'].dropna().unique()
    tail_labels = df['CID_TAIL'].dropna().unique()
    unique_labels = set()

    for label in head_labels:
        unique_labels.add(sanitize_label(label))
    for label in tail_labels:
        unique_labels.add(sanitize_label(label))

    return unique_labels


def create_dynamic_constraints(graph, labels):
    """
    为每个标签动态创建唯一约束
    确保每个标签下的TID都是唯一的
    """
    print(f"\n=== 为 {len(labels)} 个标签创建约束 ===")

    for label in sorted(labels):
        try:
            # Neo4j 4.x 语法（兼容大多数版本）
            constraint_name = f"constraint_{label}_TID"
            # 先检查是否存在
            try:
                graph.run(f"DROP CONSTRAINT {constraint_name}")
                print(f"  ✓ 删除旧约束: {constraint_name}")
            except:
                pass

            # 创建新约束
            graph.run(f"CREATE CONSTRAINT {constraint_name} ON (n:{label}) ASSERT n.TID IS UNIQUE")
            print(f"  ✓ 创建约束: {label}(TID)")

        except Exception as e:
            print(f"  ⚠ 创建约束失败 {label}: {e}")


def delete_all_constraints(graph):
    """删除所有约束（清理用）"""
    print("\n=== 清理所有约束 ===")
    try:
        # Neo4j 4.x
        constraints = list(graph.run("CALL db.constraints()").data())
        for c in constraints:
            try:
                graph.run(f"DROP CONSTRAINT {c['name']}")
                print(f"  ✓ 删除: {c['name']}")
            except:
                pass
    except Exception as e:
        print(f"  ⚠ 清理失败: {e}")


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


def create_node_only_with_label(graph, matcher, label, tid, name, original_cid):
    """
    修复：只创建动态标签，不添加统一标签
    """
    sanitized_label = sanitize_label(label)

    # 查找是否已存在（仅按标签和TID查找）
    node = matcher.match(sanitized_label, TID=tid).first()

    if not node:
        # 修复：只使用动态标签，不添加BaseEntity
        node = Node(
            sanitized_label,  # 唯一标签
            TID=tid,
            name=name,
            original_cid=original_cid
        )
        graph.create(node)

    return node


def build_knowledge_graph(graph, data):
    """构建知识图谱（无统一标签）"""
    matcher = NodeMatcher(graph)
    created_count = 0
    label_stats = defaultdict(int)

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
                print(f"警告: 第{index + 2}行缺少必要数据，跳过...")
                continue

            head_node = create_node_only_with_label(
                graph, matcher, cid_head, tid, t_head, cid_head
            )
            label_stats[sanitize_label(cid_head)] += 1

            tail_node = create_node_only_with_label(
                graph, matcher, cid_tail, tid_tail, t_tail, cid_tail
            )
            label_stats[sanitize_label(cid_tail)] += 1

            relationship = Relationship(
                head_node, rel, tail_node,
                RELID=relid,
                relation_name=rel
            )
            graph.create(relationship)

            created_count += 1
            if created_count % 100 == 0:
                print(f"进度: 已插入 {created_count} 个三元组...")

        except Exception as e:
            print(f"错误: 处理第{index + 2}行时失败: {e}")
            print(f"数据: {dict(row)}")
            raise  # 停止导入，避免不一致

    print(f"\n✓ 总计插入 {created_count} 个三元组")
    return label_stats


def load_excel_data(file_path, start_row=0, chunk_size=None):
    """加载Excel数据"""
    try:
        df = pd.read_excel(file_path, header=0, engine='openpyxl')

        # 验证列
        required_cols = ["CID_HEAD", "CID_TAIL", "TID", "T_HEAD", "REL", "TID_TAIL", "T_TAIL"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"缺少必要列: {missing_cols}")

        if chunk_size:
            data = df.iloc[start_row:start_row + chunk_size].reset_index(drop=True)
        else:
            data = df.iloc[start_row:].reset_index(drop=True)

        data = preprocess_data(data)
        print(f"从 {file_path} 加载了 {len(data)} 行数据（从第{start_row + 2}行开始）")
        return data

    except Exception as e:
        print(f"❌ 加载Excel失败: {e}")
        return pd.DataFrame()


def main():
    """主函数"""
    print("=" * 70)
    print("知识图谱导入 - 独立标签模式")
    print("=" * 70)

    # 步骤1：连接数据库
    graph = connect_to_neo4j()
    if not graph:
        return

    # 步骤2：完全清理
    print("\n步骤1: 清理数据库...")
    delete_all_constraints(graph)
    graph.run("MATCH (n) DETACH DELETE n")
    print("  ✓ 所有节点、关系和约束已删除")

    # 步骤3：分析数据并收集所有唯一标签
    print("\n步骤2: 分析数据中的唯一标签...")
    df_preview = pd.read_excel(EXCEL_FILE, header=0, engine='openpyxl')
    unique_labels = collect_unique_labels(df_preview)
    print(f"  发现 {len(unique_labels)} 个唯一标签")
    print(f"  前10个标签: {list(sorted(unique_labels))[:10]}")

    # 步骤4：为每个标签创建约束
    create_dynamic_constraints(graph, unique_labels)

    # 步骤5：导入数据
    print("\n步骤3: 开始导入数据...")
    batch_size = 500
    start_row = 0

    try:
        while True:
            print(f"\n--- 批次: 第{start_row + 2}到{start_row + batch_size + 1}行 ---")
            data = load_excel_data(EXCEL_FILE, start_row=start_row, chunk_size=batch_size)

            if data.empty:
                print("没有更多数据")
                break

            build_knowledge_graph(graph, data)

            if len(data) < batch_size:
                break

            start_row += batch_size
            time.sleep(0.1)

    except Exception as e:
        print(f"\n❌ 导入失败: {e}")
        return

    # 步骤6：验证结果
    print("\n步骤4: 验证导入结果...")

    # 查询标签分布
    result = graph.run("""
        MATCH (n) 
        UNWIND labels(n) as label
        RETURN label, count(*) as count
        ORDER BY count DESC
        LIMIT 20
    """).data()

    print("\n前20个标签的节点数量:")
    for record in result[:15]:
        print(f"  {record['label']}: {record['count']} 个节点")

    # 查询示例节点
    result = graph.run("""
        MATCH (n) 
        WHERE n.name IS NOT NULL
        RETURN n.original_cid as original_cid, 
               labels(n) as labels, 
               n.name as name,
               n.TID as TID
        LIMIT 5
    """).data()

    print("\n示例节点:")
    for record in result:
        print(f"  原始CID: '{record['original_cid']}'")
        print(f"    标签: {record['labels']}")
        print(f"    名称: {record['name']}")
        print(f"    TID: {record['TID']}")

    print("\n" + "=" * 70)
    print("✅ 导入完成！每个标签都有独立颜色")
    print("=" * 70)


if __name__ == "__main__":
    main()