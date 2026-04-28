#!/bin/bash
# =============================================================================
# Hermes Web Chat 日志查看脚本
# =============================================================================
# 用法：./logs.sh [行数]
# 示例：./logs.sh 50     # 查看最近 50 行
#       ./logs.sh -f     # 实时跟踪日志
# =============================================================================

HERMES_HOME="${HERMES_HOME:-$HOME/.Hermes}"
LOG_FILE="$HERMES_HOME/web-chat.log"

# 颜色定义
YELLOW='\033[1;33m'
NC='\033[0m'

if [ ! -f "$LOG_FILE" ]; then
    echo -e "${YELLOW}[警告]${NC} 日志文件不存在：$LOG_FILE"
    echo "请先启动服务：./start.sh"
    exit 1
fi

# 参数处理
if [ "$1" == "-f" ] || [ "$1" == "--follow" ]; then
    echo -e "实时跟踪日志 (Ctrl+C 退出)..."
    echo ""
    tail -f "$LOG_FILE"
else
    LINES="${1:-50}"
    echo "最近 $LINES 行日志:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    tail -n "$LINES" "$LOG_FILE"
fi
