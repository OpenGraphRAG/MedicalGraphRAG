from typing import Optional
from tqdm import tqdm
import numpy as np
import json
import os
import re
import time
import pickle
from config import config
from neo4j import GraphDatabase, basic_auth
from string import Template
from typing import Dict, List, Any
from openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.neighbors import NearestNeighbors
from pyvis.network import Network


class KnowledgeGraphManager:
    def __init__(self, ann_leaf_size: int = 30):
        self.vector_index_file = config.KNOWLEDGE_INDEX
        self.embedding_batch_size = 20
        self.similarity_threshold = 0.7
        self.top_k = 5
        self.ann_leaf_size = ann_leaf_size
        self.entity_cache, self.embeddings_cache = {}, {}
        self.vector_index = self._init_vector_index()
        self.driver = self._init_graph_db()
        self.kg_schema = self._load_kg_schema()
        self.openai_client = OpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY", config.TONGYI_KEY),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        self.ann_models = {"entities": None, "relationships": None}
        if self.driver and self.is_first_run:
            self._create_vector_index()
            self.build_vector_index_from_neo4j()
            self.build_ann_models()
            self._save_vector_index()
        elif self.driver and not self.is_first_run:
            self.build_ann_models()

    def _init_vector_index(self) -> Dict:
        """
        初始化向量索引结构
        尝试从文件加载，如果不存在则创建新的
        """
        # 默认向量索引结构
        default_index = {
            "entities": {
                "ids": [],  # 实体ID列表
                "names": [],  # 实体名称列表
                "types": [],  # 实体类型列表
                "embeddings": np.empty((0, 1536))  # 实体嵌入向量矩阵
            },
            "relationships": {
                "ids": [],  # 关系ID列表
                "types": [],  # 关系类型列表
                "sources": [],  # 源实体名称列表
                "targets": [],  # 目标实体名称列表
                "embeddings": np.empty((0, 1536))  # 关系嵌入向量矩阵
            }
        }

        # 标记是否为首次运行（初始值为True）
        self.is_first_run = True

        try:
            # 检查向量索引文件是否存在
            if os.path.exists(self.vector_index_file):
                print(f"🔍 找到向量索引文件: {self.vector_index_file}")
                with open(self.vector_index_file, "rb") as f:
                    index_data = pickle.load(f)

                    # 检查索引结构是否有效
                    if ("entities" in index_data and "relationships" in index_data and
                            "ids" in index_data["entities"] and "embeddings" in index_data["entities"] and
                            "ids" in index_data["relationships"] and "embeddings" in index_data["relationships"]):
                        print(f"✅ 成功加载向量索引")
                        self.is_first_run = False  # 标记为非首次运行
                        return index_data
                    else:
                        print("⚠️ 索引文件结构无效，使用默认索引")
            else:
                print("⚠️ 未找到向量索引文件，使用默认索引")
        except Exception as e:
            print(f"❌ 加载向量索引失败: {e}, 使用默认索引")

        # 如果是首次运行，使用默认索引
        return default_index

    def _save_vector_index(self):
        """保存向量索引到文件"""
        try:
            with open(self.vector_index_file, "wb") as f:
                pickle.dump(self.vector_index, f)
            print(f"💾 向量索引已保存至: {self.vector_index_file}")
        except Exception as e:
            print(f"❌ 保存向量索引失败: {e}")

    def _init_graph_db(self) -> Optional[Any]:
        """
        初始化图数据库连接

        返回:
            Neo4j驱动对象或None（如果连接失败）
        """
        try:
            # 创建数据库驱动
            driver = GraphDatabase.driver(
                config.NEO4J_URI,  # 数据库地址
                auth=basic_auth(config.NEO4J_USER, config.NEO4J_PASSWORD)  # 认证信息
            )

            # 测试连接是否成功
            try:
                with driver.session() as session:
                    # 运行简单查询测试连接
                    result = session.run("RETURN 'connection_test' AS test")
                    record = result.single()  # 获取第一条记录
                    result.consume()  # 显式消费结果集（释放资源）

                    # 检查测试结果
                    if record and record["test"] == "connection_test":
                        print("✅ Neo4j连接成功")
                        return driver
            except Exception as test_e:
                print(f"❌ 连接测试失败: {str(test_e)}")

            print("❌ Neo4j连接测试失败")
            return None
        except Exception as e:
            print(f"❌ 图数据库连接失败: {e}")
            return None

    def _load_kg_schema(self) -> Dict:
        """
        加载知识图谱模式配置

        返回:
            知识图谱模式字典
        """
        schema_path = config.KG_SCHEMA  # 模式配置文件路径
        default_schema = {
            "name": "通用知识图谱",
            "description": "默认知识图谱模式，支持多种实体类型和关系",
            "entity_types": [
                {"name": "人物", "properties": ["姓名", "职业", "国籍", "出生日期"]},
                {"name": "组织", "properties": ["名称", "类型", "成立时间", "创始人"]},
                {"name": "地点", "properties": ["名称", "类型", "所属国家", "坐标"]},
                {"name": "事件", "properties": ["名称", "时间", "地点", "参与者"]},
                {"name": "概念", "properties": ["名称", "定义", "相关领域"]},
                {"name": "技术", "properties": ["名称", "应用领域", "发明者", "发明时间"]}
            ],
            "relationship_types": [
                {"name": "属于", "source": ["人物", "组织"], "target": ["组织"]},
                {"name": "位于", "source": ["人物", "组织", "事件"], "target": ["地点"]},
                {"name": "参与", "source": ["人物", "组织"], "target": ["事件"]},
                {"name": "发明", "source": ["人物"], "target": ["技术"]},
                {"name": "应用", "source": ["技术"], "target": ["领域"]},
                {"name": "相关", "source": ["概念", "技术"], "target": ["概念", "技术"]},
                {"name": "包含", "source": ["概念"], "target": ["概念"]},
                {"name": "发生于", "source": ["事件"], "target": ["时间"]},
                {"name": "领导", "source": ["人物"], "target": ["组织"]},
                {"name": "合作", "source": ["人物", "组织"], "target": ["人物", "组织"]}
            ],
            "extraction_prompt": Template("""
你是一个专业的知识图谱工程师，请从以下文本中提取实体和关系，严格按照以下要求：
1. 只提取文本中明确提到的实体和关系
2. 使用JSON格式输出，包含两个列表："entities"和"relationships"
3. 实体格式：{"id": "唯一ID", "name": "实体名称", "type": "实体类型", "properties": {"属性名": "属性值"}}
4. 关系格式：{"source": "源实体ID", "target": "目标实体ID", "type": "关系类型", "properties": {"属性名": "属性值"}}
5. 实体类型必须是以下之一：{entity_types}
6. 关系类型必须是以下之一：{relationship_types}
文本内容：
{text}
""")
        }

        try:
            # 检查配置文件是否存在
            if os.path.exists(schema_path):
                with open(schema_path, "r", encoding="utf-8") as f:
                    schema_data = json.load(f)

                    # 处理提取提示模板
                    if "extraction_prompt" in schema_data:
                        schema_data["extraction_prompt"] = Template(schema_data["extraction_prompt"])

                    return schema_data
            else:
                # 如果配置文件不存在，创建默认配置
                with open(schema_path, "w", encoding="utf-8") as f:
                    save_data = default_schema.copy()
                    # 将模板转换为字符串以便保存
                    save_data["extraction_prompt"] = save_data["extraction_prompt"].template
                    json.dump(save_data, f, ensure_ascii=False, indent=2)

                print(f"✅ 创建默认知识图谱模式: {schema_path}")
                return default_schema
        except Exception as e:
            print(f"❌ 加载知识图谱模式失败: {e}, 使用默认模式")
            return default_schema

    def update_kg_schema(self, new_schema: Dict) -> bool:
        """
        更新知识图谱模式配置

        参数:
            new_schema: 新的模式配置字典

        返回:
            更新是否成功
        """
        try:
            save_data = new_schema.copy()

            # 处理提取提示模板
            if isinstance(save_data["extraction_prompt"], Template):
                save_data["extraction_prompt"] = save_data["extraction_prompt"].template

            # 保存到文件
            with open("kg_schema.json", "w", encoding="utf-8") as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)

            # 重新加载模式
            self.kg_schema = self._load_kg_schema()
            print("✅ 知识图谱模式更新成功")
            return True
        except Exception as e:
            print(f"❌ 更新知识图谱模式失败: {e}")
            return False

    def call_openai_api(self, prompt: str) -> Dict:
        """
        调用大模型API提取实体和关系

        参数:
            prompt: 提示词文本

        返回:
            包含实体和关系的字典
        """
        try:
            # 调用大模型API
            response = self.openai_client.chat.completions.create(
                model="qwen-plus",  # 使用qwen-plus模型
                messages=[
                    {"role": "system", "content": "你是一个专业的知识图谱工程师"},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "text"}  # 确保返回纯文本
            )

            # 获取模型返回的内容
            content = response.choices[0].message.content

            # 尝试解析JSON
            try:
                # 查找JSON部分（模型返回可能包含非JSON内容）
                json_start = content.find('{')
                json_end = content.rfind('}') + 1

                # 检查是否找到有效的JSON
                if json_start == -1 or json_end == 0:
                    print(f"❌ 未找到JSON内容: {content[:200]}...")
                    return {"entities": [], "relationships": []}

                json_str = content[json_start:json_end]

                # 修复常见的JSON格式问题
                json_str = re.sub(r',\s*]', ']', json_str)  # 修复多余的逗号
                json_str = re.sub(r',\s*}', '}', json_str)  # 修复多余的逗号
                json_str = re.sub(r"(\w+):", r'"\1":', json_str)  # 为键添加引号

                # 解析JSON
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                print(f"❌ JSON解析失败: {e}")
                print(f"原始内容: {content[:200]}...")
                return {"entities": [], "relationships": []}
        except Exception as e:
            print(f"❌ API调用失败: {e}")
            return {"entities": [], "relationships": []}

    def extract_entities_relations(self, text: str) -> Dict:
        """
        从文本中提取实体和关系

        参数:
            text: 输入文本

        返回:
            包含实体和关系的字典
        """
        # 获取实体类型列表
        entity_types = ", ".join([et["name"] for et in self.kg_schema["entity_types"]])
        # 获取关系类型列表
        relationship_types = ", ".join([rt["name"] for rt in self.kg_schema["relationship_types"]])

        # 获取提取提示模板
        if hasattr(self.kg_schema["extraction_prompt"], 'template'):
            raw_prompt_str = self.kg_schema["extraction_prompt"].template
        else:
            raw_prompt_str = self.kg_schema["extraction_prompt"]

        # 填充模板
        prompt = raw_prompt_str
        prompt = prompt.replace("{entity_types}", entity_types)
        prompt = prompt.replace("{relationship_types}", relationship_types)
        prompt = prompt.replace("{text}", text)

        print("🔍 使用大模型提取实体关系...")
        # 调用API提取实体关系
        result = self.call_openai_api(prompt)

        print(f"✅ 提取到 {len(result.get('entities', []))} 个实体")
        print(f"✅ 提取到 {len(result.get('relationships', []))} 个关系")
        return result

    def generate_embedding(self, text: str) -> List[float]:
        """
        为单个文本生成嵌入向量

        参数:
            text: 输入文本

        返回:
            嵌入向量列表（1536维）
        """
        if not text:
            return []

        # 检查缓存中是否已有该文本的嵌入
        if text in self.embeddings_cache:
            return self.embeddings_cache[text]

        try:
            # 调用嵌入模型API
            response = self.openai_client.embeddings.create(
                model="text-embedding-v1",  # 使用通义千问文本嵌入模型
                input=[text]  # 输入文本列表
            )
            # 获取嵌入向量
            embedding = response.data[0].embedding
            # 存入缓存
            self.embeddings_cache[text] = embedding
            return embedding
        except Exception as e:
            print(f"❌ 生成嵌入失败: {e}")
            return []

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        批量生成嵌入向量，提高效率

        参数:
            texts: 文本列表

        返回:
            嵌入向量列表
        """
        if not texts:
            return []

        # 检查缓存
        embeddings = []
        uncached_texts = []

        # 分离已缓存和未缓存的文本
        for text in texts:
            if text in self.embeddings_cache:
                embeddings.append(self.embeddings_cache[text])
            else:
                uncached_texts.append(text)

        # 为未缓存的文本生成嵌入
        if uncached_texts:
            try:
                # 分批处理（避免请求过大）
                batch_size = self.embedding_batch_size  # 使用配置的批量大小
                for i in range(0, len(uncached_texts), batch_size):
                    batch = uncached_texts[i:i + batch_size]

                    # 调用API
                    response = self.openai_client.embeddings.create(
                        model="text-embedding-v1",
                        input=batch
                    )

                    # 处理返回结果
                    for j, data in enumerate(response.data):
                        embedding = data.embedding
                        text = batch[j]
                        # 存入缓存
                        self.embeddings_cache[text] = embedding
                        embeddings.append(embedding)
            except Exception as e:
                print(f"❌ 批量生成嵌入失败: {e}")
                # 为失败的请求添加空嵌入
                for _ in range(len(uncached_texts)):
                    embeddings.append([])

        return embeddings

    def _create_vector_index(self):
        """在Neo4j数据库中创建向量索引（如果不存在）"""
        if not self.driver:
            return

        try:
            with self.driver.session() as session:
                # 创建实体向量索引（如果不存在）
                session.run("""
                CREATE VECTOR INDEX IF NOT EXISTS FOR (e:Entity) ON e.embedding 
                OPTIONS {indexConfig: {
                    `vector.dimensions`: 1536,
                    `vector.similarity_function`: 'cosine'
                }}
                """)

                # 创建关系向量索引（如果不存在）
                session.run("""
                CREATE VECTOR INDEX IF NOT EXISTS FOR ()-[r:RELATIONSHIP]-() ON r.embedding 
                OPTIONS {indexConfig: {
                    `vector.dimensions`: 1536,
                    `vector.similarity_function`: 'cosine'
                }}
                """)
            print("✅ 数据库向量索引已创建或已存在")
        except Exception as e:
            print(f"❌ 创建数据库向量索引失败: {e}")

    def build_vector_index_from_neo4j(self):
        """从Neo4j加载所有实体和关系，构建内存向量索引"""
        if not self.driver:
            print("❌ 图数据库未连接，无法构建索引")
            return

        try:
            with self.driver.session() as session:
                print("🔄 从Neo4j加载实体...")
                # 查询所有实体
                result = session.run("MATCH (e) RETURN id(e) as id, e.name as name, labels(e) as labels")
                entities = []
                for record in tqdm(result, desc="加载实体", disable=not self.is_first_run):
                    entities.append({
                        "id": record["id"],
                        "name": record["name"],
                        "labels": record["labels"]
                    })

                print("🧠 生成实体嵌入...")
                # 为实体生成文本描述
                entity_texts = [
                    f"{e['labels'][0] if e['labels'] else 'Entity'}: {e['name']}"
                    for e in entities
                ]
                # 批量生成嵌入向量
                entity_embeddings = self.generate_embeddings_batch(entity_texts)

                print("📥 更新实体索引...")
                # 更新内存索引
                for i, entity in enumerate(entities):
                    embedding = entity_embeddings[i] if i < len(entity_embeddings) else []
                    if embedding:
                        # 检查是否已存在
                        if entity["id"] not in self.vector_index["entities"]["ids"]:
                            self.vector_index["entities"]["ids"].append(entity["id"])
                            self.vector_index["entities"]["names"].append(entity["name"])
                            self.vector_index["entities"]["types"].append(
                                entity["labels"][0] if entity["labels"] else "Entity")
                            # 将嵌入向量添加到矩阵中
                            self.vector_index["entities"]["embeddings"] = np.vstack((
                                self.vector_index["entities"]["embeddings"],
                                np.array(embedding).reshape(1, -1)
                            ))

                print("🔄 从Neo4j加载关系...")
                # 查询所有关系
                result = session.run("""
                MATCH ()-[r]->()
                RETURN id(r) as id, type(r) as type, startNode(r).name as source, endNode(r).name as target
                """)
                relationships = []
                for record in tqdm(result, desc="加载关系", disable=not self.is_first_run):
                    relationships.append({
                        "id": record["id"],
                        "type": record["type"],
                        "source": record["source"],
                        "target": record["target"]
                    })

                print("🧠 生成关系嵌入...")
                # 为关系生成文本描述
                rel_texts = [
                    f"{rel['type']}: {rel['source']} -> {rel['target']}"
                    for rel in relationships
                ]
                # 批量生成嵌入向量
                rel_embeddings = self.generate_embeddings_batch(rel_texts)

                print("📥 更新关系索引...")
                # 更新内存索引
                for i, rel in enumerate(relationships):
                    embedding = rel_embeddings[i] if i < len(rel_embeddings) else []
                    if embedding:
                        # 检查是否已存在
                        if rel["id"] not in self.vector_index["relationships"]["ids"]:
                            self.vector_index["relationships"]["ids"].append(rel["id"])
                            self.vector_index["relationships"]["types"].append(rel["type"])
                            self.vector_index["relationships"]["sources"].append(rel["source"])
                            self.vector_index["relationships"]["targets"].append(rel["target"])
                            # 将嵌入向量添加到矩阵中
                            self.vector_index["relationships"]["embeddings"] = np.vstack((
                                self.vector_index["relationships"]["embeddings"],
                                np.array(embedding).reshape(1, -1)
                            ))

                print(
                    f"✅ 向量索引构建完成，共加载 {len(self.vector_index['entities']['ids'])} 个实体和 {len(self.vector_index['relationships']['ids'])} 个关系")
        except Exception as e:
            print(f"❌ 构建向量索引失败: {e}")

    def build_ann_models(self):
        """动态构建 ANN 模型，防止 n_neighbors > n_samples_fit"""
        for key, emb in [
            ("entities", self.vector_index["entities"]["embeddings"]),
            ("relationships", self.vector_index["relationships"]["embeddings"])
        ]:
            if emb.shape[0] == 0:
                self.ann_models[key] = None
                continue

            # 确保 n_neighbors 不超过样本数
            max_k = max(1, emb.shape[0] - 1)
            k = min(self.top_k * 2, max_k)
            print(f"🔧 构建 {key} ANN 模型：样本数={emb.shape[0]}，n_neighbors={k}")
            self.ann_models[key] = NearestNeighbors(n_neighbors=k, metric='cosine')
            self.ann_models[key].fit(emb)

    # ========= 新增图查询方法 =========
    def shortest_path(self, source: str, target: str) -> List[Dict]:
        if not self.driver:
            return []
        with self.driver.session() as session:
            res = session.run("""
                MATCH path = shortestPath((a:Entity {name:$src})-[*]-(b:Entity {name:$tgt}))
                RETURN [n in nodes(path) | {id:id(n), name:n.name, type:labels(n)[0]}] as nodes,
                       [r in relationships(path) | {source:startNode(r).name, target:endNode(r).name, type:type(r)}] as rels
            """, src=source, tgt=target)
            return [dict(r) for r in res]

    def centrality_analysis(self) -> Dict:
        if not self.driver:
            return {}
        with self.driver.session() as session:
            # 出度中心性
            res = session.run("""
                MATCH (n)-[r]-()
                RETURN n.name as node, count(r) as degree
                ORDER BY degree DESC LIMIT 10
            """)
            return {r["node"]: r["degree"] for r in res}

    def search_nodes(self, keyword: str) -> Dict:
        if not self.driver:
            return {"nodes": [], "links": []}
        with self.driver.session() as session:
            res = session.run("""
                MATCH (n)-[r]-(m)
                WHERE n.name CONTAINS $kw OR m.name CONTAINS $kw
                RETURN n.name as source, labels(n)[0] as source_type,
                       type(r) as relationship,
                       m.name as target, labels(m)[0] as target_type,
                       id(n) as source_id, id(m) as target_id
                LIMIT 50
            """, kw=keyword)
            nodes, links, node_set = [], [], set()
            for rec in res:
                for id_, name, type_ in [(rec["source_id"], rec["source"], rec["source_type"]),
                                         (rec["target_id"], rec["target"], rec["target_type"])]:
                    if id_ not in node_set:
                        nodes.append({"id": id_, "name": name, "type": type_})
                        node_set.add(id_)
                links.append({"source": rec["source_id"], "target": rec["target_id"], "type": rec["relationship"]})
            return {"nodes": nodes, "links": links}


    def save_to_neo4j(self, entities: List[Dict], relationships: List[Dict]) -> bool:
        """
        将提取的实体关系保存到Neo4j数据库
        并更新向量索引（仅新增部分）

        参数:
            entities: 实体列表
            relationships: 关系列表

        返回:
            保存是否成功
        """
        if not self.driver:
            print("❌ 图数据库未连接，无法保存")
            return False

        try:
            with self.driver.session() as session:
                # 创建实体
                new_entities = []  # 存储新添加的实体

                for entity in entities:
                    # 获取实体信息
                    entity_name = entity["name"]
                    entity_type = entity["type"]
                    properties = entity.get("properties", {})

                    # 生成实体描述文本（用于嵌入）
                    entity_text = f"{entity_type}: {entity_name}"

                    # 创建或合并实体节点
                    query = """
                    MERGE (e:Entity:%s {name: $name})
                    SET e += $props
                    RETURN id(e) as id
                    """ % entity_type

                    # 执行查询
                    result = session.run(query, name=entity_name, props=properties)
                    record = result.single()
                    result.consume()

                    if record:
                        entity_id = record["id"]

                        # 检查是否是新实体
                        if entity_id not in self.vector_index["entities"]["ids"]:
                            # 生成嵌入向量
                            embedding = self.generate_embedding(entity_text)

                            # 更新节点嵌入
                            session.run("""
                            MATCH (e) WHERE id(e) = $id
                            SET e.embedding = $embedding
                            """, id=entity_id, embedding=embedding)

                            # 添加到缓存和新实体列表
                            self.entity_cache[entity_id] = {
                                "name": entity_name,
                                "type": entity_type,
                                "embedding": embedding
                            }

                            new_entities.append({
                                "id": entity_id,
                                "name": entity_name,
                                "type": entity_type,
                                "embedding": embedding
                            })

                # 创建关系
                new_relationships = []  # 存储新添加的关系

                for rel in relationships:
                    # 获取关系信息
                    source_id = rel["source"]
                    target_id = rel["target"]
                    rel_type = rel["type"]
                    properties = rel.get("properties", {})

                    # 获取实体名称
                    source_name = self.entity_cache.get(source_id, {}).get("name", "Unknown")
                    target_name = self.entity_cache.get(target_id, {}).get("name", "Unknown")

                    # 生成关系描述文本（用于嵌入）
                    rel_text = f"{rel_type}: {source_name} -> {target_name}"

                    # 创建关系
                    query = """
                    MATCH (source), (target) 
                    WHERE id(source) = $source_id AND id(target) = $target_id
                    MERGE (source)-[r:%s]->(target)
                    SET r.type = $rel_type
                    SET r += $props
                    RETURN id(r) as id
                    """ % rel_type

                    # 执行查询
                    result = session.run(query,
                                         source_id=source_id,
                                         target_id=target_id,
                                         rel_type=rel_type,
                                         props=properties)
                    record = result.single()
                    result.consume()

                    if record:
                        rel_id = record["id"]

                        # 检查是否是新关系
                        if rel_id not in self.vector_index["relationships"]["ids"]:
                            # 生成嵌入向量
                            rel_embedding = self.generate_embedding(rel_text)

                            # 更新关系嵌入
                            session.run("""
                            MATCH ()-[r]->() WHERE id(r) = $id
                            SET r.embedding = $embedding
                            """, id=rel_id, embedding=rel_embedding)

                            new_relationships.append({
                                "id": rel_id,
                                "type": rel_type,
                                "source": source_name,
                                "target": target_name,
                                "embedding": rel_embedding
                            })

                # 更新内存索引
                for entity in new_entities:
                    self.vector_index["entities"]["ids"].append(entity["id"])
                    self.vector_index["entities"]["names"].append(entity["name"])
                    self.vector_index["entities"]["types"].append(entity["type"])
                    self.vector_index["entities"]["embeddings"] = np.vstack((
                        self.vector_index["entities"]["embeddings"],
                        np.array(entity["embedding"]).reshape(1, -1)
                    ))

                for rel in new_relationships:
                    self.vector_index["relationships"]["ids"].append(rel["id"])
                    self.vector_index["relationships"]["types"].append(rel["type"])
                    self.vector_index["relationships"]["sources"].append(rel["source"])
                    self.vector_index["relationships"]["targets"].append(rel["target"])
                    self.vector_index["relationships"]["embeddings"] = np.vstack((
                        self.vector_index["relationships"]["embeddings"],
                        np.array(rel["embedding"]).reshape(1, -1)
                    ))

                print(f"✅ 成功保存 {len(entities)} 个实体和 {len(relationships)} 个关系到Neo4j")
                print(f"📥 更新索引: 新增 {len(new_entities)} 个实体, {len(new_relationships)} 个关系")

                # 重建ANN模型
                self.build_ann_models()

                # 保存更新后的索引
                self._save_vector_index()

                return True
        except Exception as e:
            print(f"❌ 保存到Neo4j失败: {e}")
            return False

    def find_similar_entities_batch(self, embeddings: np.ndarray, threshold: float = 0.75, top_k: int = 5) -> List[
        List[Dict]]:
        """
        批量查找相似的实体（使用ANN加速）

        参数:
            embeddings: 查询嵌入向量矩阵
            threshold: 相似度阈值
            top_k: 返回的最相似结果数量

        返回:
            每个查询嵌入对应的相似实体列表
        """
        results = []

        # 检查是否有数据
        if embeddings.size == 0 or self.vector_index["entities"]["embeddings"].size == 0:
            return [[] for _ in range(len(embeddings))]

        # 使用ANN模型进行近似搜索
        if self.ann_models["entities"]:
            # 查找最近的邻居
            distances, indices = self.ann_models["entities"].kneighbors(embeddings, n_neighbors=top_k * 2)

            for i, query_embedding in enumerate(embeddings):
                similar_entities = []
                # 获取候选实体
                for j, idx in enumerate(indices[i]):
                    # 余弦距离转换为余弦相似度
                    similarity = 1 - distances[i][j]

                    # 检查是否达到阈值
                    if similarity < threshold:
                        continue

                    # 获取实体ID
                    entity_id = self.vector_index["entities"]["ids"][idx]

                    similar_entities.append({
                        "id": entity_id,
                        "name": self.vector_index["entities"]["names"][idx],
                        "type": self.vector_index["entities"]["types"][idx],
                        "similarity": similarity
                    })

                # 按相似度排序并截取top_k
                similar_entities.sort(key=lambda x: x["similarity"], reverse=True)
                results.append(similar_entities[:top_k])
        else:
            # 如果没有ANN模型，使用暴力搜索（不推荐用于大数据集）
            db_embeddings = self.vector_index["entities"]["embeddings"]
            for query_embedding in embeddings:
                # 计算所有相似度
                similarities = cosine_similarity([query_embedding], db_embeddings)[0]

                # 获取超过阈值的相似实体
                similar_entities = []
                for idx, sim in enumerate(similarities):
                    if sim >= threshold:
                        similar_entities.append({
                            "id": self.vector_index["entities"]["ids"][idx],
                            "name": self.vector_index["entities"]["names"][idx],
                            "type": self.vector_index["entities"]["types"][idx],
                            "similarity": sim
                        })

                # 按相似度排序并截取top_k
                similar_entities.sort(key=lambda x: x["similarity"], reverse=True)
                results.append(similar_entities[:top_k])

        return results

    def find_similar_relationships_batch(self, embeddings: np.ndarray, threshold: float = 0.7, top_k: int = 5) -> List[
        List[Dict]]:
        """
        批量查找相似的关系（使用ANN加速）

        参数:
            embeddings: 查询嵌入向量矩阵
            threshold: 相似度阈值
            top_k: 返回的最相似结果数量

        返回:
            每个查询嵌入对应的相似关系列表
        """
        results = []

        # 检查是否有数据
        if embeddings.size == 0 or self.vector_index["relationships"]["embeddings"].size == 0:
            return [[] for _ in range(len(embeddings))]

        # 使用ANN模型进行近似搜索
        if self.ann_models["relationships"]:
            # 查找最近的邻居
            distances, indices = self.ann_models["relationships"].kneighbors(embeddings, n_neighbors=top_k * 2)

            for i, query_embedding in enumerate(embeddings):
                similar_rels = []
                # 获取候选关系
                for j, idx in enumerate(indices[i]):
                    # 余弦距离转换为余弦相似度
                    similarity = 1 - distances[i][j]

                    # 检查是否达到阈值
                    if similarity < threshold:
                        continue

                    # 获取关系ID
                    rel_id = self.vector_index["relationships"]["ids"][idx]

                    similar_rels.append({
                        "id": rel_id,
                        "type": self.vector_index["relationships"]["types"][idx],
                        "source": self.vector_index["relationships"]["sources"][idx],
                        "target": self.vector_index["relationships"]["targets"][idx],
                        "similarity": similarity
                    })

                # 按相似度排序并截取top_k
                similar_rels.sort(key=lambda x: x["similarity"], reverse=True)
                results.append(similar_rels[:top_k])
        else:
            # 暴力搜索
            db_embeddings = self.vector_index["relationships"]["embeddings"]
            for query_embedding in embeddings:
                # 计算所有相似度
                similarities = cosine_similarity([query_embedding], db_embeddings)[0]

                # 获取超过阈值的相似关系
                similar_rels = []
                for idx, sim in enumerate(similarities):
                    if sim >= threshold:
                        similar_rels.append({
                            "id": self.vector_index["relationships"]["ids"][idx],
                            "type": self.vector_index["relationships"]["types"][idx],
                            "source": self.vector_index["relationships"]["sources"][idx],
                            "target": self.vector_index["relationships"]["targets"][idx],
                            "similarity": sim
                        })

                # 按相似度排序并截取top_k
                similar_rels.sort(key=lambda x: x["similarity"], reverse=True)
                results.append(similar_rels[:top_k])

        return results

    def query_kg_by_entities(self, entity_ids: List[int], depth: int = 2) -> List[Dict]:
        """
        在知识图谱中查询与实体相关的子图

        参数:
            entity_ids: 实体ID列表
            depth: 查询深度（关系跳数）

        返回:
            查询结果列表
        """
        if not self.driver or not entity_ids:
            return []

        try:
            with self.driver.session() as session:
                # 构建查询语句
                query = """
                MATCH path = (start)-[rel*..%d]-(end)
                WHERE id(start) IN $entity_ids
                WITH nodes(path) AS nodes, relationships(path) AS rels
                UNWIND nodes AS node
                UNWIND rels AS rel

                WITH DISTINCT rel, startNode(rel) AS start, endNode(rel) AS end
                RETURN start.name AS source, 
                       labels(start)[0] AS source_type,
                       type(rel) AS relationship, 
                       end.name AS target,
                       labels(end)[0] AS target_type,
                       properties(rel) AS rel_properties
                ORDER BY source, relationship, target
                LIMIT 100
                """ % depth

                # 执行查询
                result = session.run(query, entity_ids=entity_ids)
                # 转换为字典列表
                records = [dict(record) for record in result]
                result.consume()  # 释放资源
                return records
        except Exception as e:
            print(f"❌ 图数据库查询失败: {e}")
            return []

    def process_user_query(self, text: str, save_to_db: bool = False,
                           depth: int = 2, similarity_threshold: float = 0.7,
                           top_k: int = 5) -> List[Dict]:
        """
        处理用户查询的主要流程
        优化：只为新提取的实体关系生成嵌入向量

        参数:
            text: 用户输入的文本
            save_to_db: 是否将提取结果保存到数据库
            depth: 知识图谱查询深度
            similarity_threshold: 相似度阈值
            top_k: 返回的最相似结果数量

        返回:
            知识图谱查询结果
        """
        start_time = time.time()
        print("\n" + "=" * 50)
        print(f"🔍 开始处理查询: {text[:50]}...")
        print("=" * 50)

        # 1. 从文本中提取实体关系
        extract_start = time.time()
        extraction_result = self.extract_entities_relations(text)
        entities = extraction_result.get("entities", [])
        relationships = extraction_result.get("relationships", [])
        print(f"⏱️ 提取实体关系耗时: {time.time() - extract_start:.2f}s")
        print(f"📊 提取结果: {len(entities)} 个实体, {len(relationships)} 个关系")

        # 2. 按需保存到Neo4j
        if save_to_db and self.driver and (entities or relationships):
            save_start = time.time()
            print("💾 保存提取结果到Neo4j...")
            self.save_to_neo4j(entities, relationships)
            print(f"⏱️ 保存到数据库耗时: {time.time() - save_start:.2f}s")
        elif save_to_db and not self.driver:
            print("⚠️ 无法保存到数据库：数据库未连接")

        # 3. 为提取的实体和关系生成嵌入向量
        embed_start = time.time()

        # 生成实体嵌入
        entity_texts = [
            f"{entity.get('type', '实体')}: {entity['name']}"
            for entity in entities
        ]
        entity_embeddings = self.generate_embeddings_batch(entity_texts)

        # 生成关系嵌入
        rel_texts = []
        for rel in relationships:
            # 查找源实体和目标实体的名称
            source_name = next((e["name"] for e in entities if e.get("id") == rel["source"]), "Unknown")
            target_name = next((e["name"] for e in entities if e.get("id") == rel["target"]), "Unknown")
            rel_texts.append(f"{rel['type']}: {source_name} -> {target_name}")

        rel_embeddings = self.generate_embeddings_batch(rel_texts)

        # 转换为numpy数组并过滤空嵌入
        entity_embeddings_np = np.array([e for e in entity_embeddings if e])
        rel_embeddings_np = np.array([r for r in rel_embeddings if r])

        print(f"⏱️ 生成嵌入向量耗时: {time.time() - embed_start:.2f}s")
        print(f"🔢 生成实体嵌入: {len(entity_embeddings_np)}个, 关系嵌入: {len(rel_embeddings_np)}个")

        # 4. 批量计算相似度并找出最相似的实体关系
        similarity_start = time.time()

        # 查找相似实体
        similar_entities_results = self.find_similar_entities_batch(
            entity_embeddings_np,
            threshold=similarity_threshold,
            top_k=top_k
        )

        # 查找相似关系
        similar_rels_results = self.find_similar_relationships_batch(
            rel_embeddings_np,
            threshold=similarity_threshold,
            top_k=top_k
        )

        # 收集所有相似实体的ID
        all_similar_entity_ids = set()

        # 从相似实体结果中收集ID
        for entity_list in similar_entities_results:
            for entity in entity_list:
                all_similar_entity_ids.add(entity["id"])

        # 从相似关系结果中收集相关实体ID
        for rel_list in similar_rels_results:
            for rel in rel_list:
                # 查找关系对应的源实体和目标实体
                source_id = next((idx for idx, name in enumerate(self.vector_index["entities"]["names"])
                                  if name == rel["source"]), None)
                target_id = next((idx for idx, name in enumerate(self.vector_index["entities"]["names"])
                                  if name == rel["target"]), None)

                if source_id is not None:
                    all_similar_entity_ids.add(self.vector_index["entities"]["ids"][source_id])
                if target_id is not None:
                    all_similar_entity_ids.add(self.vector_index["entities"]["ids"][target_id])

        print(f"⏱️ 相似度计算耗时: {time.time() - similarity_start:.2f}s")
        print(f"🔍 找到 {len(all_similar_entity_ids)} 个相似实体")

        # 5. 在数据库中进行多跳查询
        query_start = time.time()
        if all_similar_entity_ids:
            kg_results = self.query_kg_by_entities(list(all_similar_entity_ids), depth)
        else:
            kg_results = []

        print(f"⏱️ 图数据库查询耗时: {time.time() - query_start:.2f}s")
        print(f"⏱️ 总耗时: {time.time() - start_time:.2f}s")
        print(f"✅ 找到 {len(kg_results)} 条相关关系")
        return kg_results

    def format_kg_results(self, records: List[Dict]) -> str:
        """
        格式化知识图谱结果为自然语言描述

        参数:
            records: 知识图谱查询结果

        返回:
            自然语言描述字符串
        """
        if not records:
            return "知识图谱中未找到相关信息"

        # 按关系类型分组
        relation_groups = {}
        for record in records:
            rel_type = record["relationship"]
            if rel_type not in relation_groups:
                relation_groups[rel_type] = []

            # 添加属性描述（排除嵌入向量）
            properties = {
                k: v for k, v in record.get("rel_properties", {}).items()
                if k != "embedding" and not k.startswith("vector")
            }

            prop_desc = ""
            if properties:
                prop_desc = " (" + ", ".join([f"{k}: {v}" for k, v in properties.items()]) + ")"

            # 构建关系描述
            relation_desc = f"{record['source']}({record['source_type']}) -> {record['target']}({record['target_type']}){prop_desc}"
            relation_groups[rel_type].append(relation_desc)

        # 构建自然语言描述
        descriptions = []
        for rel_type, items in relation_groups.items():
            if len(items) == 1:
                descriptions.append(f"{items[0]} 之间存在 {rel_type} 关系。")
            else:
                # 提取所有源实体
                sources = set([item.split('->')[0].strip() for item in items])
                # 提取所有目标实体
                targets = set([item.split('->')[1].strip() for item in items])

                source_list = ", ".join(sources)
                target_list = ", ".join(targets)
                descriptions.append(
                    f"{source_list} 与 {target_list} 之间存在 {rel_type} 关系。"
                )

        return "\n".join(descriptions)

    def visualize_kg(self, records: List[Dict], output_file: str = "kg_visualization.html") -> str:
        """
        生成知识图谱可视化

        参数:
            records: 知识图谱查询结果
            output_file: 输出文件名

        返回:
            输出文件路径
        """
        if not records:
            print("⚠️ 无数据可可视化")
            return ""

        try:
            # 创建网络图
            net = Network(height="800px", width="100%", notebook=False, directed=True)

            # 颜色映射 - 为不同类型的实体分配不同颜色
            type_colors = {
                "人物": "#FF9AA2", "组织": "#FFB7B2", "地点": "#FFDAC1",
                "事件": "#E2F0CB", "概念": "#B5EAD7", "技术": "#C7CEEA"
            }

            # 默认颜色
            default_color = "#B0B0B0"

            # 跟踪已添加的节点
            added_nodes = set()

            # 添加节点和边
            for record in records:
                src = record["source"]
                src_type = record["source_type"]
                tgt = record["target"]
                tgt_type = record["target_type"]
                rel = record["relationship"]
                properties = record.get("rel_properties", {})

                # 添加源节点（如果尚未添加）
                if src not in added_nodes:
                    color = type_colors.get(src_type, default_color)
                    net.add_node(src, title=f"{src_type}: {src}", label=src, color=color)
                    added_nodes.add(src)

                # 添加目标节点（如果尚未添加）
                if tgt not in added_nodes:
                    color = type_colors.get(tgt_type, default_color)
                    net.add_node(tgt, title=f"{tgt_type}: {tgt}", label=tgt, color=color)
                    added_nodes.add(tgt)

                # 添加关系边
                edge_title = f"{rel}"

                # 添加属性信息
                if properties:
                    edge_title += "\n" + "\n".join([f"{k}: {v}" for k, v in properties.items()])

                # 添加边
                net.add_edge(src, tgt, title=edge_title, label=rel)

            # 保存可视化
            net.save_graph(output_file)
            print(f"✅ 知识图谱可视化已保存至: {output_file}")
            return output_file
        except Exception as e:
            print(f"❌ 可视化保存失败: {e}")
            return ""

    def generate_narrative(self, records: List[Dict]) -> str:
        """
        将知识图谱结果整合成连贯叙述

        参数:
            records: 知识图谱查询结果

        返回:
            叙述文本
        """
        if not records:
            return "根据知识图谱，没有找到相关信息。"

        # 构建实体关系映射
        entity_relations = {}
        for record in records:
            source = record["source"]
            target = record["target"]
            relationship = record["relationship"]

            # 排除嵌入向量属性
            properties = {
                k: v for k, v in record.get("rel_properties", {}).items()
                if k != "embedding" and not k.startswith("vector")
            }

            # 为源实体记录关系
            if source not in entity_relations:
                entity_relations[source] = {"outgoing": [], "incoming": []}

            entity_relations[source]["outgoing"].append({
                "target": target,
                "relationship": relationship,
                "properties": properties
            })

            # 为目标实体记录关系
            if target not in entity_relations:
                entity_relations[target] = {"outgoing": [], "incoming": []}

            entity_relations[target]["incoming"].append({
                "source": source,
                "relationship": relationship,
                "properties": properties
            })

        # 生成叙述文本
        narrative = "根据知识图谱分析，以下是相关信息：\n\n"

        for entity, relations in entity_relations.items():
            # 实体介绍
            narrative += f"• {entity}："

            # 入边关系（指向该实体的关系）
            if relations["incoming"]:
                incoming_desc = []
                for rel in relations["incoming"]:
                    desc = f"{rel['source']} {rel['relationship']} {entity}"

                    # 添加属性描述（最多显示2个属性）
                    if rel["properties"]:
                        props = ", ".join([f"{k}为{v}" for i, (k, v) in enumerate(rel["properties"].items()) if i < 2])
                        if len(rel["properties"]) > 2:
                            props += "等"
                        desc += f" ({props})"

                    incoming_desc.append(desc)

                narrative += "受到 " + "、".join(incoming_desc) + " 的影响。"

            # 出边关系（从该实体出发的关系）
            if relations["outgoing"]:
                outgoing_desc = []
                for rel in relations["outgoing"]:
                    desc = f"{entity} {rel['relationship']} {rel['target']}"

                    # 添加属性描述（最多显示2个属性）
                    if rel["properties"]:
                        props = ", ".join([f"{k}为{v}" for i, (k, v) in enumerate(rel["properties"].items()) if i < 2])
                        if len(rel["properties"]) > 2:
                            props += "等"
                        desc += f" ({props})"

                    outgoing_desc.append(desc)

                # 连接词处理
                if relations["incoming"]:
                    narrative += " 同时，"

                narrative += "涉及 " + "、".join(outgoing_desc) + "。"

            narrative += "\n"

        return narrative

    def query_whole_graph(self, limit: int = 100) -> Dict:
        """
        查询整个知识图谱（限制数量）

        参数:
            limit: 返回的关系数量限制

        返回:
            {"nodes": 节点列表, "links": 关系列表}
        """
        if not self.driver:
            return {"nodes": [], "links": []}

        try:
            with self.driver.session() as session:
                # 构建查询语句（查询所有关系，限制数量）
                query = """
                MATCH (start)-[r]->(end)
                RETURN start.name AS source, 
                       labels(start)[0] AS source_type,
                       type(r) AS relationship, 
                       end.name AS target,
                       labels(end)[0] AS target_type,
                       id(start) as source_id,
                       id(end) as target_id
                LIMIT $limit
                """

                # 执行查询
                result = session.run(query, limit=limit)
                records = [dict(record) for record in result]

                # 转换为前端需要的格式
                nodes = []
                links = []
                node_set = set()

                for record in records:
                    # 确保使用正确的字段名
                    source_id = record["source_id"]
                    source_name = record["source"]
                    source_type = record["source_type"]
                    target_id = record["target_id"]
                    target_name = record["target"]
                    target_type = record["target_type"]
                    rel_type = record["relationship"]

                    # 添加源节点
                    if source_id not in node_set:
                        nodes.append({
                            "id": source_id,
                            "name": source_name,
                            "type": source_type
                        })
                        node_set.add(source_id)

                    # 添加目标节点
                    if target_id not in node_set:
                        nodes.append({
                            "id": target_id,
                            "name": target_name,
                            "type": target_type
                        })
                        node_set.add(target_id)

                    # 添加关系
                    links.append({
                        "source": source_id,
                        "target": target_id,
                        "type": rel_type
                    })

                return {"nodes": nodes, "links": links}
        except Exception as e:
            print(f"❌ 图数据库查询失败: {e}")
            return {"nodes": [], "links": []}

    def get_kg_statistics(self) -> Dict[str, int]:
        """获取知识图谱统计信息"""
        stats = {"entities": 0, "relationships": 0}
        if not self.driver:
            return stats

        try:
            with self.driver.session() as session:
                # 查询实体数量
                result = session.run("MATCH (e) RETURN count(e) as entity_count")
                record = result.single()
                stats["entities"] = record["entity_count"] if record else 0

                # 查询关系数量
                result = session.run("MATCH ()-[r]->() RETURN count(r) as rel_count")
                record = result.single()
                stats["relationships"] = record["rel_count"] if record else 0
        except Exception as e:
            print(f"❌ 获取图谱统计信息失败: {e}")

        return stats

    def query_whole_graph(self, limit: int = 500) -> Dict:
        """
                查询整个知识图谱（限制数量）

                参数:
                    limit: 返回的关系数量限制

                返回:
                    {"nodes": 节点列表, "links": 关系列表}
                """
        if not self.driver:
            return {"nodes": [], "links": []}

        try:
            with self.driver.session() as session:
                # 构建查询语句（查询所有关系，限制数量）
                query = """
                        MATCH (start)-[r]->(end)
                        RETURN start.name AS source, 
                               labels(start)[0] AS source_type,
                               type(r) AS relationship, 
                               end.name AS target,
                               labels(end)[0] AS target_type,
                               id(start) as source_id,
                               id(end) as target_id
                        LIMIT $limit
                        """

                # 执行查询
                result = session.run(query, limit=limit)
                records = [dict(record) for record in result]

                # 转换为前端需要的格式
                nodes = []
                links = []
                node_set = set()

                for record in records:
                    source_id = record["source_id"]
                    source_name = record["source"]
                    source_type = record["source_type"]
                    target_id = record["target_id"]
                    target_name = record["target"]
                    target_type = record["target_type"]
                    rel_type = record["relationship"]

                    # 添加源节点
                    if source_id not in node_set:
                        nodes.append({
                            "id": source_id,
                            "name": source_name,
                            "type": source_type
                        })
                        node_set.add(source_id)

                    # 添加目标节点
                    if target_id not in node_set:
                        nodes.append({
                            "id": target_id,
                            "name": target_name,
                            "type": target_type
                        })
                        node_set.add(target_id)

                    # 添加关系
                    links.append({
                        "source": source_id,
                        "target": target_id,
                        "type": rel_type
                    })

                return {"nodes": nodes, "links": links}
        except Exception as e:
            print(f"❌ 图数据库查询失败: {e}")
            return {"nodes": [], "links": []}


# 使用示例
if __name__ == "__main__":
    # 创建知识图谱管理器
    print("🛠️ 初始化知识图谱管理器...")
    kg = KnowledgeGraphManager(ann_leaf_size=30)

    # 设置相似度参数
    kg.similarity_threshold = 0.75  # 相似度阈值
    kg.top_k = 3  # 每个实体/关系返回的最相似结果数

    # 示例文本
    text = """
    量子计算是一种利用量子力学原理进行计算的新兴技术。IBM和Google是量子计算领域的领先企业。
    """

    # 主要流程：处理用户查询
    print("\n处理用户查询:")
    kg_results = kg.process_user_query(
        text,
        save_to_db=True,  # 是否保存提取结果到数据库
        depth=2,  # 查询深度
        similarity_threshold=kg.similarity_threshold,  # 相似度阈值
        top_k=kg.top_k  # 返回的相似结果数量
    )

    # 格式化结果
    print("\n格式化结果:")
    formatted = kg.format_kg_results(kg_results)
    print(formatted)

    # 生成叙述文本
    print("\n叙述文本:")
    narrative = kg.generate_narrative(kg_results)
    print(narrative)
