#!/bin/bash
# CLI使用示例脚本
# CLI Usage Example Script

echo "🧬 ReAct PubMed Agent - CLI使用示例"
echo "===================================="
echo ""

# 检查是否已安装
if ! command -v pubmed-agent &> /dev/null; then
    echo "⚠️  CLI命令未找到，请先安装包："
    echo "   uv pip install -e ."
    echo "   或"
    echo "   pip install -e ."
    echo ""
    echo "也可以使用Python模块方式："
    echo "   python -m pubmed_agent query \"...\""
    exit 1
fi

echo "✅ CLI命令可用"
echo ""

# 示例1: 基本查询
echo "📋 示例1: 基本查询"
echo "-------------------"
echo "命令: pubmed-agent query \"mRNA疫苗的作用机制是什么？\""
echo ""

# 示例2: 交互式模式
echo "📋 示例2: 交互式模式"
echo "-------------------"
echo "命令: pubmed-agent interactive"
echo "提示: 在交互式模式中，输入问题后按回车，输入 'quit' 退出"
echo ""

# 示例3: 搜索文献
echo "📋 示例3: 搜索文献"
echo "-------------------"
echo "命令: pubmed-agent search \"COVID-19 vaccine\" --max-results 5"
echo ""

# 示例4: 查看统计信息
echo "📋 示例4: 查看统计信息"
echo "-------------------"
echo "命令: pubmed-agent stats"
echo ""

# 示例5: 使用自定义API
echo "📋 示例5: 使用自定义API endpoint"
echo "-------------------"
echo "命令: pubmed-agent query \"Hello\" --api-base http://localhost:8000/v1"
echo ""

echo "===================================="
echo "📚 更多信息请查看 CLI_USAGE.md"
echo "===================================="

