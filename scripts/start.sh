#!/bin/bash
# =============================================================================
# Hermes Web Chat 启动脚本
# =============================================================================
# 用法：./start.sh [端口]
# 示例：./start.sh 9000
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_DIR="$(dirname "$SCRIPT_DIR")"
HERMES_HOME="${HERMES_HOME:-$HOME/.Hermes}"
VENV_DIR="$HERMES_HOME/venvs/hermes-web-chat"
PYTHON="$VENV_DIR/bin/python"
MAIN_SCRIPT="$PLUGIN_DIR/hermes_chat.py"
PORT="${1:-8888}"
LOG_FILE="$HERMES_HOME/web-chat.log"
PID_FILE="$HERMES_HOME/web-chat.pid"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[!]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }

# 检查虚拟环境
if [ ! -f "$PYTHON" ]; then
    log_error "虚拟环境不存在：$VENV_DIR"
    log_info "请运行安装脚本：./install.sh"
    exit 1
fi

# 检查主程序
if [ ! -f "$MAIN_SCRIPT" ]; then
    log_error "主程序不存在：$MAIN_SCRIPT"
    exit 1
fi

# 检查是否已运行
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        log_warn "服务已在运行 (PID: $OLD_PID)"
        log_info "访问地址：http://localhost:$PORT"
        exit 0
    else
        rm -f "$PID_FILE"
    fi
fi

# 创建日志目录
mkdir -p "$(dirname "$LOG_FILE")"

# 启动服务
log_info "启动 Hermes Web Chat..."
log_info "端口：$PORT"
log_info "日志：$LOG_FILE"

nohup "$PYTHON" "$MAIN_SCRIPT" --port "$PORT" > "$LOG_FILE" 2>&1 &
PID=$!
echo $PID > "$PID_FILE"

sleep 2

# 检查是否启动成功
if ps -p "$PID" > /dev/null 2>&1; then
    log_success "服务已启动 (PID: $PID)"
    log_success "访问地址：http://localhost:$PORT"
    echo ""
    echo "停止服务：./stop.sh"
    echo "查看日志：tail -f $LOG_FILE"
else
    log_error "服务启动失败，请查看日志：$LOG_FILE"
    rm -f "$PID_FILE"
    exit 1
fi
