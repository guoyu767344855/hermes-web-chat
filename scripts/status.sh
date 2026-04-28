#!/bin/bash
# =============================================================================
# Hermes Web Chat 状态查看脚本
# =============================================================================
# 用法：./status.sh
# =============================================================================

HERMES_HOME="${HERMES_HOME:-$HOME/.Hermes}"
PID_FILE="$HERMES_HOME/web-chat.pid"
LOG_FILE="$HERMES_HOME/web-chat.log"
PORT="${1:-8888}"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Hermes Web Chat 服务状态             ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# 检查进程
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    
    if ps -p "$PID" > /dev/null 2>&1; then
        echo -e "  运行状态：${GREEN}● 运行中${NC}"
        echo -e "  进程 ID:   $PID"
        
        # 获取端口
        ACTUAL_PORT=$(lsof -i -P -n | grep "$PID" | grep LISTEN | awk '{print $9}' | cut -d':' -f2 | head -1)
        if [ -n "$ACTUAL_PORT" ]; then
            echo -e "  端口：     $ACTUAL_PORT"
        else
            echo -e "  端口：     $PORT"
        fi
        
        echo -e "  访问地址：${GREEN}http://localhost:${ACTUAL_PORT:-$PORT}${NC}"
        echo ""
        echo -e "  日志文件：$LOG_FILE"
        
        # 显示最近日志
        if [ -f "$LOG_FILE" ]; then
            echo ""
            echo -e "  ${BLUE}最近日志:${NC}"
            tail -5 "$LOG_FILE" | sed 's/^/    /'
        fi
    else
        echo -e "  运行状态：${RED}● 已停止${NC} (PID 文件存在但进程不存在)"
        echo -e "  建议：运行 ${GREEN}./start.sh${NC} 启动服务"
        rm -f "$PID_FILE"
    fi
else
    # 尝试通过进程名查找
    PID=$(pgrep -f "hermes_chat.py" | head -1)
    
    if [ -n "$PID" ]; then
        echo -e "  运行状态：${GREEN}● 运行中${NC}"
        echo -e "  进程 ID:   $PID"
        echo -e "  访问地址：${GREEN}http://localhost:$PORT${NC}"
        echo ""
        echo -e "  ${YELLOW}[提示]${NC} PID 文件不存在，可能是通过其他方式启动的"
    else
        echo -e "  运行状态：${YELLOW}● 未运行${NC}"
        echo ""
        echo -e "  启动命令：${GREEN}./start.sh${NC}"
    fi
fi

echo ""

# 检查安装
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

VENV_DIR="$HERMES_HOME/venvs/hermes-web-chat"
PLUGIN_DIR="$HERMES_HOME/plugins/hermes-web-chat"

if [ -d "$VENV_DIR" ]; then
    echo -e "  虚拟环境：${GREEN}✓ 已安装${NC}"
else
    echo -e "  虚拟环境：${RED}✗ 未安装${NC}"
fi

if [ -d "$PLUGIN_DIR" ]; then
    echo -e "  插件目录：${GREEN}✓ 已安装${NC}"
else
    echo -e "  插件目录：${RED}✗ 未安装${NC}"
fi

if command -v hermes-web-chat &> /dev/null; then
    echo -e "  全局命令：${GREEN}✓ 可用${NC}"
else
    echo -e "  全局命令：${YELLOW}! 不可用${NC} (请确保 ~/.Hermes/bin 在 PATH 中)"
fi

echo ""
