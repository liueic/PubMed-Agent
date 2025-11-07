# 🧬 ReAct PubMed Agent (支持中文 / Chinese Language Support)

An intelligent research assistant that can retrieve, understand, store, and reason about scientific literature from PubMed using the ReAct (Reasoning and Acting) framework.

## 🎯 Project Goals (项目目标)

This agent is designed to:
1. **检索 (Retrieve)** literature from PubMed and other scientific databases
2. **嵌入与存储 (Embed and Store)** long text abstracts to reduce hallucinations
3. **语义检索与推理 (Semantic Search & Reasoning)** based on user questions
4. **清晰的推理轨迹 (Clear Reasoning Traces)** maintain "思考—行动—观察" (Thought → Action → Observation) ReAct framework
5. **扩展支持 (Extensibility)**: multi-tool integration, MCP standardization, knowledge base updates

## 🏗️ System Architecture (系统架构)

```
用户问题 → ReAct控制器 → 工具层 → 向量数据库 → LLM总结 → 最终答案
User Query → ReAct Controller → Tools Layer → Vector Database → LLM Summarization → Final Answer
```

### Core Components (核心组件)

- **ReAct Controller**: Orchestrates reasoning cycles (推理循环编排)
- **Tools Layer**: PubMed Search, Vector DB Store, Vector Search (工具层)
- **Vector Database**: Chroma/FAISS for semantic retrieval (向量数据库)
- **LLM Layer**: GPT-4o for reasoning and summarization (语言模型层)

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
pip install -r requirements.txt

# 5. 配置环境变量 (Configure environment variables)
# 复制 .env.example 为 .env
copy .env.example .env

# 6. 编辑 .env 文件，填入您的配置
# Edit .env file and fill in your configuration:
#   - OPENAI_API_KEY: 您的 OpenAI API 密钥
#   - OPENAI_MODEL: 选择模型 (gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo 等)
#   - PUBMED_EMAIL: 您的邮箱 (推荐)
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
pip install -r requirements.txt
```

### 环境变量配置 (Environment Variables Setup)

```bash
# 复制环境变量模板文件
# Copy environment variables template
cp .env.example .env

# 编辑 .env 文件，填入你的API密钥
# Edit .env file and fill in your API keys
# 必需配置:
# - OPENAI_API_KEY: 你的API密钥（OpenAI或其他兼容服务的密钥）
# Required configuration:
# - OPENAI_API_KEY: Your API key (OpenAI or other compatible service)
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

- **嵌入模型 (Embedding Model)**: 
  - 支持独立供应商配置，默认与 LLM 供应商一致
  - 如果填写 `EMBEDDING_API_KEY` 和 `EMBEDDING_BASE_URL`，则使用独立的 embedding 服务
  - 本地模型支持（如 LM Studio）: `EMBEDDING_BASE_URL=http://localhost:1234/v1`
  - 模型示例: `text-embedding-3-small`, `text-embedding-3-large`, `text-embedding-ada-002`

详细配置说明请参考 `.env.example` 文件中的注释。

## 📚 Features (功能特性)

- 🔍 **PubMed Integration**: Search and retrieve literature from PubMed database (PubMed集成)
- 🧠 **ReAct Framework**: Transparent reasoning with Thought → Action → Observation cycles (ReAct框架)
- 💾 **Vector Storage**: Embed and store long texts to reduce hallucinations (向量存储)
- 🔎 **Semantic Search**: RAG-based retrieval and reasoning (语义搜索)
- 📖 **Reference Management**: Proper citation formatting with PMID references (参考文献管理)
- 🔧 **Extensible Tools**: Modular tool system supporting future MCP integration (可扩展工具)
- 🌏 **Multi-language Support**: English and Chinese language support (多语言支持)
- 🔧 **Language Detection**: Automatic language detection and prompt selection (语言检测)

## 🎖️ Design Principles (设计原则)

| Principle | Description | 说明 |
|------------|-------------|
| 🧠 **Transparent Reasoning** | Maintain Thought/Action/Observation records (透明推理) |
| 🔒 **Controlled Hallucinations** | All answers must come from vector database content (可控幻觉) |
| 🧩 **Modular Decoupling** | Separate tool, reasoning, and database layers (模块解耦) |
| 🔄 **Sustainable Updates** | Support automatic embedding and cleanup of new literature (可持续更新) |
| 🔧 **Adjustable Logic** | Allow custom prompts or programmatic logic (可调逻辑) |
| 🌐 **Open Standards** | Compatible with MCP, LangChain, LlamaIndex ecosystems (开放标准) |
| 🌏 **Multi-language Support** | English and Chinese language support (多语言支持) |

## 📊 Success Metrics (成功指标)

- **Retrieval Accuracy**: RAG recall consistency ≥ 85% (检索准确率)
- **Hallucination Rate**: False statements ≤ 10% (幻觉率)
- **Latency**: Response time ≤ 8 seconds (延迟)
- **Explainability**: Every output includes reasoning traces (可解释性)
- **Extensibility**: New tools can be integrated in 10 lines of code (扩展性)
- **Language Support**: Automatic detection and optimal prompt selection (语言支持)

## 🔮 Future Directions (未来方向)

1. 🔬 Multi-source retrieval (PubMed + arXiv + Semantic Scholar) (多源检索)
2. 🧩 Multi-model fusion (GPT-4o + BioMedLM + Claude) (多模型融合)
3. 🧠 Self-Reflection / Self-Verification capabilities (自我反思)
4. 🌐 Web UI support (Streamlit / Gradio) (Web界面)
5. 📚 Sustainable, updatable scientific knowledge base (可持续知识库)
6. 🌏 More language support (Japanese, Korean, etc.) (更多语言支持)

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

This **ReAct PubMed Agent** is not just a "chatbot" - it's a **scientific intelligence agent** (科学智能体) with:
- 🧠 **Self-thinking** capabilities through ReAct framework (自我思考)
- 🔧 **Self-action** abilities through tool orchestration (自我行动)
- 🔍 **Explainability** through transparent reasoning traces (可解释性)
- 🚀 **Extensibility** through modular architecture (可扩展性)
- 🌏 **Multi-language support** for broader accessibility (多语言支持)

**You're not just training models—you're orchestrating intelligence!** (您不是在训练模型——您在编排智能！) 🚀

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

**详细文档**: 查看 [CLI_USAGE.md](CLI_USAGE.md) 获取完整的命令行使用指南。

**Documentation**: See [CLI_USAGE.md](CLI_USAGE.md) for complete CLI usage guide.

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
   pip install -r requirements.txt
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

---

**🎉 Ready for Production! (准备投产！)**

The complete ReAct PubMed Agent with comprehensive Chinese language support is now ready for scientific research and analysis in both English and Chinese!

**🚀 快速体验 (Quick Experience)**:
```powershell
python query.py -question:"mRNA疫苗的作用机制是什么？"
```