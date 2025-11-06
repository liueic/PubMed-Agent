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

> 💡 **快速开始**: 查看 [QUICK_START.md](QUICK_START.md) 获取详细的安装和配置指南
> 
> 💡 **Quick Start**: See [QUICK_START.md](QUICK_START.md) for detailed installation and configuration guide

### 方法1: 使用 uv (推荐 / Recommended)

```bash
# 安装 uv (如果尚未安装)
# Install uv (if not already installed)
# macOS/Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows:
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 克隆仓库
# Clone repository
git clone <repository-url>
cd PubMed-Agent

# 使用 uv 创建虚拟环境并安装依赖
# Create virtual environment and install dependencies with uv
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 安装依赖
# Install dependencies
uv pip install -r requirements.txt

# 或者使用 uv 直接安装（更快）
# Or use uv to install directly (faster)
uv pip sync requirements.txt
```

### 方法2: 使用传统 pip (Traditional pip)

```bash
# Clone repository (克隆仓库)
git clone <repository-url>
cd PubMed-Agent

# Create virtual environment (创建虚拟环境)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

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

#### PubMed API 配置 (PubMed API Configuration)

**重要提示**: NCBI要求提供真实的email地址以符合使用政策。强烈建议配置 `PUBMED_EMAIL` 和 `PUBMED_API_KEY`。

**Important**: NCBI requires a real email address to comply with usage policies. It is strongly recommended to configure `PUBMED_EMAIL` and `PUBMED_API_KEY`.

**配置步骤 (Configuration Steps)**:

1. **注册NCBI账户 (Register NCBI Account)**:
   - 访问 https://www.ncbi.nlm.nih.gov/
   - 点击右上角"登录" → "创建新账户"
   - 填写必要信息完成注册

2. **获取API密钥 (Get API Key)** (可选但推荐):
   - 登录NCBI账户
   - 进入"我的NCBI" → 找到"API密钥"选项
   - 生成并复制您的API密钥

3. **配置环境变量 (Configure Environment Variables)**:
```bash
# 必需配置（强烈推荐）
# Required configuration (strongly recommended)
PUBMED_EMAIL=your_email@example.com

# 可选配置（推荐以提升速率限制：从3次/秒提升至10次/秒）
# Optional configuration (recommended to increase rate limit: from 3 to 10 requests/sec)
PUBMED_API_KEY=your_ncbi_api_key

# 可选：自定义工具名称
# Optional: Custom tool name
PUBMED_TOOL_NAME=pubmed_agent
```

**速率限制说明 (Rate Limit Information)**:
- **未配置API Key**: 3次/秒
- **配置API Key**: 10次/秒
- **未配置Email**: 使用临时邮箱，可能导致API访问受限

**Rate Limit Information**:
- **Without API Key**: 3 requests/second
- **With API Key**: 10 requests/second
- **Without Email**: Using temporary email may result in API access restrictions

#### 自定义API Endpoint (Custom API Endpoint)

项目支持使用自定义API endpoint，允许您使用：
- 本地部署的模型（如vLLM、llama.cpp等）
- Azure OpenAI服务
- 其他兼容OpenAI API的服务

**配置方法**:
```bash
# 在 .env 文件中设置
OPENAI_API_BASE=http://localhost:8000/v1  # 本地模型
# 或
OPENAI_API_BASE=https://YOUR_RESOURCE.openai.azure.com/  # Azure OpenAI
# 或留空使用默认OpenAI API
```

**支持的endpoint格式**:
- 本地模型: `http://localhost:8000/v1`
- Azure OpenAI: `https://YOUR_RESOURCE.openai.azure.com/`
- 其他兼容服务: `https://api.example.com/v1`

**重要提示**: 请确保在运行代码前已正确配置 `.env` 文件。项目会自动加载 `.env` 文件中的环境变量。如果设置了 `OPENAI_API_BASE`，将使用自定义endpoint；否则使用默认的OpenAI API。

**Important**: Make sure to configure the `.env` file correctly before running the code. The project will automatically load environment variables from the `.env` file. If `OPENAI_API_BASE` is set, it will use the custom endpoint; otherwise, it will use the default OpenAI API.

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

### Basic Usage (基本使用)
```python
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

### Advanced Features (高级功能)
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
```

---

**🎉 Ready for Production! (准备投产！)**

The complete ReAct PubMed Agent with comprehensive Chinese language support is now ready for scientific research and analysis in both English and Chinese!