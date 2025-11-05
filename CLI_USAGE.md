# 🖥️ 命令行使用指南 (CLI Usage Guide)

ReAct PubMed Agent 提供了完整的命令行接口，让您可以直接从终端使用所有功能。

## 📦 安装

安装后，CLI会自动注册为 `pubmed-agent` 命令：

```bash
# 使用 uv 安装（推荐）
uv pip install -e .

# 或使用 pip
pip install -e .
```

## 🚀 快速开始

### 基本查询

```bash
# 中文查询
pubmed-agent query "mRNA疫苗的作用机制是什么？"

# 英文查询
pubmed-agent query "What are the mechanisms of mRNA vaccines?"

# 自动检测语言
pubmed-agent query "mRNA vaccine mechanism"
```

### 交互式模式

```bash
# 启动交互式模式
pubmed-agent interactive

# 或使用简写
pubmed-agent i
```

在交互式模式下，您可以连续提问，输入 `quit` 或 `exit` 退出。

## 📋 命令详解

### 1. query - 查询命令

查询科学问题并获取答案。

**语法**:
```bash
pubmed-agent query <问题> [选项]
```

**示例**:
```bash
# 基本查询
pubmed-agent query "CRISPR-Cas9的工作原理"

# 指定语言
pubmed-agent query "How does CRISPR work?" --language en

# 指定提示词类型
pubmed-agent query "疫苗的副作用" --prompt-type therapeutic

# 显示详细信息
pubmed-agent query "基因编辑技术" --verbose
```

**选项**:
- `--language, -l`: 语言设置 (en/zh/auto，默认: auto)
- `--prompt-type`: 提示词类型 (scientific/mechanism/therapeutic/complex)
- `--api-key, -k`: API密钥（覆盖环境变量）
- `--api-base, -b`: 自定义API端点
- `--model, -m`: 模型名称
- `--verbose, -v`: 显示详细信息

### 2. search - 搜索命令

搜索PubMed文献并存储到向量数据库。

**语法**:
```bash
pubmed-agent search <查询> [选项]
```

**示例**:
```bash
# 搜索并存储文献
pubmed-agent search "COVID-19 vaccine"

# 限制结果数量
pubmed-agent search "mRNA vaccine" --max-results 5

# 使用自定义API
pubmed-agent search "gene therapy" --api-base http://localhost:8000/v1
```

**选项**:
- `--max-results, -n`: 最大结果数（默认: 10）
- `--language, -l`: 语言设置
- `--api-key, -k`: API密钥
- `--api-base, -b`: 自定义API端点
- `--model, -m`: 模型名称
- `--verbose, -v`: 显示详细信息

### 3. interactive - 交互式模式

启动交互式对话模式，可以连续提问。

**语法**:
```bash
pubmed-agent interactive [选项]
# 或
pubmed-agent i [选项]
```

**示例**:
```bash
# 启动交互式模式
pubmed-agent interactive

# 使用中文模式
pubmed-agent interactive --language zh

# 使用自定义API
pubmed-agent interactive --api-base http://localhost:8000/v1
```

**交互式命令**:
- 输入问题并按回车查询
- 输入 `quit`、`exit` 或 `q` 退出
- 按 `Ctrl+C` 退出

### 4. stats - 统计信息

显示Agent的统计信息和配置。

**语法**:
```bash
pubmed-agent stats [选项]
```

**示例**:
```bash
# 显示统计信息
pubmed-agent stats

# 显示详细信息
pubmed-agent stats --verbose
```

## 🔧 全局选项

所有命令都支持以下全局选项：

### 语言设置

```bash
# 英文模式
pubmed-agent query "..." --language en

# 中文模式
pubmed-agent query "..." --language zh

# 自动检测（默认）
pubmed-agent query "..." --language auto
```

### API配置

```bash
# 使用命令行指定API密钥
pubmed-agent query "..." --api-key sk-your-key-here

# 使用自定义endpoint
pubmed-agent query "..." --api-base http://localhost:8000/v1

# 指定模型
pubmed-agent query "..." --model gpt-4
```

### 详细输出

```bash
# 显示详细信息（包括推理步骤、语言等）
pubmed-agent query "..." --verbose
```

## 📝 使用场景示例

### 场景1: 快速查询

```bash
# 快速查询一个问题
pubmed-agent query "mRNA疫苗的作用机制是什么？"
```

### 场景2: 深入研究

```bash
# 启动交互式模式进行多轮对话
pubmed-agent interactive

# 在交互式模式中：
❓ 问题: mRNA疫苗的原理是什么？
❓ 问题: 它和传统疫苗有什么区别？
❓ 问题: 有哪些副作用？
```

### 场景3: 文献收集

```bash
# 搜索相关文献并存储
pubmed-agent search "COVID-19 vaccine safety" --max-results 20

# 然后查询已存储的文献
pubmed-agent interactive
```

### 场景4: 使用本地模型

```bash
# 配置.env文件
OPENAI_API_BASE=http://localhost:8000/v1
OPENAI_MODEL=llama-2-7b-chat

# 或使用命令行参数
pubmed-agent query "Hello" --api-base http://localhost:8000/v1 --model llama-2-7b-chat
```

## 🎯 高级用法

### 组合使用

```bash
# 先搜索文献
pubmed-agent search "gene therapy" --max-results 10

# 然后查询相关问题
pubmed-agent query "基因治疗的最新进展是什么？"
```

### 批量处理

```bash
# 使用shell脚本批量查询
for question in "问题1" "问题2" "问题3"; do
    pubmed-agent query "$question" --language zh
    echo "---"
done
```

### 输出重定向

```bash
# 保存结果到文件
pubmed-agent query "..." > result.txt

# 保存详细输出
pubmed-agent query "..." --verbose > detailed_result.txt
```

## ⚙️ 配置优先级

配置选项的优先级（从高到低）：

1. 命令行参数（最高优先级）
2. 环境变量（`.env` 文件）
3. 默认值（最低优先级）

**示例**:
```bash
# .env文件中设置了 OPENAI_API_KEY=sk-default
# 命令行使用 --api-key sk-custom 会覆盖环境变量
pubmed-agent query "..." --api-key sk-custom
```

## 🐛 故障排除

### 问题1: 命令未找到

**错误**: `command not found: pubmed-agent`

**解决方案**:
```bash
# 确保已安装包
pip install -e .

# 或使用Python模块方式
python -m pubmed_agent query "..."
```

### 问题2: API密钥错误

**错误**: `API key not found`

**解决方案**:
```bash
# 方法1: 设置环境变量
export OPENAI_API_KEY=sk-your-key

# 方法2: 使用命令行参数
pubmed-agent query "..." --api-key sk-your-key

# 方法3: 配置.env文件
echo "OPENAI_API_KEY=sk-your-key" >> .env
```

### 问题3: 连接错误

**错误**: `Connection refused` 或连接超时

**解决方案**:
- 检查网络连接
- 验证API endpoint是否正确
- 检查防火墙设置

## 💡 提示

1. **使用交互式模式**: 对于连续的多轮对话，使用 `interactive` 模式更高效
2. **保存常用命令**: 创建shell别名或脚本保存常用命令
3. **组合使用**: 先 `search` 收集文献，再 `query` 查询相关问题
4. **使用别名**: 在 `~/.bashrc` 或 `~/.zshrc` 中添加：
   ```bash
   alias pa='pubmed-agent'
   ```

## 📚 相关文档

- [快速开始指南](QUICK_START.md)
- [自定义Endpoint配置](CUSTOM_ENDPOINT.md)
- [完整README](README.md)

---

**享受命令行使用的便利！** 🚀

