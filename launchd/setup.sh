#!/bin/bash
# =============================================================================
# Hermes Web Chat launchd 安装脚本 (macOS)
# =============================================================================
# 用法：./setup-launchd.sh
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_DIR="$(dirname "$SCRIPT_DIR")"
HERMES_HOME="${HERMES_HOME:-$HOME/.Hermes}"
PLIST_DIR="$HOME/Library/LaunchAgents"
PLIST_FILE="$PLIST_DIR/com.hermes.webchat.plist"
PLIST_TEMPLATE="$SCRIPT_DIR/com.hermes.webchat.plist"

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
echo -e "${GREEN}║   launchd 服务配置 (macOS)             ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""

# 检查 macOS
if [[ "$(uname)" != "Darwin" ]]; then
    log_error "本脚本仅支持 macOS"
    exit 1
fi

# 创建目录
log_info "创建目录..."
mkdir -p "$PLIST_DIR"

# 生成 plist 文件
log_info "生成配置文件..."

if [ -f "$PLIST_TEMPLATE" ]; then
    # 替换模板变量
    sed "s|{HERMES_HOME}|$HERMES_HOME|g" "$PLIST_TEMPLATE" > "$PLIST_FILE"
else
    # 直接创建
    cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.hermes.webchat</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>$HERMES_HOME/venvs/hermes-web-chat/bin/python</string>
        <string>$HERMES_HOME/plugins/hermes-web-chat/hermes_chat.py</string>
    </array>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
        <key>Crashed</key>
        <true/>
    </dict>
    
    <key>StandardOutPath</key>
    <string>$HERMES_HOME/web-chat.log</string>
    
    <key>StandardErrorPath</key>
    <string>$HERMES_HOME/web-chat-error.log</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>HERMES_HOME</key>
        <string>$HERMES_HOME</string>
    </dict>
    
    <key>WorkingDirectory</key>
    <string>$HERMES_HOME/plugins/hermes-web-chat</string>
    
    <key>ProcessType</key>
    <string>Background</string>
</dict>
</plist>
EOF
fi

log_success "配置文件已创建：$PLIST_FILE"

# 卸载旧服务（如果存在）
log_info "卸载旧服务..."
launchctl unload "$PLIST_FILE" 2>/dev/null || true

# 加载新服务
log_info "加载服务..."
launchctl load "$PLIST_FILE"

log_success "launchd 服务已配置"

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  管理命令:"
echo ""
echo "    # 启动服务"
echo "    launchctl load $PLIST_FILE"
echo ""
echo "    # 停止服务"
echo "    launchctl unload $PLIST_FILE"
echo ""
echo "    # 查看状态"
echo "    launchctl list | grep hermes"
echo ""
echo "    # 查看日志"
echo "    tail -f $HERMES_HOME/web-chat.log"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
log_success "launchd 服务配置完成!"
echo ""
