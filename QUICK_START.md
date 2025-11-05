# 🚀 快速开始指南 (Quick Start Guide)

本指南将帮助您快速配置和运行 ReAct PubMed Agent。

This guide will help you quickly configure and run the ReAct PubMed Agent.

---

## 📋 前置要求 (Prerequisites)

- Python 3.8+ (推荐 3.10+)
- uv (推荐) 或 pip
- OpenAI API 密钥

---

## ⚡ 使用 uv 快速安装 (推荐)

### 步骤 1: 安装 uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 验证安装
uv --version
```

### 步骤 2: 克隆项目并进入目录

```bash
git clone <repository-url>
cd PubMed-Agent
```

### 步骤 3: 创建虚拟环境并安装依赖

```bash
# 创建虚拟环境
uv venv

# 激活虚拟环境
source .venv/bin/activate  # macOS/Linux
# 或
.venv\Scripts\activate      # Windows

# 安装所有依赖
uv pip install -r requirements.txt
```

### 步骤 4: 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入你的API密钥
# 使用你喜欢的编辑器，例如：
# macOS/Linux: nano .env 或 vim .env
# Windows: notepad .env
```

**必需配置的最小环境变量**:
```bash
OPENAI_API_KEY=sk-your-actual-api-key-here
# 或使用自定义endpoint
OPENAI_API_KEY=your-api-key-here
OPENAI_API_BASE=http://localhost:8000/v1
```

**推荐配置**:
```bash
OPENAI_API_KEY=sk-your-actual-api-key-here
PUBMED_EMAIL=your_email@example.com
# 如果使用自定义endpoint，取消注释下面这行
# OPENAI_API_BASE=http://localhost:8000/v1
```

### 自定义API Endpoint (Custom API Endpoint)

如果您想使用本地部署的模型或其他兼容OpenAI API的服务，可以配置 `OPENAI_API_BASE`:

```bash
# 示例1: 本地vLLM部署的模型
OPENAI_API_BASE=http://localhost:8000/v1
OPENAI_API_KEY=EMPTY  # 如果本地模型不需要密钥
OPENAI_MODEL=your-local-model-name

# 示例2: Azure OpenAI
OPENAI_API_BASE=https://YOUR_RESOURCE.openai.azure.com/
OPENAI_API_KEY=your-azure-api-key

# 示例3: 其他兼容服务
OPENAI_API_BASE=https://api.example.com/v1
OPENAI_API_KEY=your-api-key
```

**注意**: 如果设置了 `OPENAI_API_BASE`，将使用自定义endpoint；否则使用默认的OpenAI API (`https://api.openai.com/v1`)。

### 步骤 5: 运行示例

#### 方式1: 使用命令行（推荐）

```bash
# 安装包（使CLI命令可用）
uv pip install -e .

# 基本查询
pubmed-agent query "mRNA疫苗的作用机制是什么？"

# 交互式模式
pubmed-agent interactive

# 搜索文献
pubmed-agent search "COVID-19 vaccine" --max-results 5
```

#### 方式2: 使用Python脚本

```bash
# 运行中文演示
python examples/chinese_demo.py

# 或运行快速测试
python quick_test.py

# 或运行简单示例
python run_example.py
```

**注意**: 首次使用CLI前需要先安装包：`uv pip install -e .` 或 `pip install -e .`

---

## 🔧 使用传统 pip 安装

### 步骤 1: 创建虚拟环境

```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate     # Windows
```

### 步骤 2: 安装依赖

```bash
pip install -r requirements.txt
```

### 步骤 3: 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件
```

---

## 📝 环境变量配置说明

### 必需的环境变量

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `OPENAI_API_KEY` | OpenAI API密钥 | `sk-proj-...` |

### 可选但推荐的环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `PUBMED_EMAIL` | PubMed API要求的邮箱 | 无 |
| `OPENAI_MODEL` | 使用的OpenAI模型 | `gpt-4o` |

### 其他可选环境变量

查看 `.env.example` 文件了解所有可配置选项。

---

## 🎯 快速测试

### 测试基本功能

```python
from pubmed_agent import PubMedAgent

# 初始化代理（自动检测语言）
agent = PubMedAgent(language="auto")

# 查询科学问题
response = agent.query("mRNA疫苗的作用机制是什么？")
print(response['answer'])
```

### 测试中文支持

```bash
python examples/chinese_demo.py
```

---

## 🐛 常见问题 (Troubleshooting)

### 问题 1: 找不到 `.env` 文件

**解决方案**: 
```bash
cp .env.example .env
# 然后编辑 .env 文件填入你的API密钥
```

### 问题 2: OpenAI API 密钥错误

**解决方案**: 
- 检查 `.env` 文件中的 `OPENAI_API_KEY` 是否正确
- 确保API密钥有效且有足够的额度
- 访问 https://platform.openai.com/api-keys 获取新密钥

### 问题 3: 依赖安装失败

**解决方案**:
```bash
# 使用 uv (推荐)
uv pip install -r requirements.txt

# 或使用 pip
pip install --upgrade pip
pip install -r requirements.txt
```

### 问题 4: uv 命令未找到

**解决方案**:
```bash
# 重新安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 或添加到 PATH
export PATH="$HOME/.cargo/bin:$PATH"
```

---

## 📚 下一步

- 查看 [README.md](README.md) 了解完整功能
- 查看 [examples/](examples/) 目录了解更多示例
- 阅读项目文档了解高级用法

---

## 💡 提示

1. **使用 uv**: uv 比传统 pip 快 10-100 倍，强烈推荐
2. **环境变量**: 确保 `.env` 文件在项目根目录
3. **虚拟环境**: 始终在虚拟环境中运行项目
4. **API密钥安全**: 不要将 `.env` 文件提交到 Git

---

**🎉 现在您已经准备好使用 ReAct PubMed Agent 了！**

