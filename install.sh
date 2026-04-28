#!/bin/bash

# =============================================================================
# Hermes Web Chat 一键安装脚本
# =============================================================================
# 支持：Mac / Linux
# 用法：curl -fsSL https://raw.githubusercontent.com/guoyu767344855/hermes-web-chat/main/install.sh | bash
# 或：./install.sh
# =============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[!]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }

# 打印横幅
print_banner() {
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║${NC}        💬 Hermes Web Chat 安装程序            ${GREEN}║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# 检测操作系统
detect_os() {
    OS="$(uname -s)"
    case "$OS" in
        Darwin)
            OS_NAME="macos"
            log_info "检测到 macOS 系统"
            ;;
        Linux)
            OS_NAME="linux"
            log_info "检测到 Linux 系统"
            # 检测发行版
            if [ -f /etc/os-release ]; then
                . /etc/os-release
                log_info "发行版：$NAME $VERSION_ID"
            fi
            ;;
        *)
            log_error "不支持的操作系统：$OS"
            exit 1
            ;;
    esac
}

# 检查 Python
check_python() {
    log_info "检查 Python 环境..."
    
    # 查找 python3
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        log_error "未找到 Python，请先安装 Python 3.9+"
        echo ""
        echo "安装指南:"
        echo "  macOS:  brew install python@3.11"
        echo "  Ubuntu: sudo apt install python3 python3-pip python3-venv"
        echo "  CentOS: sudo yum install python3 python3-pip"
        exit 1
    fi
    
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
    log_success "Python 版本：$PYTHON_VERSION"
    
    # 检查版本 >= 3.9
    VERSION_MAJOR=$($PYTHON_CMD -c "import sys; print(sys.version_info.major)")
    VERSION_MINOR=$($PYTHON_CMD -c "import sys; print(sys.version_info.minor)")
    
    if [ "$VERSION_MAJOR" -lt 3 ] || ([ "$VERSION_MAJOR" -eq 3 ] && [ "$VERSION_MINOR" -lt 9 ]); then
        log_error "Python 版本过低，需要 3.9+ (当前：$PYTHON_VERSION)"
        exit 1
    fi
}

# 检查 pip
check_pip() {
    log_info "检查 pip..."
    if ! $PYTHON_CMD -m pip --version &> /dev/null; then
        log_error "未找到 pip，请先安装 pip"
        exit 1
    fi
    log_success "pip 已安装"
}

# 检查 hermes 命令
check_hermes() {
    log_info "检查 Hermes Agent..."
    if command -v hermes &> /dev/null; then
        HERMES_VERSION=$(hermes --version 2>&1 | head -1)
        log_success "Hermes Agent: $HERMES_VERSION"
    else
        log_warn "未找到 hermes 命令，请确认已安装 Hermes Agent"
        log_info "安装 Hermes Agent: pip install hermes-agent"
    fi
}

# 设置目录
setup_directories() {
    log_info "创建目录结构..."
    
    # HERMES_HOME 目录
    if [ -z "$HERMES_HOME" ]; then
        HERMES_HOME="$HOME/.Hermes"
    fi
    
    # 创建必要目录
    mkdir -p "$HERMES_HOME/plugins/hermes-web-chat"
    mkdir -p "$HERMES_HOME/venvs/hermes-web-chat"
    mkdir -p "$HERMES_HOME/bin"
    mkdir -p "$HERMES_HOME/web-chat/uploads"
    
    log_success "目录创建完成"
}

# 创建虚拟环境
setup_venv() {
    log_info "创建 Python 虚拟环境..."
    
    VENV_DIR="$HERMES_HOME/venvs/hermes-web-chat"
    
    # 如果虚拟环境已存在，先删除
    if [ -d "$VENV_DIR" ]; then
        log_info "删除旧的虚拟环境..."
        rm -rf "$VENV_DIR"
    fi
    
    # 创建新的虚拟环境
    $PYTHON_CMD -m venv "$VENV_DIR"
    
    # 激活虚拟环境
    source "$VENV_DIR/bin/activate"
    
    log_success "虚拟环境创建完成：$VENV_DIR"
}

# 安装依赖
install_dependencies() {
    log_info "安装 Python 依赖..."
    
    # 升级 pip
    pip install --upgrade pip -q
    
    # 安装 requirements.txt
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
        pip install -r "$SCRIPT_DIR/requirements.txt" -q
    else
        # 在线安装
        pip install fastapi uvicorn python-multipart httpx -q
    fi
    
    log_success "依赖安装完成"
}

# 安装/更新代码
install_code() {
    log_info "安装代码..."
    
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    TARGET_DIR="$HERMES_HOME/plugins/hermes-web-chat"
    
    # 如果是从 git 克隆的目录运行，复制文件
    if [ -f "$SCRIPT_DIR/hermes_chat.py" ] && [ "$SCRIPT_DIR" != "$TARGET_DIR" ]; then
        # 复制文件
        cp -r "$SCRIPT_DIR"/* "$TARGET_DIR/"
        log_success "代码已复制到：$TARGET_DIR"
    else
        # 检查是否是 git 仓库
        if [ -d "$TARGET_DIR/.git" ]; then
            log_info "更新现有安装..."
            cd "$TARGET_DIR"
            git pull origin main 2>/dev/null || log_warn "git pull 失败，继续使用现有代码"
        else
            # 克隆仓库
            log_info "克隆仓库..."
            git clone https://github.com/guoyu767344855/hermes-web-chat.git "$TARGET_DIR" 2>/dev/null || \
                log_warn "克隆失败，使用当前目录"
        fi
    fi
}

# 创建全局启动命令
create_launcher() {
    log_info "创建全局启动命令..."
    
    LAUNCHER="$HERMES_HOME/bin/hermes-web-chat"
    VENV_PYTHON="$HERMES_HOME/venvs/hermes-web-chat/bin/python"
    SCRIPT="$HERMES_HOME/plugins/hermes-web-chat/hermes_chat.py"
    
    cat > "$LAUNCHER" << 'EOF'
#!/bin/bash
# Hermes Web Chat 启动脚本

HERMES_HOME="${HERMES_HOME:-$HOME/.Hermes}"
VENV_PYTHON="$HERMES_HOME/venvs/hermes-web-chat/bin/python"
SCRIPT="$HERMES_HOME/plugins/hermes-web-chat/hermes_chat.py"

# 检查虚拟环境
if [ ! -f "$VENV_PYTHON" ]; then
    echo "错误：虚拟环境不存在，请重新运行安装脚本"
    exit 1
fi

# 检查主程序
if [ ! -f "$SCRIPT" ]; then
    echo "错误：主程序不存在，请重新运行安装脚本"
    exit 1
fi

# 启动服务
exec "$VENV_PYTHON" "$SCRIPT" "$@"
EOF
    
    chmod +x "$LAUNCHER"
    
    log_success "启动命令已创建：$LAUNCHER"
    
    # 添加到 PATH
    if ! echo "$PATH" | grep -q "$HERMES_HOME/bin"; then
        log_info "将 $HERMES_HOME/bin 添加到 PATH..."
        
        # 检测 shell
        SHELL_NAME=$(basename "$SHELL")
        case "$SHELL_NAME" in
            bash)
                PROFILE="$HOME/.bashrc"
                [ -f "$HOME/.bash_profile" ] && PROFILE="$HOME/.bash_profile"
                ;;
            zsh)
                PROFILE="$HOME/.zshrc"
                ;;
            fish)
                PROFILE="$HOME/.config/fish/config.fish"
                ;;
            *)
                PROFILE="$HOME/.profile"
                ;;
        esac
        
        if [ -f "$PROFILE" ]; then
            if ! grep -q "HERMES_HOME/bin" "$PROFILE"; then
                echo "" >> "$PROFILE"
                echo "# Hermes Web Chat" >> "$PROFILE"
                echo "export PATH=\"$HERMES_HOME/bin:\$PATH\"" >> "$PROFILE"
                log_info "已添加到 $PROFILE，请运行 'source $PROFILE' 或重新打开终端"
            fi
        fi
    fi
}

# 配置开机自启（可选）
setup_autostart() {
    echo ""
    log_info "是否配置开机自启动？(y/N)"
    read -r response
    
    case "$response" in
        [yY][eE][sS]|[yY])
            case "$OS_NAME" in
                macos)
                    setup_launchd
                    ;;
                linux)
                    setup_systemd
                    ;;
            esac
            ;;
        *)
            log_info "跳过开机自启配置"
            ;;
    esac
}

# macOS launchd 配置
setup_launchd() {
    log_info "配置 macOS launchd 自启动..."
    
    PLIST_DIR="$HOME/Library/LaunchAgents"
    PLIST_FILE="$PLIST_DIR/com.hermes.webchat.plist"
    
    mkdir -p "$PLIST_DIR"
    
    cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.hermes.webchat</string>
    <key>ProgramArguments</key>
    <array>
        <string>$HERMES_HOME/bin/hermes-web-chat</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$HERMES_HOME/web-chat.log</string>
    <key>StandardErrorPath</key>
    <string>$HERMES_HOME/web-chat-error.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
EOF
    
    # 加载服务
    launchctl unload "$PLIST_FILE" 2>/dev/null || true
    launchctl load "$PLIST_FILE"
    
    log_success "launchd 服务已配置"
}

# Linux systemd 配置
setup_systemd() {
    log_info "配置 Linux systemd 自启动..."
    
    SERVICE_FILE="$HOME/.config/systemd/user/hermes-web-chat.service"
    mkdir -p "$(dirname "$SERVICE_FILE")"
    
    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Hermes Web Chat
After=network.target

[Service]
Type=simple
ExecStart=$HERMES_HOME/bin/hermes-web-chat
Restart=on-failure
Environment=PATH=/usr/local/bin:/usr/bin:/bin
Environment=HERMES_HOME=$HERMES_HOME

[Install]
WantedBy=default.target
EOF
    
    # 启用服务
    systemctl --user daemon-reload
    systemctl --user enable hermes-web-chat.service
    systemctl --user start hermes-web-chat.service
    
    log_success "systemd 服务已配置"
}

# 启动服务
start_service() {
    echo ""
    log_info "是否立即启动 Hermes Web Chat？(Y/n)"
    read -r response
    
    case "$response" in
        [nN][oO]|[nN])
            log_info "跳过启动"
            ;;
        *)
            log_info "启动服务..."
            "$HERMES_HOME/bin/hermes-web-chat" &
            sleep 2
            ;;
    esac
}

# 打印完成信息
print_completion() {
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║${NC}           ✅ 安装完成！                       ${GREEN}║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "  📍 安装位置：$HERMES_HOME/plugins/hermes-web-chat"
    echo "  🐍 虚拟环境：$HERMES_HOME/venvs/hermes-web-chat"
    echo "  🚀 启动命令：hermes-web-chat"
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "  使用方法:"
    echo ""
    echo "    # 启动服务"
    echo "    hermes-web-chat"
    echo ""
    echo "    # 自定义端口"
    echo "    hermes-web-chat --port 9000"
    echo ""
    echo "    # 后台运行"
    echo "    hermes-web-chat &"
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "  访问地址：http://localhost:8888"
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    # 检查 PATH
    if ! command -v hermes-web-chat &> /dev/null; then
        echo -e "${YELLOW}[提示]${NC} 运行以下命令使 hermes-web-chat 立即可用:"
        echo ""
        echo "  export PATH=\"$HERMES_HOME/bin:\$PATH\""
        echo ""
    fi
}

# 主函数
main() {
    print_banner
    detect_os
    check_python
    check_pip
    check_hermes
    setup_directories
    setup_venv
    install_dependencies
    install_code
    create_launcher
    setup_autostart
    print_completion
}

# 运行
main "$@"
