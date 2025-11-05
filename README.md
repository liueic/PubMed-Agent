# 🧬 ReAct PubMed Agent

An intelligent research assistant that can retrieve, understand, store, and reason about scientific literature from PubMed using the ReAct (Reasoning and Acting) framework.

## 🎯 Project Goals

This agent is designed to:
1. **Retrieve** literature from PubMed and other scientific databases
2. **Embed and store** long text abstracts to reduce hallucinations
3. **Perform semantic search (RAG) and reasoning** based on user questions
4. Maintain clear **"Thought → Action → Observation"** reasoning traces (ReAct framework)
5. Support **extensibility**: multi-tool integration, MCP standardization, knowledge base updates

## 🏗️ System Architecture

```
User Query → ReAct Controller → Tools Layer → Vector Database → LLM Summarization → Final Answer
```

### Core Components

- **ReAct Controller**: Orchestrates reasoning cycles
- **Tools Layer**: PubMed Search, Vector DB Store, Vector Search
- **Vector Database**: Chroma/FAISS for semantic retrieval
- **LLM Layer**: GPT-4o for reasoning and summarization

## 🚀 Quick Start

```python
from pubmed_agent import PubMedAgent

# Initialize agent
agent = PubMedAgent()

# Query scientific literature
response = agent.query("What are the mechanisms of action for COVID-19 vaccines?")
print(response)
```

## 📦 Installation

```bash
# Clone the repository
git clone <repository-url>
cd PubMed-Agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys
```

## 📚 Features

- 🔍 **PubMed Integration**: Search and retrieve literature from PubMed database
- 🧠 **ReAct Framework**: Transparent reasoning with Thought → Action → Observation cycles
- 💾 **Vector Storage**: Embed and store long texts to reduce hallucinations
- 🔎 **Semantic Search**: RAG-based retrieval and reasoning
- 📖 **Reference Management**: Proper citation formatting with PMID references
- 🔧 **Extensible Tools**: Modular tool system supporting future MCP integration

## 🎖️ Design Principles

| Principle | Description |
|------------|-------------|
| 🧠 **Transparent Reasoning** | Maintain Thought/Action/Observation records |
| 🔒 **Controlled Hallucinations** | All answers must come from vector database content |
| 🧩 **Modular Decoupling** | Separate tool, reasoning, and database layers |
| 🔄 **Sustainable Updates** | Support automatic embedding and cleanup of new literature |
| 🔧 **Adjustable Logic** | Allow custom prompts or programmatic logic |
| 🌐 **Open Standards** | Compatible with MCP, LangChain, LlamaIndex ecosystems |

## 📊 Success Metrics

- **Retrieval Accuracy**: RAG recall consistency ≥ 85%
- **Hallucination Rate**: False statements ≤ 10%
- **Latency**: Response time ≤ 8 seconds
- **Explainability**: Every output includes reasoning traces
- **Extensibility**: New tools can be integrated in 10 lines of code

## 🔮 Future Directions

1. 🔬 Multi-source retrieval (PubMed + arXiv + Semantic Scholar)
2. 🧩 Multi-model fusion (GPT-4o + BioMedLM + Claude)
3. 🧠 Self-Reflection / Self-Verification capabilities
4. 🌐 Web UI support (Streamlit / Gradio)
5. 📚 Sustainable, updatable scientific knowledge base

---

This **ReAct PubMed Agent** is not just a "chatbot" - it's a **scientific intelligence agent** with self-thinking, self-action capabilities, explainability, and extensibility.

We're not "training models" - we're **orchestrating intelligence**: combining language models + tools + data + reasoning rules to create a trustworthy, transparent, and evolving intelligent research assistant.