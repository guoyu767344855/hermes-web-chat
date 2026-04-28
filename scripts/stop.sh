#!/bin/bash
# =============================================================================
# Hermes Web Chat 停止脚本
# =============================================================================
# 用法：./stop.sh
# =============================================================================

set -e

HERMES_HOME="${HERMES_HOME:-$HOME/.Hermes}"
PID_FILE="$HERMES_HOME/web-chat.pid"
LOG_FILE="$HERMES_HOME/web-chat.log"

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

# 检查 PID 文件
if [ ! -f "$PID_FILE" ]; then
    log_warn "PID 文件不存在，尝试查找进程..."
    
    # 尝试通过进程名查找
    PID=$(pgrep -f "hermes_chat.py" | head -1)
    
    if [ -z "$PID" ]; then
        log_warn "未找到运行中的 Hermes Web Chat 进程"
        exit 0
    fi
    
    log_info "找到进程 (PID: $PID)"
else
    PID=$(cat "$PID_FILE")
fi

# 检查进程是否存在
if ! ps -p "$PID" > /dev/null 2>&1; then
    log_warn "进程 (PID: $PID) 不存在"
    rm -f "$PID_FILE"
    exit 0
fi

# 停止进程
log_info "停止服务 (PID: $PID)..."
kill "$PID" 2>/dev/null || true

# 等待进程结束
for i in {1..10}; do
    if ! ps -p "$PID" > /dev/null 2>&1; then
        break
    fi
    sleep 0.5
done

# 如果还在运行，强制终止
if ps -p "$PID" > /dev/null 2>&1; then
    log_warn "进程未响应，强制终止..."
    kill -9 "$PID" 2>/dev/null || true
fi

# 清理
rm -f "$PID_FILE"

log_success "服务已停止"
