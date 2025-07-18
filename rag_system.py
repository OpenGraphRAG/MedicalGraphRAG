#!/usr/bin/env python3
# coding: utf-8

"""
GraphRAGSystem - 整合向量检索与知识图谱的问答系统

功能：
1. 接收外挂文档并更新向量数据库
2. 处理用户输入的长文本查询
3. 同时调用向量检索和知识图谱检索
4. 整合两种检索结果形成规范的Prompt
5. 调用大模型API生成最终回答
"""
# !/usr/bin/env python3
# coding: utf-8
"""
GraphRAGSystem – 健康推送专用精简版
只处理 **用户健康画像** → 向量匹配子图 → 生成 **结构化推送**
"""
import os
import time
import json
from typing import Dict, List, Any, Optional
from openai import OpenAI
from config import config
from knowledge_graph import KnowledgeGraphManager
from vector_db import VectorDBManager
from langchain_community.document_loaders import (
    TextLoader, PyPDFLoader, Docx2txtLoader, UnstructuredMarkdownLoader
)
import glob


class GraphRAGSystem:
    def __init__(self, kg_manager=None, vdb_manager=None):
        self.kg = kg_manager or KnowledgeGraphManager()
        self.vdb = vdb_manager or VectorDBManager()
        self.openai_client = OpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY", config.TONGYI_KEY),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self.max_tokens = 1400
        # 在 __init__ 里追加
        self.max_kg_results = 10
        self.max_vdb_results = 5
        self.max_context_length = 4000

    def query(self, user_input: str, depth: int = 2, similarity_threshold: float = 0.75, top_k: int = 5) -> Dict:
        # 1️⃣ 向量检索
        vdb_res = self.vdb.hybrid_search(user_input, k=top_k) if self.vdb.is_initialized else []

        # 2️⃣ 知识图谱检索
        kg_res = self.kg.process_user_query(user_input, save_to_db=False, depth=depth,
                                            similarity_threshold=similarity_threshold, top_k=top_k)

        # 3️⃣ 构造 Prompt
        prompt = f"""你是一名健康知识助手，请基于下面用户的健康画像与知识图谱结果，用专业的语句推送出**个性化健康知识**，要求：

- 仅围绕用户 **真实健康状况** 与 **知识图谱中的有效信息**
- 分点推送出有关系的健康知识，并且要标注网址来源
- 要求推送的健康知识与用户的健康状况、知识图谱有效信息强相关
- 可以稍微给出在*饮食、运动、用药、复查、注意事项等具体可操作建议
- 以 Markdown 格式输出，可含小标题、列表、表情符号
---
### 👤 用户健康画像
{user_input}

---

### 🔍 知识图谱匹配结果
{json.dumps(kg_res, ensure_ascii=False, indent=2) if kg_res else "暂无图谱匹配"}

---

### 📄 相关文档片段
{chr(10).join([doc.page_content[:300] + "..." for doc in vdb_res]) if vdb_res else "暂无向量匹配"}

---

请开始生成 **专属健康知识推送**：
"""

        # 4️⃣ 调用大模型
        resp = self.openai_client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "system", "content": "你是医学健康知识助手，基于患者的健康画像和附加的相关信息，向患者输出结构化健康知识，要求详细、精准。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=self.max_tokens,
            temperature=0.35
        )

        answer = resp.choices[0].message.content.strip()
        return {
            "answer": answer,
            "kg_results": kg_res,
            "vdb_results": [d.page_content[:300] + "..." for d in vdb_res]
        }

    def update_knowledge_base(self, file_pattern: str) -> bool:
        """
        更新知识库：加载外部文档到向量数据库并提取知识到图谱

        参数:
            file_pattern: 文件路径模式 (如 "documents/*.pdf")

        返回:
            更新是否成功
        """
        print(f"🔄 更新知识库: {file_pattern}")

        # 1. 更新向量数据库
        vdb_success = self.vdb.update_from_files(file_pattern)
        if not vdb_success:
            print("❌ 向量数据库更新失败")
            return False

        # 2. 从文档中提取知识到图谱
        print("📚 从文档中提取知识到图谱...")
        for file_path in glob.glob(file_pattern):
            print(f"  处理文件: {file_path}")
            try:
                # 加载文档文本
                if file_path.endswith('.pdf'):
                    loader = PyPDFLoader(file_path)
                elif file_path.endswith('.docx'):
                    loader = Docx2txtLoader(file_path)
                elif file_path.endswith('.md'):
                    loader = UnstructuredMarkdownLoader(file_path)
                elif file_path.endswith('.txt'):
                    loader = TextLoader(file_path)
                else:
                    print(f"⚠️ 不支持的文件类型: {file_path}")
                    continue

                # 获取文档内容
                docs = loader.load()
                if not docs:
                    print(f"⚠️ 文件内容为空: {file_path}")
                    continue

                # 处理每个文档页面
                for i, doc in enumerate(docs):
                    text = doc.page_content
                    if not text.strip():
                        continue

                    # 从文本中提取实体和关系
                    extraction_result = self.kg.extract_entities_relations(text)

                    # 保存到知识图谱
                    if extraction_result.get("entities") or extraction_result.get("relationships"):
                        self.kg.save_to_neo4j(
                            extraction_result.get("entities", []),
                            extraction_result.get("relationships", [])
                        )
                        print(f"  页面 {i + 1}: 提取到 {len(extraction_result.get('entities', []))} 实体, "
                              f"{len(extraction_result.get('relationships', []))} 关系")

            except Exception as e:
                print(f"❌ 处理文件失败 {file_path}: {str(e)}")

        print("✅ 知识库更新完成")
        return True

    def generate_query_prompt(self, user_query: str, kg_results: List[Dict], vdb_results: List[Any]) -> str:
        """
        生成大模型查询的Prompt，整合知识图谱和向量检索结果

        参数:
            user_query: 用户查询文本
            kg_results: 知识图谱查询结果
            vdb_results: 向量数据库检索结果

        返回:
            整合后的Prompt文本
        """
        # 1. 构建系统提示
        prompt = """
你是一个专业的知识问答助手，拥有两个知识来源：
1. 知识图谱：包含结构化实体和关系
2. 向量检索：包含相关文档片段

请基于以下知识回答用户问题，注意：
- 如果知识图谱和文档内容冲突，以知识图谱为准
- 对于事实性问题，优先使用知识图谱
- 对于开放性问题，参考文档内容
- 如果无法确定答案，请说明原因
"""

        # 2. 添加知识图谱结果
        if kg_results:
            prompt += "\n\n## 知识图谱结果:\n"

            # 限制结果数量
            kg_results = kg_results[:self.max_kg_results]

            # 按关系分组
            relation_groups = {}
            for record in kg_results:
                rel_type = record["relationship"]
                if rel_type not in relation_groups:
                    relation_groups[rel_type] = []

                # 添加关系描述
                relation_desc = f"{record['source']}({record['source_type']}) → {record['target']}({record['target_type']})"
                relation_groups[rel_type].append(relation_desc)

            # 构建知识图谱描述
            for rel_type, items in relation_groups.items():
                if len(items) == 1:
                    prompt += f"- {items[0]} 之间存在 {rel_type} 关系\n"
                else:
                    # 提取所有源实体
                    sources = set([item.split('→')[0].strip() for item in items])
                    # 提取所有目标实体
                    targets = set([item.split('→')[1].strip() for item in items])

                    source_list = ", ".join(sources)
                    target_list = ", ".join(targets)
                    prompt += f"- {source_list} 与 {target_list} 之间存在 {rel_type} 关系\n"
        else:
            prompt += "\n\n## 知识图谱结果: 未找到相关信息\n"

        # 3. 添加向量检索结果
        if vdb_results:
            prompt += "\n\n## 相关文档片段:\n"

            # 限制结果数量
            vdb_results = vdb_results[:self.max_vdb_results]

            for i, doc in enumerate(vdb_results):
                content = doc.page_content.strip()
                # 截断过长的内容
                if len(content) > 500:
                    content = content[:250] + " ... " + content[-250:]

                prompt += f"\n片段 {i + 1}:\n{content}\n"
        else:
            prompt += "\n\n## 相关文档片段: 未找到相关信息\n"

        # 4. 添加用户查询
        prompt += f"\n\n## 用户问题:\n{user_query}\n\n请基于以上信息给出专业、准确的回答："

        # 确保不超过最大长度
        if len(prompt) > self.max_context_length:
            prompt = prompt[:self.max_context_length]

        return prompt

    def query(self, user_input: str, depth: int = 2,
              similarity_threshold: float = 0.7, top_k: int = 5) -> Dict:
        """
        处理用户查询并返回整合结果

        参数:
            user_input: 用户输入文本
            depth: 知识图谱查询深度
            similarity_threshold: 相似度阈值
            top_k: 返回的最相似结果数量

        返回:
            包含完整响应的字典
        """
        start_time = time.time()
        print(f"\n🔍 开始处理查询: {user_input[:50]}...")

        # 1. 向量数据库检索
        vdb_start = time.time()
        try:
            vdb_results = self.vdb.hybrid_search(user_input, k=top_k * 2)
            print(f"  向量检索完成: 找到 {len(vdb_results)} 个相关片段, 耗时 {time.time() - vdb_start:.2f}s")
        except Exception as e:
            print(f"❌ 向量检索失败: {str(e)}")
            vdb_results = []
        print(f"向量库检索结果为：{vdb_results.__str__()}")

        # 2. 知识图谱检索
        kg_start = time.time()
        try:
            kg_results = self.kg.process_user_query(
                user_input,
                save_to_db=False,
                depth=depth,
                similarity_threshold=similarity_threshold,
                top_k=top_k
            )
            print(f"  知识图谱检索完成: 找到 {len(kg_results)} 条关系, 耗时 {time.time() - kg_start:.2f}s")
        except Exception as e:
            print(f"❌ 知识图谱检索失败: {str(e)}")
            kg_results = []
        print(f"知识图谱检索结果整合为：{kg_results.__str__()}")

        # 3. 生成整合Prompt
        prompt = self.generate_query_prompt(user_input, kg_results, vdb_results)
        print(f"向量库和知识图谱检索结果整合为：{prompt}")

        # 4. 调用大模型生成最终回答
        llm_start = time.time()
        try:
            print("🧠 调用大模型生成回答...")
            response = self.openai_client.chat.completions.create(
                model="qwen-plus",
                messages=[
                    {"role": "system", "content": "你是一个专业的知识问答助手"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1024
            )

            # 获取模型回答
            answer = response.choices[0].message.content
            print(f"  大模型响应完成, 耗时 {time.time() - llm_start:.2f}s")
        except Exception as e:
            print(f"❌ 大模型调用失败: {e}")
            answer = "抱歉，生成回答时出现问题，请稍后再试。"

        # 5. 构建响应结果
        total_time = time.time() - start_time
        print(f"✅ 查询处理完成, 总耗时: {total_time:.2f}s")

        return {
            "user_query": user_input,
            "answer": answer,
            "kg_results": kg_results[:self.max_kg_results],
            "vdb_results": [doc.page_content[:500] + "..." for doc in vdb_results[:self.max_vdb_results]],
            "processing_time": total_time,
            "prompt": prompt
        }


# 示例使用
if __name__ == "__main__":
    print("🚀 启动GraphRAG系统...")

    # 1. 初始化知识图谱管理器
    print("🛠️ 初始化知识图谱管理器...")
    kg_manager = KnowledgeGraphManager(ann_leaf_size=30)

    # 2. 初始化向量数据库管理器
    print("🛠️ 初始化向量数据库管理器...")
    vdb_manager = VectorDBManager()

    # 3. 创建GraphRAG系统
    print("🛠️ 创建GraphRAG系统...")
    graph_rag = GraphRAGSystem(kg_manager, vdb_manager)

    # 5. 示例查询
    queries = [
        "患者因季节性花粉过敏就诊，症状包括打喷嚏、流涕"
    ]

    # 处理每个查询
    for query in queries:
        print("\n" + "=" * 50)
        print(f"📝 用户查询: {query}")

        # 执行查询
        response = graph_rag.query(
            user_input=query,
            depth=2,  # 知识图谱查询深度
            similarity_threshold=0.7,  # 相似度阈值
            top_k=3  # 返回的相似结果数量
        )

        # 打印结果
        print("\n💡 最终回答:")
        print(response["answer"])
