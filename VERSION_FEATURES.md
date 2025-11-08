# 🚀 版本特性说明 - v0.2.0

## 📋 版本概述

本次更新主要实现了内部 MCP 后端集成、角色提示词系统、自动 Markdown 保存、多模型供应商支持、以及配置系统全面完善。

## ✨ 主要特性

### 1. 🔌 内部 Python MCP 后端集成
- ✅ **完整的 Python MCP 实现**：
  - 从 Node.js MCP 服务器迁移到 Python
  - 支持 PubMed 搜索、详情获取、全文下载、EndNote 导出
  - 完整的缓存系统（内存缓存 + 文件缓存）
  - 代理支持和速率限制
  - 跨平台全文下载支持（Windows PowerShell、Linux wget、macOS curl）

- ✅ **MCP 后端特性**：
  - `pubmed_mcp/backend.py`: 核心 PubMed API 交互逻辑
  - `pubmed_mcp/client.py`: 高级客户端接口
  - `pubmed_mcp/http.py`: HTTP 客户端（支持代理）
  - `pubmed_mcp/cache.py`: 缓存管理
  - `pubmed_mcp/config.py`: 配置管理

- ✅ **工具集成**：
  - `PubMedSearchTool` 和 `PubMedFetchTool` 已迁移到使用内部 MCP 后端
  - 移除对 `biopython` 的直接依赖
  - 保持向后兼容的 API 接口

### 2. 🎭 角色提示词系统
- ✅ **角色加载机制**：
  - 支持从 Markdown 文件加载角色提示词
  - 自动检测 `agents/` 目录下的角色文件
  - 默认自动加载 "Synapse Scholar" 角色（如果文件存在）

- ✅ **角色配置**：
  - `AGENT_ROLE_NAME`: 通过角色名称加载（在 `agents/` 目录查找）
  - `AGENT_ROLE_FILE`: 通过文件路径加载（支持绝对路径和相对路径）
  - 角色提示词自动合并到系统提示词中

- ✅ **实现细节**：
  - `pubmed_agent/role_loader.py`: 角色加载工具
  - 支持 LangChain 0.x 和 1.0+ 版本
  - 自动移除 Markdown 标题，只保留内容

### 3. 📄 自动 Markdown 保存功能
- ✅ **自动保存**：
  - 每次查询后自动保存为 Markdown 文档
  - 保存位置：项目根目录
  - 文件名格式：`pubmed_query_YYYYMMDD_HHMMSS_问题摘要.md`

- ✅ **Markdown 内容**：
  - 完整的元数据（问题、状态、语言、提示词类型、线程ID）
  - 完整的答案内容
  - 推理过程（如果启用 verbose 模式）
  - 错误信息（如果查询失败）

- ✅ **实现位置**：
  - `pubmed_agent/output_utils.py`: Markdown 生成和保存工具
  - `query.py`: 集成自动保存
  - `pubmed_agent/cli.py`: CLI 命令集成自动保存

### 4. 🖥️ Windows 本地部署支持
- ✅ 完整的 Windows PowerShell 命令示例
- ✅ 优化的路径处理和目录创建
- ✅ 详细的 Windows 部署指南
- ✅ 支持 Windows 路径格式的配置项

### 5. 🔧 多模型供应商支持
- ✅ **LLM 多供应商支持**：
  - 支持 OpenAI、Azure OpenAI、本地模型（LM Studio）等
  - 自定义 `LLM_BASE_URL` 和 `LLM_API_KEY`
  - 用户可自由填写模型名称
  - 向后兼容原有的 `OPENAI_API_KEY` 配置

- ✅ **Embedding 独立供应商支持**：
  - 支持独立的 embedding 供应商配置
  - 默认与 LLM 供应商一致（自动继承）
  - 可单独配置 `EMBEDDING_API_KEY` 和 `EMBEDDING_BASE_URL`
  - 支持本地模型（如 LM Studio: `http://localhost:1234/v1`）

### 6. 📝 环境配置文件完善
- ✅ 创建完整的 `.env.example` 文件
- ✅ 支持多种模型选择（gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo 等）
- ✅ 详细的中英文配置说明
- ✅ 推理参数优化（TEMPERATURE=0.7, TOP_P=0.95）
- ✅ 角色提示词配置说明

### 7. 💻 命令行工具增强
- ✅ 修复 CLI 环境变量传递问题（支持 `LLM_API_KEY`）
- ✅ 新增 `query.py` 命令行查询工具
- ✅ 支持 `-question:"问题"` 格式参数
- ✅ 支持多轮对话模式（`-conversation`）
- ✅ 支持语言选择（`-language:en|zh|auto`）
- ✅ 支持详细模式（`-verbose` 显示推理过程）
- ✅ 友好的错误提示和环境检查

### 8. 📚 文档更新
- ✅ README 全面更新，包含所有新功能
- ✅ 添加 Windows 快速开始指南
- ✅ 添加多模型供应商配置说明
- ✅ 添加角色提示词使用说明
- ✅ 添加自动保存功能说明
- ✅ 添加常见问题（FAQ）
- ✅ 更新使用示例和最佳实践

### 9. 🛠️ 代码质量提升
- ✅ 创建 `pubmed_mcp/` 包（完整的 MCP 后端实现）
- ✅ 创建 `pubmed_agent/role_loader.py`（角色加载工具）
- ✅ 创建 `pubmed_agent/output_utils.py`（Markdown 输出工具）
- ✅ 完善配置管理系统
- ✅ 更新 Cursor Rules 规范
- ✅ 添加 `.gitignore` 文件（排除虚拟环境、.env、.cursor 等）

## 🔄 配置变更

### 新增环境变量

**LLM 配置**：
- `LLM_API_KEY`: 通用 API Key（支持多种供应商）
- `LLM_BASE_URL`: 自定义 API 端点（可选）
- `LLM_MODEL`: 模型名称（用户可自由填写）
- `TEMPERATURE`: 默认 0.7
- `TOP_P`: 默认 0.95

**Embedding 配置**：
- `EMBEDDING_API_KEY`: Embedding API Key（可选，默认使用 LLM_API_KEY）
- `EMBEDDING_BASE_URL`: Embedding Base URL（可选，默认使用 LLM_BASE_URL）
- `EMBEDDING_MODEL`: Embedding 模型名称

**PubMed MCP Backend 配置**：
- `PUBMED_BACKEND`: 选择 `python_mcp`（默认）或 `direct`（NCBI E-utilities）
- `PUBMED_MCP_BASE_DIR`: MCP 缓存与导出文件目录（默认 `./cache`）
- `ABSTRACT_MODE`: `quick`（1500 字符）或 `deep`（6000 字符）
- `FULLTEXT_MODE`: `disabled`、`enabled`、`auto`
- `ENDNOTE_EXPORT`: `enabled` / `disabled`
- `PROXY_ENABLED`: 代理启用状态
- `HTTP_PROXY` / `HTTPS_PROXY`: 代理地址
- `PROXY_USERNAME` / `PROXY_PASSWORD`: 代理认证

**角色提示词配置**：
- `AGENT_ROLE_NAME`: 角色名称（如 "Synapse Scholar"）
- `AGENT_ROLE_FILE`: 角色文件路径（可选，会覆盖 `AGENT_ROLE_NAME`）

### 向后兼容

- ✅ 仍支持 `OPENAI_API_KEY` 和 `OPENAI_MODEL`
- ✅ 现有配置无需修改即可使用
- ✅ 工具接口保持向后兼容

## 📦 新增文件

### 核心模块
- `pubmed_mcp/__init__.py`: MCP 包初始化
- `pubmed_mcp/config.py`: MCP 配置管理
- `pubmed_mcp/http.py`: HTTP 客户端（支持代理）
- `pubmed_mcp/cache.py`: 缓存管理
- `pubmed_mcp/backend.py`: 核心 PubMed API 交互逻辑
- `pubmed_mcp/client.py`: 高级客户端接口

### 工具模块
- `pubmed_agent/role_loader.py`: 角色提示词加载工具
- `pubmed_agent/output_utils.py`: Markdown 输出工具

### 配置文件
- `query.py`: 命令行查询工具
- `.env.example`: 完整的环境配置示例（已更新）
- `.gitignore`: Git 忽略规则

### 角色文件
- `agents/Synapse Scholar.md`: 示例角色提示词（生物医学研究科学家）

## 🎯 使用示例

### 命令行工具
```powershell
# 单次查询（自动保存 Markdown）
python query.py -question:"mRNA疫苗的作用机制是什么？"

# 多轮对话
python query.py -conversation

# 指定语言和详细模式
python query.py -question:"疫苗机制" -language:zh -verbose

# 使用 CLI 工具
pubmed-agent query "What are the mechanisms of COVID-19 vaccines?"
```

### 多模型配置示例

**OpenAI**:
```env
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o
LLM_BASE_URL=
```

**Azure OpenAI**:
```env
LLM_API_KEY=your-azure-key
LLM_BASE_URL=https://your-resource.openai.azure.com/
LLM_MODEL=gpt-4
```

**本地模型 (LM Studio)**:
```env
LLM_BASE_URL=http://localhost:1234/v1
LLM_MODEL=llama-2-7b-chat
LLM_API_KEY=lm-studio
```

**Embedding 独立配置**:
```env
# LLM 使用 OpenAI
LLM_API_KEY=sk-...
LLM_BASE_URL=

# Embedding 使用本地模型
EMBEDDING_BASE_URL=http://localhost:1234/v1
EMBEDDING_API_KEY=lm-studio
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

### 角色提示词使用

**自动加载（推荐）**:
```env
# 如果 agents/Synapse Scholar.md 存在，会自动加载
# 无需配置
```

**通过环境变量指定**:
```env
AGENT_ROLE_NAME=Synapse Scholar
# 或
AGENT_ROLE_FILE=agents/Synapse Scholar.md
```

## 🔒 安全改进

- ✅ `.env` 文件已添加到 `.gitignore`
- ✅ 虚拟环境目录已排除
- ✅ 敏感配置文件已排除
- ✅ Cursor IDE 配置已排除
- ✅ 缓存目录已排除

## 📝 注意事项

1. **首次使用**：复制 `.env.example` 为 `.env` 并填入实际配置
2. **模型选择**：根据需求选择合适的模型（性能 vs 成本）
3. **本地模型**：确保本地服务已启动（如 LM Studio）
4. **配置优先级**：Embedding 配置优先于 LLM 配置（如果填写了独立配置）
5. **角色提示词**：将角色文件放在 `agents/` 目录下，系统会自动检测
6. **Markdown 保存**：所有查询结果自动保存，无需手动操作
7. **MCP 后端**：默认使用内部 Python MCP 后端，无需额外配置

## 🐛 已知问题

- 无

## 🔮 后续计划

- [ ] 支持更多本地模型框架
- [ ] 添加批量查询功能
- [ ] 支持配置文件导入导出
- [ ] 添加交互式配置向导
- [ ] 支持更多专业角色（如临床医生、药物研发专家等）
- [ ] Web UI 支持（Streamlit / Gradio）
- [ ] 多源检索（PubMed + arXiv + Semantic Scholar）

---

**版本**: v0.2.0  
**日期**: 2024-11-07  
**状态**: 🟢 生产就绪 (Production Ready)

**主要贡献者**: PubMed Agent Team  
**许可证**: MIT
