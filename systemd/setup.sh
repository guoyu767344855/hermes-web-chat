#!/bin/bash
# =============================================================================
# Hermes Web Chat systemd 安装脚本
# =============================================================================
# 用法：./setup-systemd.sh
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_DIR="$(dirname "$SCRIPT_DIR")"
HERMES_HOME="${HERMES_HOME:-$HOME/.Hermes}"
SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$SERVICE_DIR/hermes-web-chat.service"

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

echo ""
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   systemd 服务配置                     ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""

# 检查 systemd
if ! command -v systemctl &> /dev/null; then
    log_error "未找到 systemctl，本脚本仅支持 Linux systemd 系统"
    exit 1
fi

# 创建服务目录
log_info "创建服务目录..."
mkdir -p "$SERVICE_DIR"

# 生成服务文件
log_info "生成服务文件..."

cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Hermes Web Chat Service
Documentation=https://github.com/guoyu767344855/hermes-web-chat
After=network.target

[Service]
Type=simple
Environment=HERMES_HOME=$HERMES_HOME
Environment=PATH=/usr/local/bin:/usr/bin:/bin
ExecStart=$HERMES_HOME/venvs/hermes-web-chat/bin/python $HERMES_HOME/plugins/hermes-web-chat/hermes_chat.py
Restart=on-failure
RestartSec=5
StandardOutput=append:$HERMES_HOME/web-chat.log
StandardError=append:$HERMES_HOME/web-chat-error.log

# 安全设置
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=default.target
EOF

log_success "服务文件已创建：$SERVICE_FILE"

# 重载 systemd
log_info "重载 systemd 配置..."
systemctl --user daemon-reload

# 启用服务
log_info "启用服务..."
systemctl --user enable hermes-web-chat.service

log_success "服务已启用"

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  管理命令:"
echo ""
echo "    # 启动服务"
echo "    systemctl --user start hermes-web-chat"
echo ""
echo "    # 停止服务"
echo "    systemctl --user stop hermes-web-chat"
echo ""
echo "    # 重启服务"
echo "    systemctl --user restart hermes-web-chat"
echo ""
echo "    # 查看状态"
echo "    systemctl --user status hermes-web-chat"
echo ""
echo "    # 查看日志"
echo "    journalctl --user -u hermes-web-chat -f"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
log_success "systemd 服务配置完成!"
echo ""
