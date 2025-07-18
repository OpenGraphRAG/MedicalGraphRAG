import os
import json


class Config:
    # 配置文件路径
    CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')

    # 默认配置
    DEFAULT_CONFIG = {
        # 向量数据库配置
        "VECTOR_DB_TYPE": "Chroma",
        "VECTOR_DB_PATH": "vector_db",

        # 图数据库配置
        "GRAPH_DB_TYPE": "Neo4j",
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "neo4j123",

        # 大模型配置
        "LLM_PROVIDER": "DeepSeek",
        "DEEPSEEK_API": "https://api.deepseek.cn/v1/chat/completions",
        "DEEPSEEK_KEY": "your_api_key",
        "TONGYI_API": "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
        "TONGYI_KEY": "",

        # 知识图谱配置
        "KNOWLEDGE_INDEX": "knowledge_index/kg_vector_index.pkl",
        "KG_SCHEMA": "schema/kg_schema.json",

        # 其他API密钥
        "GUIJI_KEY": "",

        # 文件路径配置
        "EXTERNAL_FILE": "documents",
        "DOCUMENTS_DIR": os.path.join(os.path.dirname(os.path.abspath(__file__)), 'documents'),
        "SQLITE_DB_PATH": os.path.join(os.path.dirname(os.path.abspath(__file__)), 'knowledge.db'),

        # 模型配置
        "EMBEDDING_URL": "https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding",
        "EMBEDDING_MODEL": "text-embedding-v1",

        # 文本处理配置
        "CHUNK_SIZE": 1000,
        "CHUNK_OVERLAP": 100,

        # 检索配置
        "VECTOR_TOP_K": 5,
        "GRAPH_TOP_K": 10,

        # 文件类型配置
        "ALLOWED_EXTENSIONS": ['txt', 'pdf', 'doc', 'docx', 'md'],
        "FILE_MIME_TYPES": {
            'pdf': 'application/pdf',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'doc': 'application/msword',
            'txt': 'text/plain',
            'md': 'text/markdown',
            'rtf': 'application/rtf',
            'odt': 'application/vnd.oasis.opendocument.text',
            'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'html': 'text/html'
        }
    }

    def __init__(self):
        # 如果配置文件存在，则加载
        if os.path.exists(self.CONFIG_FILE):
            self.load_config()
        else:
            # 否则使用默认配置并保存
            self.config = self.DEFAULT_CONFIG.copy()
            self.save_config()

        # 确保文档目录存在
        os.makedirs(self.config['DOCUMENTS_DIR'], exist_ok=True)

    def load_config(self):
        """从JSON文件加载配置"""
        try:
            with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except Exception as e:
            print(f"加载配置文件失败: {str(e)}，使用默认配置")
            self.config = self.DEFAULT_CONFIG.copy()

    def save_config(self):
        """保存配置到JSON文件"""
        try:
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置文件失败: {str(e)}")

    def update_config(self, new_config):
        """更新配置"""
        for key, value in new_config.items():
            if key in self.config:
                # 处理特殊类型转换
                if key in ['CHUNK_SIZE', 'CHUNK_OVERLAP', 'VECTOR_TOP_K', 'GRAPH_TOP_K']:
                    self.config[key] = int(value)
                elif key == 'ALLOWED_EXTENSIONS':
                    self.config[key] = [ext.strip() for ext in value.split(',')]
                else:
                    self.config[key] = value

        self.save_config()

    def get_config(self):
        """获取当前配置"""
        return self.config

    def __getattr__(self, name):
        """通过属性访问配置值"""
        if name in self.config:
            return self.config[name]
        else:
            raise AttributeError(f"Config has no attribute '{name}'")


# 创建全局配置对象
config = Config()
