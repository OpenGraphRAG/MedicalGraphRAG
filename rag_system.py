#!/usr/bin/env python3
# coding: utf-8
"""
GraphRAGSystem - 基于 Graph + RAG 的健康知识推送系统

核心流程（GraphRAG思想）:
1. 从用户健康信息中提取关键实体（疾病、症状、药物等）
2. 用实体去知识图谱中查询相关子图（关系链 = 骨架）
3. 用实体 + 图谱关系做向量语义检索（文本片段 = 血肉）
4. Context = [图谱关系链] + [向量检索文本片段]
5. 填充到Prompt模板，请求大模型生成最终结果
6. 结果中标注来源（文档文件 / URL / 知识图谱）
"""
import os
import re
import time
import json
import datetime
import sqlite3
import glob
from typing import Dict, List, Any, Optional
from openai import OpenAI
from config import config
from knowledge_graph import KnowledgeGraphManager
from vector_db import VectorDBManager
from langchain_community.document_loaders import (
    TextLoader, PyPDFLoader, Docx2txtLoader, UnstructuredMarkdownLoader
)


class GraphRAGSystem:
    def __init__(self, kg_manager=None, vdb_manager=None):
        self.kg = kg_manager or KnowledgeGraphManager()
        self.vdb = vdb_manager or VectorDBManager()
        self.openai_client = OpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY", config.TONGYI_KEY),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self.max_tokens = 2048
        self.max_kg_results = 15
        self.max_vdb_results = 8
        self.max_context_length = 8000

    # ==================== 核心查询方法 ====================
    def query(self, user_input: str, depth: int = 2,
              similarity_threshold: float = 0.75, top_k: int = 5,
              prompt_template: str = None) -> Dict:
        """
        GraphRAG 核心查询流程

        参数:
            user_input: 用户健康画像文本 + 可选的用户提问
            depth: 知识图谱查询深度
            similarity_threshold: 相似度阈值
            top_k: 返回的最相似结果数量
            prompt_template: 外部传入的Prompt模板内容（可选）
        """
        start_time = time.time()
        print(f"\n{'='*60}")
        print(f"🔍 GraphRAG 查询开始")
        print(f"{'='*60}")

        # ======= Step 1: 从用户输入中提取关键实体 =======
        print("\n📌 Step 1: 提取关键实体...")
        entities = self._extract_key_entities(user_input)
        print(f"   提取到 {len(entities)} 个实体: {entities[:10]}")

        # ======= Step 2: 用实体查询知识图谱子图（骨架）=======
        print("\n📌 Step 2: 查询知识图谱子图...")
        kg_results = []
        kg_relations_text = ""

        # 方式1: 通过process_user_query进行图谱检索
        try:
            kg_results = self.kg.process_user_query(
                user_input, save_to_db=False, depth=depth,
                similarity_threshold=similarity_threshold, top_k=top_k
            )
            if kg_results:
                print(f"   图谱检索: 找到 {len(kg_results)} 条关系")
        except Exception as e:
            print(f"   ⚠️ 图谱检索异常: {e}")

        # 方式2: 直接用提取的实体搜索图谱节点和关系
        try:
            for entity in entities[:8]:  # 限制实体数量避免过慢
                search_res = self.kg.search_nodes(entity)
                if search_res and isinstance(search_res, list):
                    for item in search_res[:3]:
                        if item not in kg_results:
                            kg_results.append(item)
        except Exception as e:
            print(f"   ⚠️ 实体搜索异常: {e}")

        # 格式化图谱关系链（骨架）
        if kg_results:
            kg_relations_text = self._format_kg_results(kg_results)
            print(f"   图谱关系链: {len(kg_results)} 条")
        else:
            kg_relations_text = "暂无知识图谱匹配结果"
            print("   图谱关系链: 无匹配")

        # ======= Step 3: 向量语义检索（血肉）=======
        print("\n📌 Step 3: 向量语义检索...")
        vdb_results = []

        # 构建检索查询：用户输入 + 提取的实体 + 图谱关键词
        search_queries = [user_input]
        # 加入实体作为补充查询
        for entity in entities[:5]:
            search_queries.append(entity)

        try:
            if self.vdb.is_initialized:
                # 主查询
                main_results = self.vdb.hybrid_search(user_input, k=top_k * 2)
                vdb_results.extend(main_results)

                # 实体补充查询（去重）
                seen_contents = set()
                for doc in vdb_results:
                    seen_contents.add(doc.page_content[:100])

                for entity in entities[:5]:
                    try:
                        extra = self.vdb.hybrid_search(entity, k=3)
                        for doc in extra:
                            if doc.page_content[:100] not in seen_contents:
                                vdb_results.append(doc)
                                seen_contents.add(doc.page_content[:100])
                    except:
                        pass

                print(f"   向量检索: 找到 {len(vdb_results)} 个文本片段")
            else:
                print("   ⚠️ 向量数据库未初始化")
        except Exception as e:
            print(f"   ⚠️ 向量检索异常: {e}")

        # 格式化向量检索结果（血肉），附带来源
        vdb_text = self._format_vdb_results(vdb_results)

        # ======= Step 4: 组装Context =======
        print("\n📌 Step 4: 组装Context...")
        # Context = [图谱关系链(骨架)] + [向量检索文本片段(血肉)]

        # ======= Step 5: 填充Prompt模板，调用大模型 =======
        print("\n📌 Step 5: 构建Prompt并调用大模型...")
        prompt = self._build_prompt(
            user_input, kg_relations_text, vdb_text, prompt_template
        )

        if len(prompt) > self.max_context_length:
            prompt = prompt[:self.max_context_length]

        # 调用大模型
        answer = self._call_llm(prompt)

        total_time = time.time() - start_time
        print(f"\n✅ GraphRAG 查询完成, 总耗时: {total_time:.2f}s")
        print(f"{'='*60}\n")

        return {
            "user_query": user_input,
            "answer": answer,
            "kg_results": kg_results[:self.max_kg_results] if kg_results else [],
            "vdb_results": [
                {
                    "content": doc.page_content[:500],
                    "source": doc.metadata.get('source', '未知来源')
                }
                for doc in vdb_results[:self.max_vdb_results]
            ] if vdb_results else [],
            "entities_extracted": entities,
            "processing_time": total_time,
        }

    # ==================== 实体提取 ====================
    def _extract_key_entities(self, text: str) -> List[str]:
        """从文本中提取关键医学实体（疾病、症状、药物、指标等）"""
        entities = []

        # 规则1: 提取中文医学关键词（基于常见模式）
        patterns = [
            r'(高血压|低血压|糖尿病|冠心病|心脏病|支气管炎|哮喘|肺炎|肝炎|肾炎|胃炎)',
            r'(头晕|头痛|胸闷|心悸|气短|咳嗽|发热|腹痛|腹泻|失眠|乏力|恶心)',
            r'(青霉素|阿司匹林|降压药|胰岛素|他汀|二甲双胍|硝苯地平)',
            r'(血压|血糖|血脂|胆固醇|尿酸|肌酐|血红蛋白|白细胞|血小板)',
            r'(BMI|LDL|HDL|HbA1c)',
            r'(手术|过敏|家族史|吸烟|饮酒)',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text)
            entities.extend(matches)

        # 规则2: 从"主诊断:"、"健康状况:"等字段提取
        field_patterns = [
            r'主诊断[：:]\s*(.+?)(?:\n|$)',
            r'健康状况[：:]\s*(.+?)(?:\n|$)',
            r'过敏史[：:]\s*(.+?)(?:\n|$)',
            r'疾病史[：:]\s*(.+?)(?:\n|$)',
            r'家族病史[：:]\s*(.+?)(?:\n|$)',
            r'用药情况[：:]\s*(.+?)(?:\n|$)',
        ]
        for pattern in field_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if match and match != '无' and match != '无特殊记录' and match != '-':
                    # 分割逗号/顿号分隔的多个实体
                    sub_entities = re.split(r'[，,、;；]', match)
                    entities.extend([e.strip() for e in sub_entities if e.strip()])

        # 规则3: 从用户补充信息中提取
        supplement_match = re.search(r'用户补充信息[：:]\s*(.+?)(?:\n|$)', text)
        if supplement_match:
            supplement = supplement_match.group(1)
            # 简单分词
            words = re.split(r'[，,、。！？\s]+', supplement)
            entities.extend([w for w in words if len(w) >= 2])

        # 去重并过滤
        seen = set()
        result = []
        for e in entities:
            e = e.strip()
            if e and e not in seen and len(e) >= 2:
                seen.add(e)
                result.append(e)

        return result

    # ==================== 格式化知识图谱结果 ====================
    def _format_kg_results(self, kg_results: List) -> str:
        """将图谱查询结果格式化为关系链文本"""
        if not kg_results:
            return "暂无知识图谱匹配结果"

        lines = []
        seen = set()
        for i, record in enumerate(kg_results[:self.max_kg_results]):
            if isinstance(record, dict):
                src = record.get('source', record.get('name', ''))
                rel = record.get('relationship', record.get('type', ''))
                tgt = record.get('target', '')
                src_type = record.get('source_type', '')
                tgt_type = record.get('target_type', '')

                if src and rel and tgt:
                    key = f"{src}-{rel}-{tgt}"
                    if key not in seen:
                        seen.add(key)
                        line = f"- [{src_type}]{src} --[{rel}]--> [{tgt_type}]{tgt}"
                        lines.append(line)
                elif src:
                    # 单节点搜索结果
                    key = f"node:{src}"
                    if key not in seen:
                        seen.add(key)
                        lines.append(f"- 实体: {src} (类型: {src_type or '未知'})")
            elif isinstance(record, str):
                if record not in seen:
                    seen.add(record)
                    lines.append(f"- {record}")

        if not lines:
            return "暂无知识图谱匹配结果"

        return "\n".join(lines)

    # ==================== 格式化向量检索结果 ====================
    def _format_vdb_results(self, vdb_results: List) -> str:
        """将向量检索结果格式化为带来源的文本片段"""
        if not vdb_results:
            return "暂无向量匹配结果"

        lines = []
        for i, doc in enumerate(vdb_results[:self.max_vdb_results]):
            source = doc.metadata.get('source', '未知来源')
            content = doc.page_content[:500].strip()

            # 判断来源类型
            if source.startswith('http://') or source.startswith('https://'):
                source_label = f"[在线文档]({source})"
            elif os.path.exists(str(source)):
                source_label = f"[本地文档: {os.path.basename(source)}]"
            else:
                source_label = f"[来源: {os.path.basename(str(source))}]"

            lines.append(f"**片段{i+1}** {source_label}\n{content}\n")

        return "\n".join(lines)

    # ==================== 构建Prompt ====================
    def _build_prompt(self, user_input: str, kg_text: str,
                      vdb_text: str, prompt_template: str = None) -> str:
        """构建最终Prompt，支持动态模板"""

        # 优先使用外部传入的模板
        if prompt_template:
            try:
                return prompt_template.format(
                    user_input=user_input,
                    kg_results=kg_text,
                    vdb_results=vdb_text,
                    current_date=datetime.datetime.now().strftime("%Y-%m-%d"),
                    user_name="用户"
                )
            except Exception as e:
                print(f"   ⚠️ 外部模板格式化失败: {e}")

        # 尝试从数据库获取激活的Prompt模板
        active_prompt = self._get_active_prompt_template()
        if active_prompt:
            try:
                return active_prompt['content'].format(
                    user_input=user_input,
                    kg_results=kg_text,
                    vdb_results=vdb_text,
                    current_date=datetime.datetime.now().strftime("%Y-%m-%d"),
                    user_name="用户"
                )
            except Exception as e:
                print(f"   ⚠️ 数据库模板格式化失败: {e}")

        # 默认模板
        return f"""你是一名资深健康知识助手。请基于以下用户健康画像、知识图谱关系链和相关文档片段，生成**个性化健康知识推送**。

## 严格要求
1. 先展示用户关键健康数据摘要
2. 分模块推送知识：疾病认知、饮食建议、运动建议、用药提醒、复查计划、注意事项
3. **每个知识点必须标注来源**：
   - 如果来自上传的文档，标注 [来源: 文档名称]
   - 如果来自在线URL文档，标注 [来源](完整URL)
   - 如果来自知识图谱，标注 [来源: 知识图谱]
   - 如果来自通用医学知识，标注 [来源: 医学常识] 并附权威网站链接
4. 以Markdown格式输出，使用小标题、列表、表情符号
5. 内容必须与用户实际健康状况强相关

---
### 👤 用户健康画像
{user_input}

---
### 🔗 知识图谱关系链（骨架知识）
{kg_text}

---
### 📄 相关文档片段（详细知识）
{vdb_text}

---
请开始生成专属健康知识推送，确保每个知识点都有来源标注："""

    # ==================== 调用大模型 ====================
    def _call_llm(self, prompt: str) -> str:
        """调用大模型生成回答"""
        try:
            print("   🧠 调用大模型...")
            llm_start = time.time()
            response = self.openai_client.chat.completions.create(
                model="qwen-plus",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "你是一名专业的医学健康知识助手。你的任务是基于患者的健康画像、"
                            "知识图谱关系链和相关文档片段，生成结构化、个性化的健康知识推送。"
                            "要求：详细、专业、准确，使用Markdown格式。"
                            "重要：必须为每个知识点标注来源（文档名称、URL链接或知识图谱）。"
                            "如果引用了文档内容，务必注明来源文件名或URL。"
                        )
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=0.35
            )
            answer = response.choices[0].message.content.strip()
            print(f"   大模型响应完成, 耗时 {time.time() - llm_start:.2f}s")
            return answer
        except Exception as e:
            print(f"   ❌ 大模型调用失败: {e}")
            return "抱歉，生成健康知识时出现问题，请稍后再试。"

    # ==================== 获取激活的Prompt模板 ====================
    def _get_active_prompt_template(self) -> Optional[Dict]:
        """从数据库获取当前激活的Prompt模板"""
        try:
            BASE_DIR = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(BASE_DIR, 'data/hospital.db')
            if not os.path.exists(db_path):
                return None
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute('SELECT * FROM prompt_templates WHERE is_active = 1')
            row = c.fetchone()
            conn.close()
            if row:
                return {'id': row['id'], 'name': row['name'], 'content': row['content']}
        except Exception as e:
            print(f"   ⚠️ 获取Prompt模板失败: {e}")
        return None

    # ==================== 知识库更新 ====================
    def update_knowledge_base(self, file_pattern: str) -> bool:
        """更新知识库"""
        print(f"🔄 更新知识库: {file_pattern}")
        vdb_success = self.vdb.update_from_files(file_pattern)
        if not vdb_success:
            print("❌ 向量数据库更新失败")
            return False

        print("📚 从文档中提取知识到图谱...")
        for file_path in glob.glob(file_pattern):
            try:
                if file_path.endswith('.pdf'):
                    loader = PyPDFLoader(file_path)
                elif file_path.endswith('.docx'):
                    loader = Docx2txtLoader(file_path)
                elif file_path.endswith('.md'):
                    loader = UnstructuredMarkdownLoader(file_path)
                elif file_path.endswith('.txt'):
                    loader = TextLoader(file_path)
                else:
                    continue
                docs = loader.load()
                for i, doc in enumerate(docs):
                    text = doc.page_content
                    if not text.strip():
                        continue
                    result = self.kg.extract_entities_relations(text)
                    if result.get("entities") or result.get("relationships"):
                        self.kg.save_to_neo4j(result.get("entities", []), result.get("relationships", []))
            except Exception as e:
                print(f"❌ 处理文件失败 {file_path}: {e}")
        print("✅ 知识库更新完成")
        return True


if __name__ == "__main__":
    print("🚀 启动GraphRAG系统测试...")
    kg_manager = KnowledgeGraphManager()
    vdb_manager = VectorDBManager()
    graph_rag = GraphRAGSystem(kg_manager, vdb_manager)
    response = graph_rag.query("患者张伟，42岁，男，轻度高血压，过敏青霉素")
    print(f"\n💡 回答:\n{response['answer']}")
