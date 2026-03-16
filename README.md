# MedicalGraphRAG 项目文档
## 感谢各位starter
[![Stargazers repo roster for @OpenGraphRAG/MedicalGraphRAG](https://reporoster.com/stars/OpenGraphRAG/MedicalGraphRAG)](https://github.com/OpenGraphRAG/MedicalGraphRAG/stargazers)
# MedicalGraphRAG — 基于 GraphRAG 的智能医学健康知识平台

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.3+-green.svg)](https://flask.palletsprojects.com/)
[![Neo4j](https://img.shields.io/badge/Neo4j-5.0+-orange.svg)](https://neo4j.com/)
[![LangChain](https://img.shields.io/badge/LangChain-0.2+-purple.svg)](https://python.langchain.com/)
[![License](https://img.shields.io/badge/License-Apache_2.0-red.svg)](LICENSE)

---

## 一、📖 项目简介

MedicalGraphRAG 是一个基于 **Graph + RAG（检索增强生成）** 架构的智能医学健康知识平台。系统通过整合医学文献、临床指南和在线医学资源，构建结构化的 **Neo4j 知识图谱** 与 **ChromaDB 向量知识库**，并利用大模型（通义千问）实现个性化健康知识推送、医学影像智能分析和辅助诊断决策。

### 🔬 GraphRAG 核心思想

系统严格遵循 GraphRAG 的五步流程：

```
用户健康信息 → ①实体提取 → ②知识图谱子图查询(骨架) → ③向量语义检索(血肉) 
             → ④Context = [图谱关系链] + [文本片段] → ⑤大模型生成
```

- **图谱关系链** 提供结构化骨架（疾病→症状→药物→注意事项）
- **向量检索文本** 提供详细血肉（文献原文、指南段落、在线资料）
- **大模型** 融合两者生成个性化、有来源标注的健康知识推送

### 🎯 核心功能

| 模块 | 功能 | 说明 |
|------|------|------|
| 🏥 健康画像 | 多维度健康档案 + SVG数字孪生人体 | 20+维度数据卡片，异常部位实时标红 |
| 💡 知识推送 | GraphRAG个性化健康知识生成 | 无需输入问题即可基于画像自动推送 |
| 🔬 影像分析 | 多模态AI医学影像/伤患图片诊断 | 上传即分析，结果可同步至健康档案 |
| 📊 知识图谱 | Neo4j可视化 + 文本三元组抽取 | Vis.js交互式网络，支持最短路径/中心性分析 |
| 📚 知识库 | 多格式文档上传 + URL爬取 + 向量化 | WebSocket实时进度，支持doc/docx/pdf/xlsx/md/txt |
| ⚙️ 系统管理 | Prompt模板管理 + 实体属性配置 + 系统设置 | 配置即时生效，无需重启 |

---

## 二、🏗️ 系统架构

### 系统架构图
<img width="1902" height="942" alt="image" src="https://github.com/user-attachments/assets/49415d4f-d83a-4ca6-a892-d9cc0779b914" />

### 模块架构图
<img width="1902" height="942" alt="image" src="https://github.com/user-attachments/assets/f5aee87d-8d4d-4b43-b317-92a03b6dbad8" />

### 数据流架构
<img width="1902" height="942" alt="image" src="https://github.com/user-attachments/assets/a13f6165-64f1-406f-8fb6-f58fcc8d54db" />

### 部署架构图
<img width="1902" height="942" alt="image" src="https://github.com/user-attachments/assets/3479eaff-8c9e-47a6-ba74-8c96a5f62a0d" />

### demo    
<img width="1897" height="907" alt="image" src="https://github.com/user-attachments/assets/98fb4497-64f0-40df-a5a5-4b015a5f52cf" />

<img width="1918" height="907" alt="image" src="https://github.com/user-attachments/assets/b33b88c9-6ca4-4c9c-bb28-59452539a679" />

<img width="1896" height="905" alt="image" src="https://github.com/user-attachments/assets/eb1cdefa-a1e8-4f45-954c-cb27f3641fb6" />

<img width="1904" height="910" alt="image" src="https://github.com/user-attachments/assets/4ed3ca7e-f0c3-43ad-bf1e-34d65f74cca9" />

<img width="1916" height="896" alt="image" src="https://github.com/user-attachments/assets/b13644b7-cbc6-4e58-87bf-4baebf826cf8" />

<img width="1896" height="905" alt="image" src="https://github.com/user-attachments/assets/1731f6f6-6d43-43a2-8c9c-0f8f4642bc47" />

<img width="1886" height="898" alt="image" src="https://github.com/user-attachments/assets/b1b5c3b7-8c0b-4b5d-81d5-259d913e4e87" />

<img width="1912" height="896" alt="image" src="https://github.com/user-attachments/assets/842dd764-c229-4a99-94a0-36338319de02" />

<img width="1916" height="908" alt="image" src="https://github.com/user-attachments/assets/6516abe1-f393-4fe8-bddb-89a95f9a76f9" />

<img width="1904" height="908" alt="image" src="https://github.com/user-attachments/assets/c04bb7ae-668a-4316-8442-58d817acb1ae" />

### 2.1 技术栈

| 层级 | 技术 |
|------|------|
| **前端** | HTML5 + CSS3 + JavaScript（赛博朋克暗色主题）、SVG数字孪生、Vis.js图谱可视化、Particles.js粒子背景、Marked.js Markdown渲染 |
| **后端** | Python 3.9+、Flask 2.3+、Flask-SocketIO（WebSocket）|
| **图数据库** | Neo4j 5.0+（知识图谱存储与查询）|
| **向量数据库** | ChromaDB（文档向量化与语义检索）|
| **元数据库** | SQLite（用户、文档、模板、影像分析记录）|
| **大模型** | 通义千问 qwen-plus（文本生成）、qwen-vl-plus（多模态影像分析）、text-embedding-v1（文本嵌入）|
| **文档处理** | LangChain（PyPDF、Docx2txt、Unstructured）、BeautifulSoup（URL爬取）|

### 2.2 数据流架构

```
┌─────────────────────────────────────────────────────────┐
│                    前台（患者端）                          │
│  登录/注册 → 健康画像 → 知识推送 → 影像分析 → 个人设置    │
└────────┬──────────┬──────────┬───────────────────────────┘
         │          │          │
         ▼          ▼          ▼
┌──────────┐ ┌───────────┐ ┌──────────────┐
│ SQLite   │ │ GraphRAG  │ │ 多模态大模型  │
│ 用户档案  │ │   Engine  │ │ qwen-vl-plus │
└──────────┘ └─────┬─────┘ └──────────────┘
                   │
         ┌─────────┼─────────┐
         ▼         ▼         ▼
   ┌──────────┐ ┌───────┐ ┌──────────┐
   │ Neo4j KG │ │ChromaDB│ │ 通义千问  │
   │ 知识图谱  │ │向量检索 │ │ qwen-plus│
   └──────────┘ └───────┘ └──────────┘
         ▲                    ▲
         │                    │
┌────────┴────────────────────┴──────────┐
│               后台（管理端）              │
│ 用户档案管理 → 知识库管理 → 知识图谱管理  │
│ 实体属性配置 → Prompt模板 → 系统设置      │
└────────────────────────────────────────┘
```

---

## 三、📁 项目结构

```
MedicalGraphRAG/
├── app.py                          # Flask 主程序（70个路由）
├── rag_system.py                   # GraphRAG 核心引擎（5步流程）
├── knowledge_graph.py              # Neo4j 知识图谱管理器
├── vector_db.py                    # ChromaDB 向量数据库管理器
├── config.py                       # 配置管理类（热重载）
├── config.json                     # ⚠️ 核心配置文件
├── models.py                       # SQLAlchemy 数据模型
├── requirements.txt                # Python 依赖
│
├── templates/                      # Jinja2 模板（14个页面）
│   ├── base.html                   # 基础布局模板
│   │── 前台页面 ──
│   ├── login.html                  # 患者登录（赛博朋克风格）
│   ├── register.html               # 患者注册
│   ├── health_profile.html         # 健康画像 + SVG数字孪生
│   ├── diagnosis.html              # GraphRAG 知识推送
│   ├── image_analysis.html         # AI 医学影像分析
│   ├── profile_settings.html       # 个人设置
│   │── 后台页面 ──
│   ├── admin_login.html            # 管理员独立登录
│   ├── admin_dashboard.html        # 用户健康档案管理
│   ├── knowledge_management.html   # 知识库文档管理
│   ├── knowledge_graph.html        # 知识图谱可视化
│   ├── entity_config.html          # 实体关系属性配置
│   ├── prompt_templates.html       # Prompt 模板管理
│   └── system_settings.html        # 系统配置
│
├── static/
│   ├── css/                        # 样式文件（8个）
│   │   ├── style.css               # 基础全局样式
│   │   ├── health_profile.css      # 健康画像赛博朋克风格
│   │   ├── diagnosis.css           # 知识推送页面风格
│   │   ├── admin.css               # 后台管理布局
│   │   ├── knowledge.css           # 知识库管理
│   │   ├── knowledge_graph.css     # 知识图谱可视化+详情卡片
│   │   ├── entity_config.css       # 实体属性配置
│   │   └── system_settings.css     # 系统设置
│   └── js/                         # 脚本文件（9个）
│       ├── main.js                 # 全局基础交互
│       ├── diagnosis.js            # 知识推送逻辑
│       ├── health_profile.js       # 健康画像辅助
│       ├── admin.js                # 用户档案管理CRUD
│       ├── knowledge.js            # 知识库上传/向量化
│       ├── knowledge_graph.js      # 图谱可视化/查询（1700+行）
│       ├── entity_config.js        # 三元组分页编辑
│       ├── prompt_templates.js     # Prompt模板CRUD
│       └── system_settings.js      # 系统配置保存/重置
│
├── documents/                      # 上传文档存储（自动创建）
├── data/
│   └── hospital.db                 # SQLite 数据库（自动创建）
├── vector_db/                      # ChromaDB 持久化目录（自动创建）
├── knowledge_index/                # KG 向量索引（自动创建）
│   └── kg_vector_index.pkl
├── schema/
│   └── kg_schema.json              # 知识图谱 Schema 定义
└── nltk_data/                      # NLTK 分词数据
```

### 数据库表结构（SQLite - 7张表）

| 表名 | 用途 | 核心字段 |
|------|------|----------|
| `patients` | 用户健康档案 | 姓名、手机号、年龄、性别、身高体重、血压、诊断、过敏史、疾病史、用药等24个字段 |
| `admins` | 管理员账号 | 用户名、密码（哈希） |
| `medical_records` | 就诊记录 | 日期、科室、医生、描述 |
| `check_metrics` | 检查指标 | 项目、结果、参考范围、单位、状态 |
| `knowledge_documents` | 知识文档 | 名称、类型(file/url)、路径、标签、是否已向量化 |
| `prompt_templates` | Prompt模板 | 名称、内容、分类、是否激活 |
| `image_analyses` | 影像分析记录 | 患者ID、图片类型、分析结果、是否同步到档案 |

---

## 四、🚀 快速开始

### 4.1 环境要求

- Python 3.9+
- Neo4j 5.0+（本地或远程）
- 阿里云百炼平台 API 密钥（[获取地址](https://dashscope.console.aliyun.com/)）

### 4.2 安装部署

```bash
# 1. 克隆项目
git clone https://github.com/OpenGraphRAG/MedicalGraphRAG.git
cd MedicalGraphRAG

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate      # Linux/macOS
# .\venv\Scripts\activate     # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 下载 NLTK 数据
python -c "import nltk; nltk.download('punkt', download_dir='./nltk_data')"

# 5. 准备 Schema 文件
mkdir -p schema
# 将 kg_schema.json 放入 schema/ 目录
```

### 4.3 配置（⚠️ 必须修改）

编辑 `config.json`，至少修改以下三项：

```json
{
    "NEO4J_URI": "bolt://你的Neo4j地址:7687",
    "NEO4J_PASSWORD": "你的Neo4j密码",
    "TONGYI_KEY": "sk-你的百炼平台API密钥"
}
```

或通过环境变量设置 API 密钥（优先级更高）：
```bash
export DASHSCOPE_API_KEY="sk-你的密钥"
```

> **路径说明**：`config.json` 中的 `DOCUMENTS_DIR` 和 `SQLITE_DB_PATH` 无需修改，系统强制使用项目目录下的 `documents/` 和 `data/hospital.db`。

### 4.4 启动

```bash
python app.py
```

首次启动时系统会自动：
- 创建 `data/hospital.db` 并初始化7张数据表
- 创建默认管理员账号 `admin` / `admin123`
- 创建5个测试患者账号
- 创建3个默认 Prompt 模板
- 创建 `documents/`、`vector_db/` 等必要目录

启动后访问 `http://localhost:5001`

---

## 五、📱 功能详解

### 5.1 前台功能（患者端）

#### 🏥 健康画像（`/health_profile`）
- **SVG 数字孪生人体**：根据用户健康信息实时标注异常部位（心血管→红色脉动、呼吸系统→黄色警示等），右侧图例面板显示各系统状态
- **个人信息**：姓名、年龄、性别、民族、职业、婚姻等8项
- **身体指标**：身高、体重、BMI自动计算、血压、吸烟/饮酒/运动等9项
- **健康状态**：主诊断、过敏史、疾病史、家族史、手术史、用药等6项
- **就诊记录**：时间轴展示，实时从数据库加载
- **健康指标**：支持日期筛选、分页浏览
- **30秒自动刷新**：实时同步最新健康数据

#### 💡 知识推送（`/diagnosis`）
- **无需输入即可推送**：直接点击按钮，系统自动基于完整健康画像（包括就诊记录、检查指标）执行 GraphRAG 五步流程
- **也支持提问**：输入具体问题（如"高血压饮食注意什么"），系统结合画像 + 问题双目标检索
- **来源标注**：每条知识标注来源（上传文档名/URL/知识图谱/权威网站）
- **Markdown渲染**：代码高亮、表格、列表、链接等完整支持

#### 🔬 影像分析（`/image_analysis`）
- **支持拖拽/点击上传**：JPG、PNG、BMP、WebP 等
- **图片类型选择**：X光、CT、MRI、超声、皮肤病变、外伤、眼科、病理切片
- **多模态AI分析**：调用 `qwen-vl-plus` 视觉模型，输出影像分析、初步诊断、治疗方案、严重程度
- **同步到健康档案**：点击"更新到健康档案"按钮，分析结果自动写入就诊记录
- **图片不留存**：仅在请求时使用 base64，不保存到服务器

#### ⚙️ 个人设置（`/profile/settings`）
- 可修改：姓名、密码
- 不可修改：手机号（登录凭证）

### 5.2 后台功能（管理端）

> 后台入口：`/admin`（独立 URL，不在前台导航中暴露）
> 默认账号：`admin` / `admin123`

#### 👥 用户健康档案管理（`/admin/dashboard`）
- **搜索筛选**：按姓名、手机号、健康状况服务端搜索
- **新增用户**：手机号若已存在则自动合并健康信息（前后台通过手机号联通）
- **编辑/预览**：四页签（基本信息、健康指标、医疗历史、生活习惯）
- **健康指标CRUD**：新增/编辑/删除检查指标
- **AI影像分析记录**：在用户详情中查看该患者所有影像分析历史

#### 📚 知识库管理（`/admin/knowledge`）
- **文档上传**：支持 PDF、DOC、DOCX、TXT、MD、XLSX、XLS、PPTX 等
- **在线URL**：仅记录链接，向量化时才实时爬取文本（不永久存储爬取内容）
- **统计面板**：文档总数、已向量化数、文档占用空间、向量库大小、知识领域标签
- **WebSocket向量化**：实时日志输出，进度可视

#### 🧠 知识图谱管理（`/knowledge_graph`）
- **Vis.js 可视化**：支持拖拽、缩放、全屏
- **数量控制滑块**：50-2000节点可调，避免大图卡顿
- **文本分析入图**：输入文本 → LLM抽取三元组 → 写入Neo4j → 立即可视化
- **节点/边详情**：暗色主题高对比卡片，属性多时自动分页
- **高级查询**：最短路径、中心性分析、关键词搜索

#### ✏️ 实体关系属性配置（`/admin/entity_config`）
- **实时统计**：实体总数、关系总数（直接从Neo4j查询）
- **三元组分页**：每页5条，请求取消机制（AbortController）
- **属性编辑**：支持新增/修改/删除实体和关系的属性，实时同步到Neo4j

#### 📝 Prompt 模板管理（`/admin/prompt_templates`）
- **CRUD管理**：新建、编辑、删除模板
- **激活机制**：一键激活某模板，前台知识推送立即使用新模板
- **模板变量**：`{user_input}`、`{kg_results}`、`{vdb_results}`、`{current_date}`、`{user_name}`

#### ⚙️ 系统设置（`/admin/system_settings`）
- **向量数据库配置**：类型、存储路径
- **图数据库配置**：Neo4j URI/用户名/密码
- **LLM配置**：提供商、模型名、API地址/密钥、温度/Token数
- **多模态视觉模型配置**：模型名、API地址/密钥
- **嵌入模型配置**：API地址、模型名、密钥
- **文本处理参数**：分块大小、重叠、检索Top-K
- **热重载**：保存后自动重新初始化 KG/VDB/RAG 组件，无需重启服务

---

## 六、📡 API 接口一览

### 前台 API（共12个）

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/generate_health_knowledge` | GraphRAG知识推送 |
| GET | `/api/health_data` | 实时获取健康画像数据 |
| GET | `/api/health_metrics` | 分页获取检查指标（支持日期筛选）|
| GET | `/api/profile/basic` | 获取个人基本信息 |
| PUT | `/api/profile/basic` | 修改姓名/密码 |
| POST | `/api/analyze_image` | 上传图片AI分析 |
| POST | `/api/save_image_analysis` | 保存分析结果到档案 |
| GET | `/api/image_analyses` | 获取影像分析历史 |

### 后台 API（共40+个）

涵盖用户CRUD、健康指标CRUD、文档管理、向量化WebSocket、知识图谱查询/更新、三元组分页/编辑、Prompt模板CRUD/激活、系统配置读写等。

---

## 七、🔧 配置说明

### config.json 核心配置

```json
{
    "NEO4J_URI": "bolt://IP:7687",         // ⚠️ Neo4j地址
    "NEO4J_USER": "neo4j",
    "NEO4J_PASSWORD": "密码",               // ⚠️ Neo4j密码
    "TONGYI_KEY": "sk-xxx",                 // ⚠️ 百炼API密钥
    "EMBEDDING_MODEL": "text-embedding-v1", // 嵌入模型
    "CHUNK_SIZE": 1000,                     // 文本分块大小
    "CHUNK_OVERLAP": 100,                   // 分块重叠
    "VECTOR_TOP_K": 5,                      // 向量检索数量
    "GRAPH_TOP_K": 10                       // 图谱检索数量
}
```

### 环境变量（可选，优先级高于config.json）

| 变量 | 作用 |
|------|------|
| `DASHSCOPE_API_KEY` | 百炼平台API密钥 |

### 自动创建的目录

| 目录 | 说明 |
|------|------|
| `documents/` | 上传文档存储 |
| `data/` | SQLite数据库 |
| `vector_db/` | ChromaDB向量库 |
| `knowledge_index/` | KG向量索引 |

### 需手动准备

| 文件/目录 | 说明 |
|-----------|------|
| `schema/kg_schema.json` | 知识图谱实体关系Schema定义 |
| `nltk_data/` | NLTK分词数据包 |

---

## 八、🐳 生产部署

### 直接部署

```bash
# 生产启动（gunicorn + eventlet 支持 WebSocket）
gunicorn --worker-class eventlet -w 1 -b 0.0.0.0:5001 app:app
```

### Docker 部署

```yaml
# docker-compose.yml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "5001:5001"
    volumes:
      - ./config.json:/app/config.json
      - ./documents:/app/documents
      - ./data:/app/data
      - ./vector_db:/app/vector_db
      - ./schema:/app/schema
    environment:
      - DASHSCOPE_API_KEY=sk-你的密钥
    restart: unless-stopped

  neo4j:
    image: neo4j:5
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      - NEO4J_AUTH=neo4j/你的密码
    volumes:
      - neo4j_data:/data
    restart: unless-stopped

volumes:
  neo4j_data:
```

### Nginx 反向代理

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location /socket.io {
        proxy_pass http://127.0.0.1:5001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        client_max_body_size 100M;
    }
}
```

---

## 九、🔑 默认账号

| 角色 | 账号 | 密码 | 入口 |
|------|------|------|------|
| 管理员 | `admin` | `admin123` | `/admin` |
| 测试患者 | `13800138000` | `password123` | `/login` |
| 测试患者 | `13900139000` | `abc123` | `/login` |
| 测试患者 | `13700137000` | `pass1234` | `/login` |
| 后台新建用户 | 自定义手机号 | `123456`（默认） | `/login` |

---

## 十、🎨 界面风格

整个系统采用 **赛博朋克暗色主题**，以 `#0a0a1a` 深色背景配合 `#00f5ff`（青色）和 `#ff00ff`（品红）霓虹渐变为主视觉。

| 页面 | 风格特点 |
|------|----------|
| 前台登录/注册 | Particles.js粒子背景 + 玻璃态表单 + 霓虹按钮 |
| 健康画像 | SVG人体模型 + 霓虹边框卡片 + 时间轴 |
| 知识推送 | 网格背景 + 玻璃面板 + Markdown美化渲染 |
| 影像分析 | 拖拽上传区 + 结果卡片 + 档案同步按钮 |
| 后台管理 | 侧边栏导航 + 深色表格 + 暗色模态框 |
| 知识图谱 | Vis.js全屏可视化 + 暗色详情面板 |

---

## 十一、📈 开发计划

- [x] GraphRAG 五步流程引擎
- [x] SVG 数字孪生人体健康标注
- [x] 多模态AI医学影像分析
- [x] 前后台用户通过手机号联通
- [x] Prompt模板动态管理
- [x] 系统配置热重载
- [ ] 📱 移动端适配 / 小程序
- [ ] 🎤 语音交互知识推送
- [ ] 📊 健康趋势分析报告
- [ ] 🔗 医院HIS系统对接
- [ ] 🌍 多语言支持
- [ ] 🔒 RBAC 细粒度权限控制

---

## 十二、🤝 贡献指南

1. Fork 本仓库
2. 创建分支：`git checkout -b feature/your-feature`
3. 提交代码：`git commit -am 'Add your feature'`
4. 推送分支：`git push origin feature/your-feature`
5. 提交 Pull Request

问题反馈请在 [GitHub Issues](https://github.com/OpenGraphRAG/MedicalGraphRAG/issues) 中提交，附上详细复现步骤和环境信息。

---

## 十三、📄 许可证

本项目采用 [Apache License 2.0](LICENSE) 许可证。

---

> ⚠️ **免责声明**：本系统生成的健康知识和影像分析结果仅供参考，不能替代专业医生的面对面诊断。如有健康问题请及时就医。

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=OpenGraphRAG/MedicalGraphRAG&type=Date)](https://www.star-history.com/#OpenGraphRAG/MedicalGraphRAG&Date)
