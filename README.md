# 🧬 ReAct PubMed Agent (支持中文 / Chinese Language Support)

An intelligent research assistant that can retrieve, understand, store, and reason about scientific literature from PubMed using the ReAct (Reasoning and Acting) framework.

## 🎯 Project Goals (项目目标)

This agent is designed to:
1. **检索 (Retrieve)** literature from PubMed and other scientific databases
2. **嵌入与存储 (Embed and Store)** long text abstracts to reduce hallucinations
3. **语义检索与推理 (Semantic Search & Reasoning)** based on user questions
4. **清晰的推理轨迹 (Clear Reasoning Traces)** maintain "思考—行动—观察" (Thought → Action → Observation) ReAct framework
5. **扩展支持 (Extensibility)**: multi-tool integration, MCP standardization, knowledge base updates
6. **角色化提示词 (Role-based Prompts)**: Support for specialized agent roles like "Synapse Scholar"
7. **自动文档保存 (Auto-save)**: Automatic Markdown export of query results

## 🏗️ System Architecture (系统架构)

```
用户问题 → ReAct控制器 → 工具层 → 向量数据库 → LLM总结 → 最终答案
User Query → ReAct Controller → Tools Layer → Vector Database → LLM Summarization → Final Answer
```

### Core Components (核心组件)

- **ReAct Controller**: Orchestrates reasoning cycles (推理循环编排)
- **Tools Layer**: PubMed Search, Vector DB Store, Vector Search (工具层)
- **Internal MCP Backend**: Python-based PubMed MCP server for enhanced functionality (内部MCP后端)
- **Vector Database**: Chroma/FAISS for semantic retrieval (向量数据库)
- **LLM Layer**: Multi-provider support (OpenAI, Azure, local models) (多供应商语言模型层)
- **Role System**: Customizable agent roles via markdown prompts (角色系统)

## 🚀 Quick Start (快速开始)

### English Usage (英文使用)
```python
from pubmed_agent import PubMedAgent

# Initialize agent (初始化代理)
agent = PubMedAgent()

# Query scientific literature (查询科学文献)
response = agent.query("What are the mechanisms of action for COVID-19 vaccines?")
print(response)
```

### Chinese Usage (中文使用)
```python
from pubmed_agent import PubMedAgent

# 初始化代理
agent = PubMedAgent(language="zh")  # 设置为中文模式

# 查询科学文献
response = agent.query("mRNA疫苗的作用机制是什么？")
print(response)
```

### Multi-language Support (多语言支持)
```python
from pubmed_agent import PubMedAgent

# Auto-detect language (自动检测语言)
agent = PubMedAgent(language="auto")  

# English query (英文问题)
response1 = agent.query("What are the mechanisms of mRNA vaccines?")

# Chinese query (中文问题)  
response2 = agent.query("mRNA疫苗的作用机制是什么？")
```

## 📦 Installation (安装)

### Windows 本地部署 (Windows Local Deployment)

```powershell
# 1. 克隆仓库 (Clone repository)
git clone <repository-url>
cd PubMed-Agent

# 2. 创建虚拟环境 (Create virtual environment)
python -m venv venv

# 3. 激活虚拟环境 (Activate virtual environment)
venv\Scripts\activate

# 4. 安装依赖 (Install dependencies)
## 完整安装（推荐） 
pip install -e .

## 或者
pip install -r requirements.txt

# 5. 配置环境变量 (Configure environment variables)
# 复制 .env.example 为 .env
copy .env.example .env

# 6. 编辑 .env 文件，填入您的配置
# Edit .env file and fill in your configuration:
#   - LLM_API_KEY: 您的 LLM API 密钥（支持多种供应商）
#   - LLM_MODEL: 选择模型 (gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo 等)
#   - LLM_BASE_URL: 自定义 API 端点（可选，留空则使用默认 OpenAI URL）
#   - PUBMED_EMAIL: 您的邮箱 (推荐)
#   - AGENT_ROLE_NAME: 角色名称（可选，默认自动加载 "Synapse Scholar"）
#   - 其他配置项可根据需要调整
```

### Linux/macOS 部署 (Linux/macOS Deployment)

```bash
# Clone repository (克隆仓库)
git clone <repository-url>
cd PubMed-Agent

# Create virtual environment (创建虚拟环境)
python -m venv venv
source venv/bin/activate

# Install dependencies (安装依赖)
pip install -e .
```

### 环境变量配置 (Environment Variables Setup)

```bash
# 复制环境变量模板文件
# Copy environment variables template
cp .env.example .env

# 编辑 .env 文件，填入你的API密钥
# Edit .env file and fill in your API keys
```

### 环境配置文件说明 (Environment Configuration)

`.env.example` 文件包含所有可配置项，支持多种大模型供应商：

- **多模型供应商支持 (Multi-Provider Support)**:
  - **OpenAI**: 设置 `LLM_API_KEY`，`LLM_MODEL`（如 gpt-4o, gpt-4o-mini），`LLM_BASE_URL` 留空
  - **Azure OpenAI**: 设置 `LLM_API_KEY`，`LLM_BASE_URL` 为 Azure 端点，`LLM_MODEL` 为部署名称
  - **本地模型/代理**: 设置 `LLM_BASE_URL` 为本地服务地址（如 http://localhost:8000/v1），`LLM_MODEL` 为模型名称
  - **其他兼容服务**: 设置 `LLM_BASE_URL` 和 `LLM_API_KEY`，使用兼容 OpenAI API 格式的服务

- **模型选择示例 (Model Selection Examples)**: 
  - OpenAI: `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`, `gpt-3.5-turbo`
  - Azure OpenAI: `gpt-4`, `gpt-35-turbo`（部署名称）
  - 本地模型: `llama-2-7b-chat`, `mistral-7b-instruct` 等

- **推理参数 (Reasoning Parameters)**:
  - `TEMPERATURE`: 默认 0.7，适合大多数模型
  - `TOP_P`: 默认 0.95，适合大多数模型

- **向量数据库 (Vector Database)**: 支持 Chroma 和 FAISS

- **PubMed MCP Backend**:
  - `PUBMED_BACKEND`: 选择 `python_mcp`（默认，使用内部 Python MCP 后端）
  - `PUBMED_MCP_BASE_DIR`: MCP 缓存与导出文件目录（默认 `./cache`）
  - `ABSTRACT_MODE`: `quick`（1500 字符摘要）或 `deep`（6000 字符摘要）
  - `FULLTEXT_MODE`: `disabled`、`enabled`（手动下载）、`auto`（自动下载开放获取 PDF）
  - `ENDNOTE_EXPORT`: `enabled` / `disabled`
  - 代理支持：`PROXY_ENABLED`、`HTTP_PROXY`、`HTTPS_PROXY`、`PROXY_USERNAME`、`PROXY_PASSWORD`

- **角色提示词配置 (Role Prompt Configuration)**:
  - `AGENT_ROLE_NAME`: 角色名称（如 "Synapse Scholar"），会在 `agents/` 目录下查找对应的 `.md` 文件
  - `AGENT_ROLE_FILE`: 角色文件的完整路径（可选，会覆盖 `AGENT_ROLE_NAME`）
  - 如果两者都不设置，系统会自动尝试加载 `agents/Synapse Scholar.md`（如果文件存在）

- **嵌入模型 (Embedding Model)**: 
  - 支持独立供应商配置，默认与 LLM 供应商一致
  - 如果填写 `EMBEDDING_API_KEY` 和 `EMBEDDING_BASE_URL`，则使用独立的 embedding 服务
  - 本地模型支持（如 LM Studio）: `EMBEDDING_BASE_URL=http://localhost:1234/v1`
  - 模型示例: `text-embedding-3-small`, `text-embedding-3-large`, `text-embedding-ada-002`

详细配置说明请参考 `.env.example` 文件中的注释。

### 🚀 Deployment Checklist (部署清单)

1. **Install dependencies**
   ```bash
   pip install -e .
   ```
   该命令会在虚拟环境中安装 `pubmed_agent` 与新的 `pubmed_mcp` 包。

2. **Copy & edit environment file**
   ```bash
   copy .env.example .env   # Windows
   # or
   cp .env.example .env     # Linux / macOS
   ```
   - 设置 `LLM_API_KEY`、`LLM_MODEL` 等模型参数
   - 若使用自定义推理服务（Azure、本地代理等），同时设置 `LLM_BASE_URL`
   - 如使用不同的嵌入供应商，可配置 `EMBEDDING_API_KEY`、`EMBEDDING_BASE_URL`、`EMBEDDING_MODEL`
   - 配置 `PUBMED_EMAIL`、`PUBMED_API_KEY`
   - 如需启用全文或 EndNote 导出，调整 `FULLTEXT_MODE`、`ENDNOTE_EXPORT`
   - 如需使用自定义角色，设置 `AGENT_ROLE_NAME` 或 `AGENT_ROLE_FILE`

3. **Prepare cache directories (optional)**
   - 默认缓存目录为 `./cache`，首次运行会自动创建
   - 若使用自定义目录，确保 `.env` 中的 `PUBMED_MCP_BASE_DIR` 指向有效路径

4. **Prepare role prompts (optional)**
   - 将角色提示词文件放在 `agents/` 目录下（如 `agents/Synapse Scholar.md`）
   - 系统会自动检测并加载（如果文件存在）

5. **Smoke test**
   ```bash
   pubmed-agent query "mRNA疫苗的作用机制是什么？"
   ```
   成功返回 JSON 结果表示 Python MCP 后端已正常工作。查询结果会自动保存为 Markdown 文档到项目根目录。

### ✅ Quality Assurance Workflow (质量保障流程)

1. **环境验证**：确认 `.env` 中的 PubMed/LLM 配置正确；若启用全文下载，验证网络代理设置。
2. **单次查询测试**：运行 `pubmed-agent query "..."`，检查搜索结果中是否包含 `success: true`、`articles` 等字段。
3. **工具链测试**：在 REPL 中执行
   ```python
   from pubmed_agent import PubMedAgent
   agent = PubMedAgent()
   response = agent.query("COVID-19 vaccine adverse events")
   ```
   确认结果包含引用与线程 ID。
4. **Markdown 保存测试**：运行查询后，检查项目根目录是否生成了对应的 Markdown 文件。
5. **角色提示词测试**：确认 `agents/Synapse Scholar.md` 存在时，agent 会自动加载该角色。
6. **缓存与全文 QA**：调用 `pubmed_mcp` 客户端（或 agent 工具）运行 `cache_info`、`fulltext_status`、`endnote_status` 检查缓存书目和全文下载行为。
7. **日志检查**：查看 `logs/`（如启用）或终端输出，确保无异常堆栈；若有网络/代理问题按提示调整。

完成以上步骤后，即可投入日常使用或集成到更大的工作流中。

## 📚 Features (功能特性)

- 🔍 **PubMed Integration**: Search and retrieve literature from PubMed database (PubMed集成)
- 🧠 **ReAct Framework**: Transparent reasoning with Thought → Action → Observation cycles (ReAct框架)
- 💾 **Vector Storage**: Embed and store long texts to reduce hallucinations (向量存储)
- 🔎 **Semantic Search**: RAG-based retrieval and reasoning (语义搜索)
- 📖 **Reference Management**: Proper citation formatting with PMID references (参考文献管理)
- 🔧 **Extensible Tools**: Modular tool system supporting future MCP integration (可扩展工具)
- 🌏 **Multi-language Support**: English and Chinese language support (多语言支持)
- 🔧 **Language Detection**: Automatic language detection and prompt selection (语言检测)
- 🎭 **Role-based Prompts**: Support for specialized agent roles (角色化提示词)
- 📄 **Auto-save Markdown**: Automatic export of query results to Markdown files (自动保存Markdown)
- 🔌 **Internal MCP Backend**: Python-based PubMed MCP server for enhanced functionality (内部MCP后端)
- 🌐 **Multi-provider LLM**: Support for OpenAI, Azure, local models, and more (多供应商LLM支持)
- 📊 **Structured Workflow**: 9-step structured workflow for systematic literature review (结构化工作流)

## 🎖️ Design Principles (设计原则)

| Principle | Description | 说明 |
|------------|-------------|------|
| 🧠 **Transparent Reasoning** | Maintain Thought/Action/Observation records (透明推理) | 保持完整的推理轨迹 |
| 🔒 **Controlled Hallucinations** | All answers must come from vector database content (可控幻觉) | 所有答案基于向量数据库内容 |
| 🧩 **Modular Decoupling** | Separate tool, reasoning, and database layers (模块解耦) | 工具、推理、数据库层分离 |
| 🔄 **Sustainable Updates** | Support automatic embedding and cleanup of new literature (可持续更新) | 支持自动嵌入和清理 |
| 🔧 **Adjustable Logic** | Allow custom prompts or programmatic logic (可调逻辑) | 支持自定义提示词和程序化逻辑 |
| 🌐 **Open Standards** | Compatible with MCP, LangChain, LlamaIndex ecosystems (开放标准) | 兼容 MCP、LangChain 等生态系统 |
| 🌏 **Multi-language Support** | English and Chinese language support (多语言支持) | 中英文双语支持 |
| 🎭 **Role Customization** | Support for specialized agent roles via markdown prompts (角色定制) | 通过 Markdown 提示词支持专业角色 |

## 📊 Success Metrics (成功指标)

- **Retrieval Accuracy**: RAG recall consistency ≥ 85% (检索准确率)
- **Hallucination Rate**: False statements ≤ 10% (幻觉率)
- **Latency**: Response time ≤ 8 seconds (延迟)
- **Explainability**: Every output includes reasoning traces (可解释性)
- **Extensibility**: New tools can be integrated in 10 lines of code (扩展性)
- **Language Support**: Automatic detection and optimal prompt selection (语言支持)
- **Documentation**: All queries automatically saved as Markdown (文档化)

## 🔮 Future Directions (未来方向)

1. 🔬 Multi-source retrieval (PubMed + arXiv + Semantic Scholar) (多源检索)
2. 🧩 Multi-model fusion (GPT-4o + BioMedLM + Claude) (多模型融合)
3. 🧠 Self-Reflection / Self-Verification capabilities (自我反思)
4. 🌐 Web UI support (Streamlit / Gradio) (Web界面)
5. 📚 Sustainable, updatable scientific knowledge base (可持续知识库)
6. 🌏 More language support (Japanese, Korean, etc.) (更多语言支持)
7. 🎭 More specialized agent roles (更多专业角色)

---

## 🌟 Language Support (语言支持)

### English (英文)
- Full ReAct reasoning in English
- Scientific terminology and citation formatting
- PubMed search with English queries

### Chinese (中文)
- Complete ReAct reasoning in Chinese
- Chinese scientific terminology
- Optimized prompts for Chinese queries
- Support for Chinese medical and scientific terms

### Auto-detection (自动检测)
- Automatic language detection based on query content
- Optimal prompt template selection
- Seamless switching between language modes

---

## 🖥️ 命令行使用 (Command Line Usage)

项目提供了完整的命令行接口，可以直接从终端使用：

The project provides a complete command-line interface:

```bash
# 基本查询 / Basic query
pubmed-agent query "mRNA疫苗的作用机制是什么？"

# 交互式模式 / Interactive mode
pubmed-agent interactive

# 搜索文献 / Search articles
pubmed-agent search "COVID-19 vaccine" --max-results 5

# 查看统计信息 / View statistics
pubmed-agent stats
```

**所有查询结果会自动保存为 Markdown 文档到项目根目录！**

**All query results are automatically saved as Markdown files to the project root directory!**

---

## 📋 Usage Examples (使用示例)

### 命令行工具 (Command-line Tool) ⭐ 推荐

最简单快捷的使用方式，支持单次查询和多轮对话：

```powershell
# Windows PowerShell 示例

# 单次查询 (Single Query)
python query.py -question:"What are the mechanisms of mRNA vaccines?"
python query.py -question:"mRNA疫苗的作用机制是什么？"

# 指定语言 (Specify Language)
python query.py -question:"疫苗机制" -language:zh
python query.py -question:"vaccine mechanism" -language:en

# 多轮对话模式 (Multi-turn Conversation)
python query.py -conversation

# 详细模式 (显示推理过程) (Verbose Mode)
python query.py -question:"疫苗安全性" -verbose

# 组合使用 (Combined Usage)
python query.py -conversation -language:auto -verbose
```

**命令行参数说明 (Command-line Arguments)**:
- `-question:"问题"`: 要查询的问题
- `-language:en|zh|auto`: 语言设置 (默认: auto)
- `-conversation`: 进入多轮对话模式
- `-verbose`: 显示详细推理过程

**多轮对话模式特殊命令 (Conversation Mode Commands)**:
- `exit` 或 `quit`: 退出对话
- `clear`: 清除对话历史
- `stats`: 查看代理统计信息

**自动保存功能 (Auto-save Feature)**:
- 每次查询后，结果会自动保存为 Markdown 文件
- 文件名格式: `pubmed_query_YYYYMMDD_HHMMSS_问题摘要.md`
- 保存位置: 项目根目录

### Python API 使用 (Python API Usage)

#### Basic Usage (基本使用)
```python
from pubmed_agent import PubMedAgent

# English mode (英文模式)
agent = PubMedAgent(language="en")
response = agent.query("What are the mechanisms of action of mRNA vaccines?")

# Chinese mode (中文模式)
agent = PubMedAgent(language="zh")  
response = agent.query("mRNA疫苗的作用机制是什么？")

# Auto-detection (自动检测)
agent = PubMedAgent(language="auto")  # Automatically detects language
response = agent.query("How do vaccines work?")  # English
response = agent.query("疫苗是如何工作的？")  # Chinese
```

#### Advanced Features (高级功能)
```python
# Search and store (搜索和存储)
result = agent.search_and_store("COVID-19 vaccine safety", max_results=5)

# Get agent statistics (获取代理统计)
stats = agent.get_agent_stats()

# Add custom tools (添加自定义工具)
from langchain.tools import BaseTool
agent.add_custom_tool(MyCustomTool())

# Multi-language query (多语言查询)
results = agent.query_multi_language("疫苗机制", ["en", "zh"])

# Clear conversation memory (清除对话记忆)
agent.clear_memory()
```

---

## 🎭 Role-based Prompts (角色化提示词)

项目支持通过 Markdown 文件定义专业角色，如 "Synapse Scholar"（生物医学研究科学家）。

### 使用角色提示词 (Using Role Prompts)

1. **创建角色文件**: 在 `agents/` 目录下创建 Markdown 文件（如 `agents/Synapse Scholar.md`）
2. **配置环境变量** (可选):
   ```env
   AGENT_ROLE_NAME=Synapse Scholar
   # 或
   AGENT_ROLE_FILE=agents/Synapse Scholar.md
   ```
3. **自动加载**: 如果 `agents/Synapse Scholar.md` 存在，系统会自动加载（无需配置）

### 角色文件格式 (Role File Format)

角色文件应包含完整的系统提示词，定义：
- 角色身份和职责
- 工具使用规范
- 工作流程
- 输出格式要求
- 约束条件

示例角色文件请参考 `agents/Synapse Scholar.md`。

---

## 🖥️ Windows 快速开始指南 (Windows Quick Start Guide)

### 一键部署步骤 (One-click Deployment)

1. **环境准备 (Environment Setup)**
   ```powershell
   # 确保已安装 Python 3.8+
   python --version
   
   # 创建并激活虚拟环境
   python -m venv venv
   venv\Scripts\activate
   ```

2. **安装依赖 (Install Dependencies)**
   ```powershell
   pip install -e .
   ```

3. **配置环境变量 (Configure Environment)**
   ```powershell
   # 复制配置文件
   copy .env.example .env
   
   # 使用文本编辑器打开 .env 文件，填入以下必需配置：
   # - LLM_API_KEY: 您的 API 密钥（支持 OpenAI、Azure、本地模型等）
   # - LLM_MODEL: 模型名称（如 gpt-4o, gpt-4o-mini 等，用户可自由填写）
   # - LLM_BASE_URL: 自定义 API 端点（可选，留空则使用默认 OpenAI URL）
   # - PUBMED_EMAIL: 您的邮箱 (推荐)
   ```

4. **测试运行 (Test Run)**
   ```powershell
   # 测试单次查询
   python query.py -question:"What is CRISPR?"
   
   # 或进入对话模式
   python query.py -conversation
   ```

### 常见问题 (FAQ)

**Q: 如何选择模型？**
- **OpenAI**: 复杂推理用 `gpt-4o`，一般查询用 `gpt-4o-mini`，简单查询用 `gpt-3.5-turbo`
- **Azure OpenAI**: 设置 `LLM_BASE_URL` 为 Azure 端点，`LLM_MODEL` 为部署名称
- **本地模型**: 设置 `LLM_BASE_URL` 为本地服务地址，`LLM_MODEL` 为模型名称
- **其他供应商**: 设置 `LLM_BASE_URL` 和 `LLM_API_KEY`，使用兼容 OpenAI API 格式的服务

**Q: 如何配置推理参数？**
- `TEMPERATURE`: 默认 0.7，适合大多数模型（0.0-1.0）
- `TOP_P`: 默认 0.95，适合大多数模型（0.0-1.0）

**Q: 支持哪些语言？**
- 英文 (en): 完整支持
- 中文 (zh): 完整支持
- 自动检测 (auto): 根据问题自动选择

**Q: 如何查看详细推理过程？**
- 使用 `-verbose` 参数: `python query.py -question:"问题" -verbose`

**Q: 多轮对话如何清除历史？**
- 在对话模式下输入 `clear` 命令

**Q: 查询结果保存在哪里？**
- 所有查询结果自动保存为 Markdown 文件到项目根目录
- 文件名包含时间戳和问题摘要，便于查找

**Q: 如何使用角色提示词？**
- 将角色文件放在 `agents/` 目录下（如 `agents/Synapse Scholar.md`）
- 系统会自动检测并加载（如果文件存在）
- 或通过环境变量 `AGENT_ROLE_NAME` 或 `AGENT_ROLE_FILE` 指定

---

**🎉 Ready for Production! (准备投产！)**

The complete ReAct PubMed Agent with comprehensive Chinese language support, role-based prompts, and auto-save functionality is now ready for scientific research and analysis in both English and Chinese!

**🚀 快速体验 (Quick Experience)**:
```powershell
python query.py -question:"mRNA疫苗的作用机制是什么？"
```

---

## 📝 Changelog (更新日志)

### v0.2.0 (Latest)
- ✨ 新增内部 Python MCP 后端集成
- ✨ 新增角色提示词系统（支持 Synapse Scholar 等专业角色）
- ✨ 新增自动 Markdown 保存功能
- ✨ 增强多模型供应商支持
- ✨ 完善环境变量配置系统
- 🐛 修复 CLI 环境变量传递问题
- 📚 更新文档和示例

### v0.1.0
- 🎉 初始版本发布
- ✅ 完整的 ReAct 框架实现
- ✅ 中英文双语支持
- ✅ 向量数据库集成
- ✅ 命令行工具支持

---

**You're not just training models—you're orchestrating intelligence!** (您不是在训练模型——您在编排智能！) 🚀
