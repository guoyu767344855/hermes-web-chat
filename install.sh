#!/bin/bash

# Hermes Web Chat 安装脚本
# 用法：./install.sh

set -e

echo ""
echo "╔════════════════════════════════════════╗"
echo "║   💬 Hermes Web Chat 安装程序          ║"
echo "╚════════════════════════════════════════╝"
echo ""

# 检测操作系统
OS="$(uname -s)"
case "$OS" in
    Darwin)
        echo "✓ 检测到 macOS 系统"
        PYTHON_CMD="python3"
        ;;
    Linux)
        echo "✓ 检测到 Linux 系统"
        PYTHON_CMD="python3"
        ;;
    *)
        echo "⚠ 未知操作系统，尝试使用 python3"
        PYTHON_CMD="python3"
        ;;
esac

# 检查 Python
echo ""
echo "→ 检查 Python 环境..."
if ! command -v $PYTHON_CMD &> /dev/null; then
    echo "✗ 错误：未找到 Python3，请先安装 Python3"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
echo "✓ Python 版本：$PYTHON_VERSION"

# 检查 pip
echo ""
echo "→ 检查 pip..."
if ! $PYTHON_CMD -m pip --version &> /dev/null; then
    echo "✗ 错误：未找到 pip，请先安装 pip"
    exit 1
fi
echo "✓ pip 已安装"

# 安装依赖
echo ""
echo "→ 安装 Python 依赖..."
$PYTHON_CMD -m pip install fastapi uvicorn python-multipart -q
echo "✓ 依赖安装完成"

# 创建必要目录
echo ""
echo "→ 创建数据目录..."
mkdir -p ~/.Hermes/web-chat/uploads
echo "✓ 目录创建完成"

# 设置执行权限
echo ""
echo "→ 设置执行权限..."
chmod +x hermes_chat.py 2>/dev/null || true
echo "✓ 权限设置完成"

# 完成
echo ""
echo "╔════════════════════════════════════════╗"
echo "║           ✅ 安装完成！                ║"
echo "╚════════════════════════════════════════╝"
echo ""
echo "启动命令："
echo "  python3 hermes_chat.py"
echo ""
echo "访问地址："
echo "  http://localhost:8888"
echo ""
echo "自定义端口："
echo "  python3 hermes_chat.py 9000"
echo ""
