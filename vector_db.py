import glob
import os
import sqlite3
import time
import traceback
from datetime import datetime
from typing import List, Any, Optional, Callable
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import (
    TextLoader, PyPDFLoader, Docx2txtLoader, UnstructuredMarkdownLoader,
    UnstructuredWordDocumentLoader  # 新增对 doc 文件的支持
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from config import config
import requests
import json
import numpy as np

class TongyiEmbeddings:
    """通义千问嵌入模型API封装"""

    def __init__(self):
        self.api_url = "https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding"
        self.api_key = config.TONGYI_KEY
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.model = "text-embedding-v1"  # 通义千问嵌入模型

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """批量嵌入文档"""
        # 分批处理避免API限制
        batch_size = 10
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            embeddings = [self.embed_query(text) for text in batch]
            all_embeddings.extend(embeddings)
            time.sleep(0.1)  # 避免API速率限制

        return all_embeddings

    def embed_query(self, text: str) -> List[float]:
        """嵌入单个查询文本"""
        payload = {
            "model": self.model,
            "input": {
                "texts": [text]
            }
        }

        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                data=json.dumps(payload),
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            if "output" in data and "embeddings" in data["output"]:
                return data["output"]["embeddings"][0]["embedding"]
            else:
                print(f"API响应格式错误: {data}")
                return self._fallback_embedding()
        except requests.exceptions.RequestException as e:
            print(f"嵌入API调用失败: {str(e)}")
            return self._fallback_embedding()
        except json.JSONDecodeError:
            print("API响应JSON解析失败")
            return self._fallback_embedding()

    def _fallback_embedding(self, dim=1536) -> List[float]:
        """API失败时的回退方案"""
        return list(np.random.rand(dim).astype(np.float32))


class VectorDBManager:
    def __init__(self):
        self.stats = None
        self.embedding = TongyiEmbeddings()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP
        )
        self.vector_db = self._init_vector_db()
        self.is_initialized = self.vector_db is not None

    def _init_vector_db(self) -> Optional[Chroma]:
        """初始化或加载现有向量数据库"""
        try:
            if os.path.exists(config.VECTOR_DB_PATH):
                print("加载现有向量数据库...")
                return Chroma(
                    persist_directory=config.VECTOR_DB_PATH,
                    embedding_function=self.embedding
                )
            print("未找到现有向量数据库，请先加载文档")
            return None
        except Exception as e:
            print(f"向量数据库初始化失败: {str(e)}")
            return None

    def _load_documents(self, file_path: str) -> List[Any]:
        print(f"加载文件: {file_path}")
        try:
            # 支持更多文件类型
            file_ext = os.path.splitext(file_path)[1].lower()

            if file_ext == '.pdf':
                return PyPDFLoader(file_path).load()
            elif file_ext in ['.docx', '.doc']:
                # 统一处理 Word 文档
                return UnstructuredWordDocumentLoader(file_path).load()
            elif file_ext == '.md':
                return UnstructuredMarkdownLoader(file_path).load()
            elif file_ext == '.txt':
                return TextLoader(file_path).load()
            else:
                print(f"⚠️ 不支持的文件类型: {file_path}")
                return []
        except Exception as e:
            print(f"文件加载失败: {file_path}, 错误: {str(e)}")
            return []

    def update_from_files(self, file_pattern: str) -> bool:
        """挂载外部文件更新向量数据库"""
        all_docs = []
        processed_files = 0
        skipped_files = 0

        for file_path in glob.glob(file_pattern):
            raw_docs = self._load_documents(file_path)
            if not raw_docs:
                skipped_files += 1
                continue

            docs = self.text_splitter.split_documents(raw_docs)
            all_docs.extend(docs)
            processed_files += 1
            print(f"✅ 已处理: {file_path} -> {len(docs)}个片段")

        print(f"总计: 处理{processed_files}个文件, 跳过{skipped_files}个文件, 共生成{len(all_docs)}个文本片段")

        if not all_docs:
            print("⚠️ 未找到有效文档，向量数据库未更新")
            return False

        try:
            # 分批处理避免内存溢出
            batch_size = 20
            batches = [all_docs[i:i + batch_size] for i in range(0, len(all_docs), batch_size)]

            print(f"开始嵌入处理 ({len(batches)}批, 每批{batch_size}个文档)...")

            # 创建新的向量数据库
            self.vector_db = Chroma.from_documents(
                documents=batches[0],
                embedding=self.embedding,
                persist_directory=config.VECTOR_DB_PATH
            )

            # 添加剩余批次
            for i, batch in enumerate(batches[1:]):
                print(f"处理批次 {i + 2}/{len(batches)}...")
                self.vector_db.add_documents(
                    documents=batch,
                    embedding=self.embedding
                )

            print(f"✅ 向量数据库更新完成，存储在: {config.VECTOR_DB_PATH}")
            self.is_initialized = True
            return True
        except Exception as e:
            print(f"❌ 向量数据库更新失败: {str(e)}")
            self.is_initialized = False
            return False

    def similarity_search(self, query: str, k: int = config.VECTOR_TOP_K) -> List[Any]:
        """执行相似性搜索"""
        if not self.is_initialized:
            raise ValueError("向量数据库未初始化，请先加载文档")

        print(f"执行相似性搜索: '{query}'")
        try:
            return self.vector_db.similarity_search(query, k=k)
        except Exception as e:
            print(f"搜索失败: {str(e)}")
            return []

    def hybrid_search(self, query: str, k: int = config.VECTOR_TOP_K) -> List[Any]:
        """混合检索：相似性 + MMR多样性"""
        if not self.is_initialized:
            raise ValueError("向量数据库未初始化，请先加载文档")

        print(f"执行混合检索: '{query}'")

        try:
            # 相似性搜索
            sim_results = self.vector_db.similarity_search(query, k=k * 2)

            # 最大边际相关性搜索（增强多样性）
            mmr_results = self.vector_db.max_marginal_relevance_search(query, k=k)

            # 合并并去重
            combined = {}
            for doc in sim_results + mmr_results:
                content = doc.page_content
                if content not in combined:
                    combined[content] = doc

            # 按相关性排序
            unique_results = list(combined.values())
            return sorted(
                unique_results,
                key=lambda x: x.metadata.get('relevance_score', 0),
                reverse=True
            )[:k]
        except Exception as e:
            print(f"混合搜索失败: {str(e)}")
            return []

    def get_stats(self) -> dict:
        """获取向量数据库详细统计信息"""
        try:
            # 如果向量数据库未初始化，尝试初始化
            if not self.is_initialized and not self._init_vector_db():
                return {
                    "status": "not_initialized",
                    "message": "请先加载文档",
                    "last_updated": "N/A",
                    "document_count": 0,
                    "chunk_count": 0,
                    "chunk_size": config.CHUNK_SIZE,
                    "embedding_model": "Tongyi-Text-Embedding-V1",
                    "embedding_dimension": 1536,
                    "db_size": "0 MB"
                }

            collection = self.vector_db._collection
            if not collection:
                return {
                    "status": "no_collection",
                    "last_updated": "N/A",
                    "document_count": 0,
                    "chunk_count": 0,
                    "chunk_size": config.CHUNK_SIZE,
                    "embedding_model": "Tongyi-Text-Embedding-V1",
                    "embedding_dimension": 1536,
                    "db_size": "0 MB"
                }

            # 获取文档数量
            document_count = collection.count()

            # 获取分块数量（实际存储的向量数量）
            chunk_count = len(collection.get()['ids']) if collection.get() else 0

            # 获取数据库大小
            db_size = self._get_db_size()

            # 获取最后更新时间
            last_updated = self._get_last_updated_time()

            return {
                "status": "active",
                "last_updated": last_updated,
                "document_count": document_count,
                "chunk_count": chunk_count,
                "chunk_size": config.CHUNK_SIZE,
                "embedding_model": "Tongyi-Text-Embedding-V1",
                "embedding_dimension": 1536,
                "db_size": db_size
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "last_updated": "N/A",
                "document_count": 0,
                "chunk_count": 0,
                "chunk_size": config.CHUNK_SIZE,
                "embedding_model": "N/A",
                "embedding_dimension": "N/A",
                "db_size": "0 MB"
            }

    def _get_db_size(self) -> str:
        """获取向量数据库目录大小"""
        total_size = 0
        try:
            for dirpath, _, filenames in os.walk(config.VECTOR_DB_PATH):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if os.path.exists(fp):
                        total_size += os.path.getsize(fp)

            # 转换为MB
            size_mb = total_size / (1024 * 1024)
            return f"{size_mb:.2f} MB"
        except:
            return "N/A"

    def _get_last_updated_time(self) -> str:
        """获取最后更新时间"""
        try:
            # 尝试从元数据获取最后更新时间
            meta_file = os.path.join(config.VECTOR_DB_PATH, "chroma.sqlite3")
            if not os.path.exists(meta_file):
                return "N/A"

            # 连接到SQLite数据库
            conn = sqlite3.connect(meta_file)
            c = conn.cursor()

            # 查询最后更新时间
            c.execute("SELECT MAX(timestamp) FROM embeddings_fulltext")
            result = c.fetchone()
            conn.close()

            if result and result[0]:
                timestamp = result[0] / 1000  # 毫秒转秒
                return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
            return "N/A"
        except:
            return "N/A"

    def update_single_file(self, file_path: str, tags: str = "", log_callback: Callable = None) -> bool:
        """处理单个文件更新向量数据库并关联标签"""
        try:
            if log_callback:
                log_callback(f"开始处理文件: {os.path.basename(file_path)}")
                log_callback(f"文件路径: {file_path}")
                log_callback(f"关联标签: {tags}")

            # 加载文档
            if log_callback:
                log_callback("加载文档内容...")
            raw_docs = self._load_documents(file_path)

            if not raw_docs:
                msg = f"⚠️ 未找到有效内容: {file_path}"
                if log_callback: log_callback(msg)
                print(msg)
                return False

            # 确保文件是有效的
            if not any(doc.page_content.strip() for doc in raw_docs):
                msg = f"⚠️ 文件内容为空: {file_path}"
                if log_callback: log_callback(msg)
                print(msg)
                return False

            if log_callback:
                log_callback(f"✅ 已加载文档: {file_path}")
                log_callback(f"原始文本块数: {len(raw_docs)}")

            # 分割文档
            if log_callback:
                log_callback("分割文档内容...")
            docs = self.text_splitter.split_documents(raw_docs)

            if not docs:
                msg = "⚠️ 未生成有效文本片段"
                if log_callback: log_callback(msg)
                print(msg)
                return False

            if log_callback:
                log_callback(f"✅ 已分割为 {len(docs)} 个文本片段")
                log_callback(f"文本片段示例: {docs[0].page_content[:100]}...")

            # 为每个文档片段添加标签元数据
            for doc in docs:
                doc.metadata['tags'] = tags

            # 分批处理避免内存溢出
            batch_size = 5
            batches = [docs[i:i + batch_size] for i in range(0, len(docs), batch_size)]

            if log_callback:
                log_callback(f"准备分批处理 ({len(batches)}批, 每批{batch_size}个文档)...")

            # 如果向量数据库不存在，创建新的
            if not self.is_initialized or not self.vector_db:
                if log_callback:
                    log_callback("创建新的向量数据库...")
                try:
                    self.vector_db = Chroma.from_documents(
                        documents=batches[0],
                        embedding=self.embedding,
                        persist_directory=config.VECTOR_DB_PATH
                    )
                    start_index = 1
                    if log_callback:
                        log_callback("✅ 向量数据库创建成功")
                except Exception as e:
                    error_msg = f"❌ 创建向量数据库失败: {str(e)}"
                    if log_callback: log_callback(error_msg)
                    print(error_msg)
                    return False
            else:
                start_index = 0

            print(f"[DEBUG] 文档加载完成，共 {len(raw_docs)} 个原始段落")
            print(f"[DEBUG] 分割完成，共 {len(docs)} 个文本片段")
            # 添加剩余批次
            for i, batch in enumerate(batches[start_index:]):
                batch_num = i + 1 + start_index
                if log_callback:
                    log_callback(f"处理批次 {batch_num}/{len(batches)}...")

                try:
                    self.vector_db.add_documents(
                        documents=batch,
                        embedding=self.embedding
                    )

                    if log_callback:
                        log_callback(f"✅ 批次 {batch_num} 处理完成")
                        log_callback(f"本批次处理了 {len(batch)} 个文本片段")

                    # 添加延迟避免API速率限制
                    time.sleep(1)
                except Exception as e:
                    error_msg = f"❌ 批次 {batch_num} 处理失败: {str(e)}"
                    if log_callback: log_callback(error_msg)
                    print(error_msg)
                    return False

            # 持久化向量数据库
            self.vector_db.persist()
            success_msg = f"✅ 向量数据库更新完成，存储在: {config.VECTOR_DB_PATH}"
            if log_callback: log_callback(success_msg)
            print(success_msg)
            self.is_initialized = True

            # 更新统计信息
            self.update_stats()
            if log_callback:
                log_callback("向量化处理完成!")
            return True
        except Exception as e:
            error_msg = f"❌ 向量数据库更新失败: {str(e)}"
            if log_callback: log_callback(error_msg)
            print(error_msg)
            traceback.print_exc()
            self.is_initialized = False
            return False

    def update_stats(self):
        """更新向量数据库统计信息"""
        self.stats = self.get_stats()


# 使用示例
if __name__ == "__main__":
    vdb = VectorDBManager()

    # 检查数据库状态
    stats = vdb.get_stats()
    print("\n向量数据库状态:")
    for k, v in stats.items():
        print(f"{k}: {v}")

    success = vdb.update_from_files("/Users/local/GraphRAG/MedicalRAG/documents/量子计算原理.docx")

    # # 如果未初始化，则加载文档
    # if not vdb.is_initialized:
    #     print("\n尝试加载文档...")
    #     success = vdb.update_from_files("/Users/local/GraphRAG/MedicalRAG/documents/量子计算原理.docx")
    #     if not success:
    #         print("文档加载失败，请检查文件路径")
    #         exit(1)

    # 获取统计信息
    stats = vdb.get_stats()
    print("\n向量数据库统计信息:")
    for k, v in stats.items():
        print(f"{k}: {v}")

    # 执行搜索
    try:
        results = vdb.hybrid_search("量子计算原理")
        print(f"\n检索结果 ({len(results)}):")
        for i, doc in enumerate(results):
            print(f"\n结果 {i + 1} [分数: {doc.metadata.get('relevance_score', 0):.3f}]:")
            print(doc.page_content)
    except ValueError as e:
        print(f"\n错误: {str(e)}")
