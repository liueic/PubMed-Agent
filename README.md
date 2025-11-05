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

```bash
# Clone repository (克隆仓库)
git clone <repository-url>
cd PubMed-Agent

# Create virtual environment (创建虚拟环境)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (安装依赖)
pip install -r requirements.txt

# Set up environment variables (设置环境变量)
cp .env.example .env
# Edit .env with your API keys (编辑.env文件填入API密钥)
```

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