# 💬 Hermes Web Chat

Hermes Agent 的现代化 Web 聊天界面，支持 Markdown 渲染、数学公式、文件上传、多会话管理、主题切换等功能。

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

### 💬 聊天对话
| 功能 | 说明 |
|------|------|
| 🌊 **流式响应** | 实时显示 AI 回复进度，逐行更新 |
| 📎 **图片粘贴** | Ctrl+V / Cmd+V 直接粘贴图片 |
| 📁 **文件上传** | 支持上传任意文件，自动读取文本内容 |
| ⏸️ **停止生成** | 点击暂停按钮即可中断 AI 回复 |
| ✏️ **右键编辑** | 右键点击消息可重新编辑 |
| ⌨️ **快捷键** | Ctrl+K 新建会话、Ctrl+/ 聚焦输入、Esc 停止 |

### 📝 Markdown 渲染
| 功能 | 说明 |
|------|------|
| 📊 **标题层级** | H1/H2/H3 清晰层级，H1 带分隔线 |
| **粗体/斜体** | 正常黑色粗体 + 彩色斜体 |
| 💻 **代码块** | 语法高亮（20+ 语言）+ 一键复制按钮 |
| `` `行内代码` `` | 带背景和边框的行内代码 |
| 📋 **有序/无序列表** | 正常颜色序号，嵌套列表支持 |
| ☑️ **任务列表** | `- [x]` / `- [ ]` 渲染为可交互复选框 |
| 💬 **引用块** | 左侧竖线 + 背景色 + 斜体文字 |
| 📏 **分隔线** | `---` 渲染为水平分隔线 |
| 📊 **表格** | 带边框的 Markdown 表格 |
| 🔢 **数学公式** | KaTeX 渲染，支持 `$行内$` 和 `$$块级$$` |

### 🎨 主题与界面
| 功能 | 说明 |
|------|------|
| 🌗 **4 种主题** | 浅色/深空蓝/纯黑/护眼绿 |
| 🖥️ **系统主题检测** | 自动匹配系统深色/浅色偏好 |
| 💾 **偏好保存** | 主题选择自动保存，下次访问自动应用 |

### 📋 数据面板
| 功能 | 说明 |
|------|------|
| 📋 **会话历史** | 分页浏览所有会话，按时间筛选 |
| 🧠 **记忆管理** | 查看和管理 Hermes 长期记忆 |
| 📚 **技能列表** | 按分类分组显示所有技能 |
| ⏰ **定时任务** | 管理 Cron 任务 |
| 📊 **项目跟踪** | 从记忆中提取项目信息 |
| 💰 **费用统计** | Token 用量、模型分布、预估费用 |
| 📈 **使用模式** | 按小时/日期统计使用频率 |
| 🔄 **插件更新** | 一键检查并安装最新版本 |

### ⚙️ 架构优化
| 功能 | 说明 |
|------|------|
| 🔄 **异步非阻塞** | asyncio.to_thread 避免阻塞 FastAPI 事件循环 |
| 📦 **IndexedDB** | 聊天历史存储在 IndexedDB，突破 localStorage 5MB 限制 |
| 🔒 **文件大小限制** | 上传文件限制 10MB，防止磁盘占满 |
| 📝 **结构化日志** | logging 模块替代 print，支持日志级别 |
| ⚙️ **配置文件** | `hermes_chat_config.json` 支持自定义端口、文件大小等 |
| 🏥 **健康检查** | `/api/health` 端点返回服务状态 |
| 🛡️ **CDN 回退** | marked.js/KaTeX 加载失败时启用内置解析器 |
| ✅ **自动化测试** | 54 个后端测试 + 60+ 前端测试 |

---

## 📖 使用方法

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

### 配置文件

复制示例配置并修改：

```bash
cp hermes_chat_config.json.example hermes_chat_config.json
```

支持的配置项：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `port` | `8888` | 服务端口 |
| `max_file_size` | `10485760` | 最大上传文件大小（字节） |
| `allowed_origins` | `["*"]` | CORS 允许的源 |

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `HERMES_HOME` | `~/.Hermes` | Hermes 配置目录 |

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

### 运行测试

```bash
# 后端测试
cd ~/.hermes/plugins/hermes-web-chat
python3 -m pytest test_hermes_chat.py -v

# 前端测试
open test_app.html  # 在浏览器中打开
```

### 项目结构

```
hermes-web-chat/
├── hermes_chat.py              # 主程序 (FastAPI)
├── hermes_chat_config.json     # 配置文件（可选）
├── plugin.yaml                 # Hermes 插件配置
├── requirements.txt            # Python 依赖
├── install.sh                  # Mac/Linux 安装脚本
├── install.ps1                 # Windows 安装脚本
├── README.md                   # 说明文档
├── test_hermes_chat.py         # 后端自动化测试
├── test_app.html               # 前端自动化测试
├── scripts/                    # 管理脚本
│   ├── start.sh
│   ├── stop.sh
│   ├── status.sh
│   └── logs.sh
├── static/
│   └── app.js                  # 前端 JavaScript
├── systemd/                    # Linux systemd 配置
│   ├── hermes-web-chat.service
│   └── setup.sh
├── launchd/                    # macOS launchd 配置
│   ├── com.hermes.webchat.plist
│   └── setup.sh
└── assets/                     # 资源文件
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

### v3.0.0 (2026-04-29)

**🎉 重大更新 - 格式渲染全面升级**

**📝 Markdown 渲染**
- 新增 KaTeX 数学公式渲染（支持 `$行内$` 和 `$$块级$$`）
- 新增代码块一键复制按钮（20+ 语言语法高亮）
- 新增任务列表渲染（`- [x]` / `- [ ]` 显示为复选框）
- 新增行内代码背景和边框
- 优化标题层级（H1/H2 分隔线，H3 彩色）
- 优化粗体颜色为正常黑色（非主题色）
- 优化有序列表序号颜色为正常颜色
- 优化引用块、分隔线、列表间距

**⚙️ 架构优化**
- 流式渲染修复：实时显示纯文本 + 完成后统一渲染 Markdown
- 任务列表后处理：避免 marked 扩展导致的渲染冲突
- IndexedDB 存储：突破 localStorage 5MB 限制
- 异步非阻塞：asyncio.to_thread 避免阻塞事件循环
- 结构化日志：logging 模块替代 print
- 文件大小限制：10MB 上传限制
- 健康检查端点：/api/health
- 配置文件支持：hermes_chat_config.json

**🧪 测试**
- 新增 54 个后端自动化测试
- 新增 60+ 前端自动化测试
- CDN 回退机制测试

**🎨 界面优化**
- 系统主题自动检测
- 键盘快捷键支持
- 会话历史分页
- Cron 数据表格化显示
- 更好的会话标题

### v2.3.0 (2026-04-28)

**🐛 Bug 修复**
- 修复回复内容包含思考过程文字的问题
- 移除选择按钮功能（用户反馈不需要）
- 改进流式响应过滤逻辑

### v2.2.0 (2026-04-28)

**✨ 新增功能**
- 新增插件自动更新功能
- 设置页面新增"插件更新"模块

### v2.0.0 (2026-04-28)

**🎉 重大更新**
- 新增一键安装脚本（Mac/Linux/Windows）
- 新增虚拟环境管理
- 新增全局启动命令 `hermes-web-chat`
- 新增开机自启支持（systemd/launchd）

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
- [KaTeX](https://katex.org/)
- [marked.js](https://marked.js.org/)
