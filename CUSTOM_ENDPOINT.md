# 🔧 自定义API Endpoint配置指南

本指南说明如何配置和使用自定义API endpoint，以支持本地部署的模型或其他兼容OpenAI API的服务。

## 📋 概述

ReAct PubMed Agent 支持使用自定义API endpoint，允许您：
- 使用本地部署的模型（vLLM、llama.cpp等）
- 使用Azure OpenAI服务
- 使用其他兼容OpenAI API的服务

## 🚀 快速配置

### 方法1: 使用环境变量（推荐）

在 `.env` 文件中配置：

```bash
# 必需：API密钥（如果服务需要）
OPENAI_API_KEY=your-api-key-here

# 可选：自定义endpoint（留空则使用默认OpenAI API）
OPENAI_API_BASE=http://localhost:8000/v1

# 可选：模型名称（根据您的服务调整）
OPENAI_MODEL=your-model-name
```

### 方法2: 在代码中配置

```python
from pubmed_agent import AgentConfig, PubMedAgent

# 创建自定义配置
config = AgentConfig(
    openai_api_key="your-api-key",
    openai_api_base="http://localhost:8000/v1",
    openai_model="your-model-name"
)

# 使用自定义配置创建agent
agent = PubMedAgent(config=config, language="auto")
```

## 📝 配置示例

### 示例1: 本地vLLM部署

```bash
# .env 文件配置
OPENAI_API_KEY=EMPTY  # 如果本地模型不需要密钥
OPENAI_API_BASE=http://localhost:8000/v1
OPENAI_MODEL=llama-2-7b-chat  # 根据您的模型名称调整
```

**启动vLLM服务**:
```bash
python -m vllm.entrypoints.openai.api_server \
    --model your-model-name \
    --port 8000
```

### 示例2: 本地llama.cpp部署

```bash
# .env 文件配置
OPENAI_API_KEY=sk-no-key-required
OPENAI_API_BASE=http://localhost:8080/v1
OPENAI_MODEL=your-model-name
```

**启动llama.cpp服务**:
```bash
# 使用llama-cpp-python的OpenAI兼容服务器
python -m llama_cpp.server \
    --model your-model.gguf \
    --port 8080
```

### 示例3: Azure OpenAI

```bash
# .env 文件配置
OPENAI_API_KEY=your-azure-api-key
OPENAI_API_BASE=https://YOUR_RESOURCE.openai.azure.com/
OPENAI_MODEL=gpt-4  # Azure部署的模型名称
```

### 示例4: 其他兼容服务

```bash
# .env 文件配置
OPENAI_API_KEY=your-api-key
OPENAI_API_BASE=https://api.example.com/v1
OPENAI_MODEL=your-model-name
```

## 🔍 验证配置

运行以下代码验证配置是否正确：

```python
from pubmed_agent import PubMedAgent

# 创建agent（会自动加载.env配置）
agent = PubMedAgent(language="auto")

# 测试查询
response = agent.query("Hello, can you respond?")
print(response['answer'])
```

如果看到日志输出 `Using custom API endpoint: http://localhost:8000/v1`，说明配置成功。

## ⚠️ 注意事项

1. **API兼容性**: 确保您的服务完全兼容OpenAI API格式，包括：
   - `/v1/chat/completions` 端点
   - 请求/响应格式
   - 认证方式

2. **模型名称**: 不同服务的模型名称可能不同，请根据实际情况调整 `OPENAI_MODEL`。

3. **API密钥**: 某些服务可能不需要API密钥，可以设置为空字符串或 `EMPTY`。

4. **网络连接**: 确保能够访问您配置的endpoint地址。

5. **错误处理**: 如果遇到连接错误，请检查：
   - endpoint地址是否正确
   - 服务是否正在运行
   - 防火墙设置是否允许连接

## 🛠️ 故障排除

### 问题1: 连接被拒绝

**错误**: `Connection refused` 或 `ConnectionError`

**解决方案**:
- 检查服务是否正在运行
- 验证endpoint地址和端口是否正确
- 检查防火墙设置

### 问题2: 401 Unauthorized

**错误**: `401 Unauthorized`

**解决方案**:
- 检查API密钥是否正确
- 某些服务可能需要特定的认证格式

### 问题3: 模型不存在

**错误**: `Model not found` 或 `Invalid model`

**解决方案**:
- 检查 `OPENAI_MODEL` 是否与服务的模型名称匹配
- 查看服务文档确认可用的模型名称

### 问题4: 格式不兼容

**错误**: `Invalid request format` 或 `Unsupported endpoint`

**解决方案**:
- 确保服务完全兼容OpenAI API格式
- 检查服务版本和文档

## 📚 相关资源

- [OpenAI API文档](https://platform.openai.com/docs/api-reference)
- [vLLM文档](https://docs.vllm.ai/)
- [llama.cpp文档](https://github.com/ggerganov/llama.cpp)
- [Azure OpenAI文档](https://learn.microsoft.com/azure/ai-services/openai/)

## 💡 提示

- 使用本地模型可以避免API费用，适合大量测试
- 本地模型通常响应速度更快，延迟更低
- 可以根据需要选择不同大小的模型（7B、13B、70B等）
- 建议在开发环境使用本地模型，生产环境使用云服务

---

**需要帮助？** 查看 [QUICK_START.md](QUICK_START.md) 或提交 Issue。

