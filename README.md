# 💬 Hermes Web Chat

Hermes Agent 的现代化 Web 聊天界面，支持图片粘贴、多会话管理、主题切换等功能。

![Hermes Web Chat](assets/screenshot.png)

## 🚀 快速开始

### 一键安装（推荐）

**Mac / Linux:**
```bash
curl -fsSL https://raw.githubusercontent.com/guoyu767344855/hermes-web-chat/main/install.sh | bash
```

**Windows PowerShell:**
```powershell
irm https://raw.githubusercontent.com/guoyu767344855/hermes-web-chat/main/install.ps1 | iex
```

### 启动服务

安装完成后，使用以下命令启动：

```bash
hermes-web-chat
```

**访问地址：** http://localhost:8888

---

## ✨ 功能特点

| 功能 | 说明 |
|------|------|
| 💬 **聊天对话** | 流式响应，实时显示 AI 回复 |
| 📎 **图片粘贴** | Ctrl+V / Cmd+V 直接粘贴图片 |
| 📁 **文件上传** | 支持上传任意文件，自动读取文本内容 |
| 🎨 **主题切换** | 4 种主题（深空蓝/纯白/纯黑/护眼绿） |
| 📋 **多会话** | 创建/切换会话，独立保存聊天记录 |
| 🧠 **记忆管理** | 查看和管理 Hermes 长期记忆 |
| 📚 **技能列表** | 查看所有已安装的技能 |
| ⏰ **定时任务** | 管理 Cron 任务 |
| 🔘 **选择按钮** | AI 回复中的选项自动显示为可点击按钮 |
| 🔄 **自动更新** | 一键检查和安装最新版本 |

---

## 📖 使用方法

### 选择按钮功能

当 AI 回复包含带编号的选项时，会自动显示为可点击的按钮：

**支持的格式：**
- `1. 选项内容` - 数字编号
- `A) 选项内容` - 字母编号  
- `[1] 选项内容` - 方括号编号

**示例：**
```
请问你想选择哪个？
1. 苹果
2. 香蕉
3. 橙子
```

AI 回复下方会显示蓝色选择按钮，点击后自动发送选项内容。

### 启动/停止

```bash
# 启动
hermes-web-chat

# 自定义端口
hermes-web-chat --port 9000

# 停止
pkill -f hermes_chat.py

# 查看状态
lsof -i :8888
```

### 使用管理脚本

```bash
cd ~/.Hermes/plugins/hermes-web-chat

# 启动
./scripts/start.sh

# 停止
./scripts/stop.sh

# 查看状态
./scripts/status.sh

# 查看日志
./scripts/logs.sh
```

### Hermes 插件命令

```bash
# 启动
hermes web-chat start

# 停止
hermes web-chat stop

# 查看状态
hermes web-chat status

# 查看日志
hermes web-chat logs
```

---

## 🔧 配置

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `HERMES_HOME` | `~/.Hermes` | Hermes 配置目录 |
| `PORT` | `8888` | 服务端口 |

### 开机自启

**macOS:**
```bash
cd ~/.Hermes/plugins/hermes-web-chat/launchd
./setup.sh
```

**Linux:**
```bash
cd ~/.Hermes/plugins/hermes-web-chat/systemd
./setup.sh
```

---

## 🛠️ 开发

### 本地开发

```bash
# 克隆仓库
git clone https://github.com/guoyu767344855/hermes-web-chat.git
cd hermes-web-chat

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Mac/Linux
# 或
.\venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 运行
python hermes_chat.py
```

### 项目结构

```
hermes-web-chat/
├── hermes_chat.py         # 主程序
├── plugin.yaml            # Hermes 插件配置
├── requirements.txt       # Python 依赖
├── install.sh             # Mac/Linux 安装脚本
├── install.ps1            # Windows 安装脚本
├── README.md              # 说明文档
├── scripts/               # 管理脚本
│   ├── start.sh
│   ├── stop.sh
│   ├── status.sh
│   └── logs.sh
├── systemd/               # Linux systemd 配置
│   ├── hermes-web-chat.service
│   └── setup.sh
├── launchd/               # macOS launchd 配置
│   ├── com.hermes.webchat.plist
│   └── setup.sh
└── assets/                # 资源文件
    └── screenshot.png
```

---

## 🐛 故障排查

### 端口已被占用

```bash
# 查找占用端口的进程
lsof -i :8888

# 杀死进程
kill -9 <PID>

# 或使用其他端口
hermes-web-chat --port 9000
```

### 找不到 hermes 命令

```bash
# 安装 Hermes Agent
pip install hermes-agent

# 或添加到 PATH
export PATH="$HOME/.local/bin:$PATH"
```

### 虚拟环境不存在

```bash
# 重新运行安装脚本
./install.sh
```

### 查看日志

```bash
# 查看最近 50 行
tail -50 ~/.Hermes/web-chat.log

# 实时跟踪
tail -f ~/.Hermes/web-chat.log
```

---

## 📝 更新日志

### v2.2.0 (2026-04-28)

**✨ 新增功能**
- 新增选择按钮功能
- AI 回复中的选项自动显示为可点击按钮
- 支持多种编号格式（`1.` `A)` `[1]`）
- 点击按钮自动发送选项内容
- 按钮点击后自动禁用防止重复点击

**🔧 技术改进**
- 使用 data 属性存储选项内容，避免转义问题
- 三层检测策略识别选项格式
- 自动去重避免重复匹配

### v2.1.0 (2026-04-28)

**✨ 新增功能**
- 新增插件自动更新功能
- 设置页面新增"插件更新"模块
- 支持一键检查最新版本
- 支持一键拉取并安装更新
- 自动安装 Python 依赖
- 显示当前版本和最新版本信息

### v2.0.0 (2026-04-28)

**🎉 重大更新**
- 新增一键安装脚本（Mac/Linux/Windows）
- 新增虚拟环境管理
- 新增全局启动命令 `hermes-web-chat`
- 新增开机自启支持（systemd/launchd）
- 新增管理脚本（start/stop/status/logs）
- 增强 plugin.yaml 配置

### v1.10.0 (2026-04-21)
- 添加主题切换系统
- 支持 4 种主题

### v1.9.0 (2026-04-16)
- 添加流式响应支持
- 实时显示 AI 回复

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 👤 作者

- 郭昱 <guoyu@qtshe.com>
- GitHub: [@guoyu767344855](https://github.com/guoyu767344855)

## 🔗 相关链接

- [Hermes Agent](https://github.com/nousresearch/hermes-agent)
- [FastAPI](https://fastapi.tiangolo.com/)
