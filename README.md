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

```bash
# 克隆仓库
git clone https://github.com/guoyu767344855/hermes-web-chat.git ~/.hermes/plugins/hermes-web-chat

# 安装依赖
pip install fastapi uvicorn python-multipart

# 启动
python3 ~/.hermes/plugins/hermes-web-chat/hermes_chat.py
```

### 方法三：使用安装脚本

```bash
cd hermes-web-chat
./install.sh
```

## 📖 使用说明

### 启动插件

```bash
# 默认端口 8888
python3 ~/.hermes/plugins/hermes-web-chat/hermes_chat.py

# 自定义端口
python3 ~/.hermes/plugins/hermes-web-chat/hermes_chat.py 9000
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
