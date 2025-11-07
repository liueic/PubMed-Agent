# 🚀 版本特性说明 - dev_hhx 分支

## 📋 版本概述

本次更新主要实现了 Windows 本地部署优化、多模型供应商支持、命令行工具增强以及配置系统完善。

## ✨ 主要特性

### 1. 🖥️ Windows 本地部署支持
- ✅ 完整的 Windows PowerShell 命令示例
- ✅ 优化的路径处理和目录创建
- ✅ 详细的 Windows 部署指南
- ✅ 支持 Windows 路径格式的配置项

### 2. 🔧 多模型供应商支持
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

### 3. 📝 环境配置文件完善
- ✅ 创建完整的 `.env.example` 文件
- ✅ 支持多种模型选择（gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo 等）
- ✅ 详细的中英文配置说明
- ✅ 推理参数优化（TEMPERATURE=0.7, TOP_P=0.95）

### 4. 💻 命令行工具增强
- ✅ 新增 `query.py` 命令行查询工具
- ✅ 支持 `-question:"问题"` 格式参数
- ✅ 支持多轮对话模式（`-conversation`）
- ✅ 支持语言选择（`-language:en|zh|auto`）
- ✅ 支持详细模式（`-verbose` 显示推理过程）
- ✅ 友好的错误提示和环境检查

### 5. 📚 文档更新
- ✅ README 添加 Windows 快速开始指南
- ✅ 添加多模型供应商配置说明
- ✅ 添加常见问题（FAQ）
- ✅ 更新使用示例和最佳实践

### 6. 🛠️ 代码质量提升
- ✅ 创建 `embedding_utils.py` 工具函数
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

### 向后兼容

- ✅ 仍支持 `OPENAI_API_KEY` 和 `OPENAI_MODEL`
- ✅ 现有配置无需修改即可使用

## 📦 新增文件

- `query.py`: 命令行查询工具
- `pubmed_agent/embedding_utils.py`: Embedding 模型初始化工具
- `.env.example`: 完整的环境配置示例
- `.gitignore`: Git 忽略规则
- `.cursor/rules/`: Cursor IDE 规则文件

## 🎯 使用示例

### 命令行工具
```powershell
# 单次查询
python query.py -question:"mRNA疫苗的作用机制是什么？"

# 多轮对话
python query.py -conversation

# 指定语言和详细模式
python query.py -question:"疫苗机制" -language:zh -verbose
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

## 🔒 安全改进

- ✅ `.env` 文件已添加到 `.gitignore`
- ✅ 虚拟环境目录已排除
- ✅ 敏感配置文件已排除
- ✅ Cursor IDE 配置已排除

## 📝 注意事项

1. **首次使用**：复制 `.env.example` 为 `.env` 并填入实际配置
2. **模型选择**：根据需求选择合适的模型（性能 vs 成本）
3. **本地模型**：确保本地服务已启动（如 LM Studio）
4. **配置优先级**：Embedding 配置优先于 LLM 配置（如果填写了独立配置）

## 🐛 已知问题

- 无

## 🔮 后续计划

- [ ] 支持更多本地模型框架
- [ ] 添加批量查询功能
- [ ] 支持配置文件导入导出
- [ ] 添加交互式配置向导

---

**版本**: dev_hhx  
**日期**: 2024-11-07  
**状态**: 🟢 测试版本

