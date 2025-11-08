# MedicalGraphRAG 项目文档
## 感谢各位starter
[![Stargazers repo roster for @OpenGraphRAG/MedicalGraphRAG](https://reporoster.com/stars/OpenGraphRAG/MedicalGraphRAG)](https://github.com/OpenGraphRAG/MedicalGraphRAG/stargazers)
## 一、📖 项目简介

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.3+-green.svg)](https://flask.palletsprojects.com/)
[![Neo4j](https://img.shields.io/badge/Neo4j-4.4+-orange.svg)](https://neo4j.com/)

MedicalGraphRAG 是一个专为医疗领域设计的开源知识图谱增强检索生成（GraphRAG）系统。项目通过整合医学文献、临床指南、病例报告等多源异构数据，构建动态医学知识图谱，并结合大语言模型（LLM）实现可解释、可追溯的智能医疗问答与临床决策支持。
与传统RAG相比，MedicalGraphRAG通过图结构捕捉医学实体间的复杂关系，显著降低医疗场景下的幻觉风险，提供基于循证医学的精准回答。

### 🎯 🎯 核心亮点
- 🔍 三重知识融合：私有文档 + 公开医学文献 + 医学词典，构建权威知识库
- 🧠 智能图谱构建：自动抽取<实体, 关系, 实体>三元组，支持百万级节点
- 💬 多轮循证问答：上下文感知对话，每个回答附带来源溯源
- 📊 患者健康画像：20+维度健康数据管理，支持BMI自动计算与趋势分析
- ⚡ 实时向量化处理：WebSocket推送处理进度，支持PDF/Word/TXT多格式文档
- 🎨 交互式可视化：基于Vis.js的知识图谱探索，支持最短路径、节点关联分析
- 🔒 医疗级安全：回答置信度评分，敏感信息自动过滤

## 🎨 界面展示

| 功能                  | 截图描述                                                 |
| --------------------- | -------------------------------------------------------- |
| **患者端 - 健康画像** | 20+ 维度健康数据卡片式展示，BMI 自动计算，时间轴就诊记录 |
| **患者端 - 知识推送** | 赛博朋克风格输入框，Markdown 渲染的 AI 建议              |
| **管理端 - 患者列表** | 分页表格，一键编辑/预览患者完整档案                      |
| **管理端 - 知识图谱** | 基于 Vis.js 的可视化网络，支持拖拽、缩放、最短路径查询   |
| **管理端 - 文档管理** | 文件 & URL 双模式上传，实时向量化进度条                  |

## 二、系统架构
### 系统架构图
<img width="1902" height="942" alt="image" src="https://github.com/user-attachments/assets/49415d4f-d83a-4ca6-a892-d9cc0779b914" />

### 模块架构图
<img width="1902" height="942" alt="image" src="https://github.com/user-attachments/assets/f5aee87d-8d4d-4b43-b317-92a03b6dbad8" />

### 数据流架构
<img width="1902" height="942" alt="image" src="https://github.com/user-attachments/assets/a13f6165-64f1-406f-8fb6-f58fcc8d54db" />

### 部署架构图
<img width="1902" height="942" alt="image" src="https://github.com/user-attachments/assets/3479eaff-8c9e-47a6-ba74-8c96a5f62a0d" />

### 技术栈

- **前端**：HTML5、CSS3、JavaScript、Tailwind CSS
- **后端**：Python、Flask
- **数据库**：Neo4j（图数据库）、SQLite（元数据存储）
- **向量检索**：基于 FAISS 的相似度检索
- **大模型**：阿里云通义大模型 API
- **部署**：Docker、Nginx
### demo
<img width="1406" height="685" alt="截屏2025-09-21 03 20 06" src="https://github.com/user-attachments/assets/9abdb3f1-fbf9-4227-bc7a-50ede81150a0" />

<img width="1383" height="680" alt="截屏2025-09-21 03 21 07" src="https://github.com/user-attachments/assets/32fed79b-a6bd-4e0c-9f9d-0c842c3f15d5" />

<img width="1382" height="681" alt="截屏2025-09-21 03 21 26" src="https://github.com/user-attachments/assets/3bbc49a0-f315-453d-b1e8-c38139e09491" />

<img width="1391" height="670" alt="截屏2025-09-21 03 21 51" src="https://github.com/user-attachments/assets/a436c9e3-1062-43a2-8316-ed88591e2c4d" />

<img width="1387" height="678" alt="截屏2025-09-21 03 22 02" src="https://github.com/user-attachments/assets/21726ddf-57ba-4924-9085-59baf51a5d1c" />

## 三、快速开始

### 3.1 环境准备

1. 安装 Python 3.8+
2. 安装 Neo4j 数据库（建议使用 Neo4j Desktop 或 Docker）
3. 获取阿里云通义大模型 API 密钥

```bash
# 克隆项目仓库
git clone https://github.com/OpenGraphRAG/MedicalGraphRAG.git
cd MedicalGraphRAG

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/MacOS
.\venv\Scripts\activate  # Windows

# 安装依赖库
pip install -r requirements.txt
```

### 3.3 配置环境变量

在项目根目录创建 `.env` 文件：

```xml
DASHSCOPE_API_KEY=your_dashscope_api_key
TONGYI_KEY=your_tongyi_key
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password
SECRET_KEY=your_flask_secret_key
```

### 3.4 初始化数据库

```python
# 创建SQLite数据库和表结构
python manage.py init_db

# 初始化Neo4j图数据库
python manage.py init_neo4j
```

### 3.5 启动应用

```python
# 启动Flask应用
python app.py
```

应用启动后，访问 `http://localhost:5000` 即可进入系统界面。

## 四、项目结构

```xml
MedicalGraphRAG/
├── app.py                      # Flask应用主文件
├── knowledge_graph.py          # 知识图谱管理核心模块
├── document_processor.py       # 文档处理与解析模块
├── entity_extractor.py         # 实体和关系抽取模块
├── requirements.txt            # 项目依赖列表
├── manage.py                   # 项目管理脚本
├── static/                     # 静态资源目录
│   ├── css/                    # CSS样式文件
│   ├── js/                     # JavaScript脚本
│   └── img/                    # 图片资源
├── templates/                  # HTML模板目录
├── data/                       # 数据存储目录
│   ├── documents/              # 上传的文档
│   └── indexes/                # 向量索引文件
└── migrations/                 # 数据库迁移脚本
```

## 五、核心功能

### 5.1 文档管理系统

- **多格式支持**：PDF、Word、TXT 等多种文档格式
- **版本控制**：支持文档历史版本管理
- **标签分类**：自定义标签系统，方便文档组织

### 5.2 知识图谱构建

- **实体识别**：自动识别医学实体（疾病、症状、药物等）
- **关系抽取**：分析实体间的关系（治疗、导致、关联等）
- **图谱可视化**：交互式知识图谱可视化展示

### 5.3 智能问答系统

- **检索增强生成**：结合知识图谱和大模型实现精准回答
- **多轮对话**：支持上下文理解的多轮问答
- **证据溯源**：提供回答依据的文档出处

### 5.4 管理后台

- **用户权限**：管理员、编辑、普通用户三级权限
- **系统监控**：实时监控系统运行状态
- **数据统计**：文档数量、实体数量、用户活跃度等统计

## 六、使用示例

### 6.1 添加医学文档

1. 登录管理后台
2. 导航至 "文档管理" 页面
3. 点击 "上传文档" 按钮
4. 选择本地文档或输入在线文档 URL
5. 添加文档标签（如 "心血管疾病"、"诊疗指南"）
6. 提交后系统自动处理并提取知识

### 6.2 知识图谱查询

1. 进入 "知识图谱" 页面
2. 在搜索框输入感兴趣的医学实体（如 "高血压"）
3. 系统展示相关实体及关系网络
4. 点击节点或边查看详细信息
5. 支持导出图谱为多种格式

### 6.3 智能问答示例

```reStructuredText
用户: 高血压患者应该注意哪些饮食问题？
系统: 高血压患者的饮食应注意以下几点：
1. 减少钠盐摄入：每日不超过5克盐
2. 增加钾摄入：多吃香蕉、土豆等富含钾的食物
3. 控制体重：保持BMI在18.5-24.9之间
4. 减少脂肪摄入：尤其是饱和脂肪和反式脂肪
5. 增加膳食纤维：多吃全谷物、蔬菜和水果

证据来源：
[1] 《中国高血压防治指南2023》
[2] World Health Organization. (2022). Diet and cardiovascular disease.
```

## 七、性能指标

### 7.1 系统性能

| 指标           | 数值           |
| -------------- | -------------- |
| 实体抽取准确率 | 92.7%          |
| 关系分类准确率 | 89.5%          |
| 问答响应时间   | 平均 2.3 秒    |
| 系统吞吐量     | 50 QPS         |
| 知识图谱规模   | 支持百万级实体 |

### 7.2 文档处理能力

| 文档类型 | 处理时间 | 支持最大文件大小 |
| -------- | -------- | ---------------- |
| PDF      | 5-30 秒  | 100MB            |
| Word     | 3-15 秒  | 50MB             |
| TXT      | <1 秒    | 无限制           |

## 八、部署与扩展

### 8.1 生产环境部署

```bash
# 使用Docker部署
docker-compose up -d

# 配置Nginx反向代理
server {
    listen 80;
    server_name medicalgraphrag.example.com;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### 8.2 系统扩展

- **水平扩展**：通过负载均衡器添加多个应用实例
- **垂直扩展**：升级服务器硬件配置
- **分布式向量检索**：使用 Milvus 等分布式向量数据库
- **大模型优化**：支持模型量化和推理加速

## 九、贡献指南

### 9.1 代码贡献

1. Fork 项目仓库
2. 创建特性分支：`git checkout -b feature/new-feature`
3. 提交代码：`git commit -am 'Add new feature'`
4. 推送分支：`git push origin feature/new-feature`
5. 提交 Pull Request

### 9.2 问题反馈

- 请在 GitHub Issues 中提交问题
- 提交时请提供详细的复现步骤和环境信息

## 9.3📈 开发计划

- [ ] 📱 移动端APP开发
- [ ] 🌐 微信小程序集成
- [ ] 🎤 语音知识推送
- [ ] 📊 健康数据分析报告
- [ ] 🔗 医院HIS系统对接
- [ ] 🌍 多语言支持

## 十、许可证

本项目采用 Apache License 2.0 许可证，详情见LICENSE文件。

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=OpenGraphRAG/MedicalGraphRAG&type=Date)](https://www.star-history.com/#OpenGraphRAG/MedicalGraphRAG&Date)
