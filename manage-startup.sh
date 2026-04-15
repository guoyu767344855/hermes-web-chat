#!/bin/bash
# Hermes Web Chat 自启动管理脚本

PLIST=~/Library/LaunchAgents/com.hermes.webchat.plist

case "$1" in
    start)
        echo "→ 启动 Hermes Web Chat 自启动..."
        if [ -f "$PLIST" ]; then
            launchctl load "$PLIST" 2>/dev/null
            echo "✅ 已启动"
        else
            echo "❌ plist 文件不存在"
        fi
        ;;
    stop)
        echo "→ 停止 Hermes Web Chat 自启动..."
        launchctl unload "$PLIST" 2>/dev/null
        echo "✅ 已停止"
        ;;
    restart)
        $0 stop
        sleep 1
        $0 start
        ;;
    status)
        echo "→ 检查状态..."
        launchctl list | grep -i hermes || echo "未运行"
        ;;
    install)
        echo "→ 安装自启动..."
        if [ -f "$PLIST" ]; then
            echo "✅ 已安装"
        else
            echo "❌ plist 文件不存在"
        fi
        ;;
    uninstall)
        echo "→ 卸载自启动..."
        launchctl unload "$PLIST" 2>/dev/null
        rm -f "$PLIST"
        echo "✅ 已卸载"
        ;;
    *)
        echo "用法：$0 {start|stop|restart|status|install|uninstall}"
        echo ""
        echo "命令说明："
        echo "  start     - 启动自启动服务"
        echo "  stop      - 停止自启动服务"
        echo "  restart   - 重启自启动服务"
        echo "  status    - 查看服务状态"
        echo "  install   - 安装自启动"
        echo "  uninstall - 卸载自启动"
        exit 1
        ;;
esac
