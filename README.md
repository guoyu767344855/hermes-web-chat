# 💬 Hermes Web Chat

Hermes Agent 的现代化 Web 聊天界面插件，支持图片粘贴和上传。

![Hermes Web Chat](assets/screenshot.png)

## ✨ 功能特点

### 💬 聊天对话
- 📋 **左侧导航菜单** - 仿 hermes-hudui 风格的垂直菜单
- 📎 **剪贴板粘贴** - 直接在输入框按 `Ctrl+V` / `Cmd+V` 粘贴图片
- 🖼️ **图片上传** - 点击按钮上传图片，支持预览和删除
- 📁 **文件上传** - 支持上传任意类型文件（PDF、Word、Excel 等）
- 📌 **固定底部** - 输入框始终固定在聊天页面底部
- 🎨 **现代化 UI** - 深色渐变主题，流畅动画效果
- 💬 **聊天对话** - 类似现代聊天软件的交互体验
- 🖥️ **跨平台支持** - Windows / Mac / Linux 全平台兼容

### 📊 数据管理
- 🧠 **记忆管理** - 查看和管理 Hermes 长期记忆和每日记忆
- 📚 **技能列表** - 查看所有已安装的技能
- 📋 **会话历史** - 浏览历史对话记录
- ⏰ **定时任务** - 管理 Cron 任务
- 📊 **项目跟踪** - 查看项目状态
- 💰 **费用统计** - Token 使用统计和费用估算
- 📈 **使用模式** - 24 小时和每日使用分析

## 🚀 快速开始

### 方法一：通过 Hermes 插件系统安装

```bash
hermes plugins install guoyu767344855/hermes-web-chat
```

### 方法二：手动安装

**Mac/Linux:**
```bash
# 克隆仓库
git clone https://github.com/guoyu767344855/hermes-web-chat.git ~/.hermes/plugins/hermes-web-chat

# 安装依赖
pip install fastapi uvicorn python-multipart

# 启动
python3 ~/.hermes/plugins/hermes-web-chat/hermes_chat.py
```

**Windows:**
```powershell
# 克隆仓库
git clone https://github.com/guoyu767344855/hermes-web-chat.git $HOME\.hermes\plugins\hermes-web-chat

# 安装依赖
pip install fastapi uvicorn python-multipart

# 启动
python $HOME\.hermes\plugins\hermes-web-chat\hermes_chat.py
```

### 方法三：使用安装脚本

**Mac/Linux:**
```bash
cd hermes-web-chat
./install.sh
```

**Windows:**
```powershell
cd hermes-web-chat
.\install.bat
```

## 📖 使用说明

### 启动插件

**Mac/Linux:**
```bash
# 默认端口 8888
python3 ~/.hermes/plugins/hermes-web-chat/hermes_chat.py

# 自定义端口
python3 ~/.hermes/plugins/hermes-web-chat/hermes_chat.py 9000
```

**Windows:**
```powershell
# 默认端口 8888
python $HOME\.hermes\plugins\hermes-web-chat\hermes_chat.py

# 自定义端口
python $HOME\.hermes\plugins\hermes-web-chat\hermes_chat.py 9000
```

### 访问界面

在浏览器中打开：**http://localhost:8888**

### 功能操作

| 操作 | 说明 |
|------|------|
| `Enter` | 发送消息 |
| `Shift+Enter` | 换行 |
| `Ctrl+V` / `Cmd+V` | 粘贴图片 |
| 📎 按钮 | 点击上传图片 |
| 📤 按钮 | 发送消息 |

## 📋 菜单功能

左侧菜单包含以下功能入口（当前为展示，后续可扩展）：

- 💬 聊天对话 - 主聊天界面
- 🧠 记忆管理 - 查看和管理 Hermes 记忆
- 📚 技能列表 - 查看已安装技能
- 📋 会话历史 - 查看历史对话
- ⏰ 定时任务 - 管理 Cron 任务
- 📊 项目跟踪 - 项目状态
- 💰 费用统计 - Token 使用统计
- 📈 使用模式 - 使用分析

## 🔧 配置

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `HERMES_HOME` | `~/.Hermes` | Hermes 配置目录 |
| `PORT` | `8888` | 服务端口 |

### 依赖要求

- Python 3.9+
- FastAPI
- Uvicorn
- Python-multipart
- Hermes Agent

## 📁 项目结构

```
hermes-web-chat/
├── hermes_chat.py      # 主程序
├── plugin.yaml         # 插件配置
├── install.sh          # 安装脚本
├── README.md           # 说明文档
├── .gitignore          # Git 忽略文件
└── assets/             # 资源文件
    └── screenshot.png  # 截图
```

## 🛠️ 开发

### 本地开发

```bash
# 安装依赖
pip install fastapi uvicorn python-multipart

# 运行
python3 hermes_chat.py

# 开发模式（自动重载）
uvicorn hermes_chat:app --reload --port 8888
```

### 修改端口

编辑 `hermes_chat.py` 底部的端口配置，或通过命令行参数指定：

```bash
python3 hermes_chat.py 9000
```

## 📝 更新日志

### v1.9.0 (2026-04-16)

**✨ 新功能**
- 添加流式响应支持，实时显示 Hermes 思考过程
- 像终端聊天一样实时看到 AI 回复
- 不再需要等待完整回复

**🔧 技术实现**
- 新增 `/api/chat_stream` 流式聊天接口
- 后端使用 Generator 逐行输出
- 前端使用 XHR 接收 Server-Sent Events
- 自动滚动到最新消息

### v1.8.0 (2026-04-16)

**🐛 Bug 修复**
- 修复上传的文件内容无法被识别的问题
- 修复 `hermes` 命令路径问题（使用完整路径）

**✨ 新功能**
- 文本文件：读取内容并附加到消息中（限制 10000 字符）
- 二进制文件：提示文件类型并保存路径

**🔧 技术改进**
- `call_hermes()` 使用完整路径 `/Users/guomin/.local/bin/hermes`
- 自动检测文件类型（UTF-8 文本或二进制）
- 添加详细的调试日志

### v1.7.0 (2026-04-16)

**🐛 Bug 修复**
- 修复粘贴图片（base64 dataURL）无法上传的问题
- `fetch()` 无法直接处理 `data:` 开头的 base64 URL

**✨ 新功能**
- 添加 `dataURLtoBlob()` 函数
- 支持 base64 dataURL 和 HTTP URL 两种格式

**🔧 技术实现**
- 检测 dataURL 是否以 `'data:'` 开头
- base64 格式：使用 `atob()` 解码，创建 `Uint8Array`
- HTTP URL：使用 `fetch()` 获取 blob

### v1.6.0 (2026-04-16)

**🐛 Bug 修复**
- 修复图片上传后未被识别的问题
- 修复 `sendMessage` 函数中 `currentImage` 被提前清除的问题

**🔧 技术改进**
- 保存 `imageToSend` 变量避免闭包问题
- 添加图片加载错误处理
- 添加后端图片接收调试日志

### v1.5.0 (2026-04-16)

**🎨 UI 优化**
- 将时间筛选器移到刷新按钮后面，水平排列
- `.page-header h2` 使用 flex 布局，`gap: 12px`
- `.filter-bar` 改为 `inline-flex`，移除 `margin-left`
- `.refresh-btn` 添加 `font-size: 13px` 统一大小

### v1.4.0 (2026-04-16)

**🐛 Bug 修复**
- 修复会话框出现左右滚动条问题
- 修复技能列表显示为空问题

**🎨 CSS 优化**
- `.chat-messages` 添加 `overflow-x: hidden`
- `.message-avatar` 添加 `flex-shrink: 0` 防止压缩
- `.message-content` 和 `.message-text` 添加 `overflow-wrap: break-word`
- `.message-image` 改为 `max-width: 100%`, `max-height: 400px`
- 所有文本内容支持自动换行，适应不同屏幕宽度

### v1.3.0 (2026-04-16)

**🐛 Bug 修复**
- 修复点击会话历史中的会话后无法显示消息记录的问题

**✨ 新功能**
- 添加 `/api/session_detail` API 端点
- 从服务器加载历史会话的完整消息
- 加载后自动缓存到 localStorage

**🔧 技术实现**
- `get_session_detail()` 函数读取会话 JSON 文件
- `loadSessionDetail()` 优先从 localStorage 加载，不存在则从服务器加载
- `renderChatHistory()` 统一渲染消息历史

### v1.2.0 (2026-04-16)

**✨ 新功能**
- 会话历史页面添加日期筛选（全部时间/最近 7 天/30 天/90 天）
- 记忆管理页面添加日期筛选（全部时间/最近 7 天/30 天/90 天）
- 筛选器位于页面标题栏右侧，与刷新按钮并排

**🔧 技术实现**
- 存储原始数据用于前端筛选
- 按日期字段过滤会话和记忆数据
- 空数据状态友好提示

### v1.1.0 (2026-04-16)

**🐛 Bug 修复**
- 修复左侧选项卡点击无反应问题（JavaScript 语法错误 - 引号转义问题）
- 修复技能列表显示为空问题（表格解析逻辑优化）

**✨ 功能优化**
- 新增/清空按钮移至聊天页面标题栏右上角，布局更合理
- 技能列表按分类分组显示，支持本地技能标识
- 优化页面加载和交互体验

**🔧 技术改进**
- 使用 data-属性 + 动态事件绑定替代内联 onclick
- 优化表格数据解析逻辑，正确解析 4 列格式（Name|Category|Source|Trust）

### v1.0.0 (2026-04-15)

- ✨ 初始版本发布
- 💬 完整的聊天对话功能
- 📎 剪贴板图片粘贴支持
- 🎨 现代化 UI 设计
- 📋 左侧导航菜单

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 👤 作者

- 郭昱 <guoyu@qtshe.com>
- GitHub: [@guoyu](https://github.com/guoyu)

## 🔗 相关链接

- [Hermes Agent](https://github.com/nousresearch/hermes-agent)
- [Hermes HUD UI](https://github.com/joeynyc/hermes-hudui)
- [FastAPI](https://fastapi.tiangolo.com/)
