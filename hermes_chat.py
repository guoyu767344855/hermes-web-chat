"""
Hermes Agent Web Chat - FastAPI 版本
支持剪贴板图片粘贴，现代化 UI 设计
"""

from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from pathlib import Path
import subprocess
import tempfile
import os
from typing import Optional
import uvicorn
import sys

app = FastAPI()

# 获取插件目录
PLUGIN_DIR = Path(__file__).parent
HERMES_HOME = Path.home() / ".Hermes"
UPLOAD_DIR = HERMES_HOME / "web-chat" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# 存储对话历史
chat_history = []

def call_hermes(message: str, image_path: Optional[str] = None) -> str:
    """调用 Hermes 获取回复"""
    try:
        cmd = ["hermes", "chat", "-q", message, "-Q", "--source", "web"]
        
        if image_path:
            cmd.extend(["--image", image_path])
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            env={**os.environ, "HERMES_HOME": str(HERMES_HOME)}
        )
        
        response = result.stdout.strip()
        if not response:
            response = result.stderr.strip() or "没有收到回复"
        
        return response
    
    except subprocess.TimeoutExpired:
        return "⏱️ 请求超时"
    except Exception as e:
        return f"❌ 错误：{str(e)}"

def get_html_content() -> str:
    """获取 HTML 页面内容"""
    return """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hermes Agent Chat</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
            min-height: 100vh;
            display: flex;
        }
        .sidebar {
            width: 260px;
            background: linear-gradient(180deg, #0a0a1a 0%, #1a1a2e 100%);
            border-right: 1px solid #1f3a5f;
            padding: 20px 0;
            flex-shrink: 0;
        }
        .logo {
            text-align: center;
            padding: 20px;
            border-bottom: 1px solid #1f3a5f;
            margin-bottom: 20px;
        }
        .logo h1 {
            font-size: 24px;
            background: linear-gradient(135deg, #00d9ff 0%, #00ff88 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .logo p { color: #666; font-size: 12px; margin-top: 5px; }
        .menu { list-style: none; padding: 0 10px; }
        .menu-item {
            padding: 12px 16px;
            margin: 4px 0;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s ease;
            color: #888;
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 14px;
        }
        .menu-item:hover { background: rgba(0, 217, 255, 0.1); color: #00d9ff; }
        .menu-item.active {
            background: linear-gradient(135deg, #00d9ff 0%, #0099ff 100%);
            color: white;
            box-shadow: 0 4px 15px rgba(0, 217, 255, 0.3);
        }
        .menu-icon { font-size: 18px; }
        .main { flex: 1; display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
        .chat-header {
            padding: 20px 30px;
            border-bottom: 1px solid #1f3a5f;
            background: rgba(15, 15, 26, 0.8);
        }
        .chat-header h2 { color: #e8e8e8; font-size: 18px; font-weight: 500; }
        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 30px;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        .message {
            display: flex;
            gap: 15px;
            max-width: 80%;
            animation: fadeIn 0.3s ease;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .message.user { align-self: flex-end; flex-direction: row-reverse; }
        .message-avatar {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            flex-shrink: 0;
        }
        .message.assistant .message-avatar {
            background: linear-gradient(135deg, #00d9ff 0%, #0099ff 100%);
        }
        .message.user .message-avatar {
            background: linear-gradient(135deg, #ff6b6b 0%, #ff8e53 100%);
        }
        .message-content {
            background: #1a1a2e;
            padding: 15px 20px;
            border-radius: 16px;
            border: 1px solid #2a2a4e;
        }
        .message.user .message-content {
            background: linear-gradient(135deg, #1f3a5f 0%, #2a4a6f 100%);
            border-color: #3a5a8f;
        }
        .message-text {
            color: #e8e8e8;
            line-height: 1.6;
            font-size: 15px;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        .message-image { max-width: 300px; border-radius: 10px; margin-top: 10px; border: 2px solid #2a2a4e; }
        .input-container {
            padding: 20px 30px;
            background: rgba(15, 15, 26, 0.95);
            border-top: 1px solid #1f3a5f;
        }
        .input-wrapper {
            display: flex;
            gap: 15px;
            align-items: flex-end;
            background: #1a1a2e;
            border: 2px solid #2a2a4e;
            border-radius: 24px;
            padding: 8px 8px 8px 20px;
            transition: all 0.3s ease;
        }
        .input-wrapper:focus-within {
            border-color: #00d9ff;
            box-shadow: 0 0 20px rgba(0, 217, 255, 0.2);
        }
        #messageInput {
            flex: 1;
            background: transparent;
            border: none;
            outline: none;
            color: #e8e8e8;
            font-size: 15px;
            padding: 10px 0;
            resize: none;
            max-height: 150px;
            font-family: inherit;
        }
        #messageInput::placeholder { color: #666; }
        .input-actions { display: flex; gap: 8px; padding-right: 8px; }
        .action-btn {
            width: 44px;
            height: 44px;
            border-radius: 50%;
            border: none;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            transition: all 0.2s ease;
        }
        .upload-btn { background: #2a2a4e; color: #888; }
        .upload-btn:hover { background: #3a3a5e; color: #00d9ff; }
        .send-btn { background: linear-gradient(135deg, #00d9ff 0%, #0099ff 100%); color: white; }
        .send-btn:hover {
            transform: scale(1.05);
            box-shadow: 0 4px 15px rgba(0, 217, 255, 0.4);
        }
        .send-btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        .preview-container {
            display: none;
            padding: 10px 30px;
            background: rgba(15, 15, 26, 0.95);
            border-top: 1px solid #1f3a5f;
        }
        .preview-container.show { display: block; }
        .preview-wrapper { display: inline-block; position: relative; }
        .preview-image { max-height: 150px; border-radius: 10px; border: 2px solid #00d9ff; }
        .preview-remove {
            position: absolute;
            top: -8px;
            right: -8px;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            background: #ff4757;
            color: white;
            border: none;
            cursor: pointer;
            font-size: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .typing-indicator { display: flex; gap: 5px; padding: 15px 20px; }
        .typing-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #00d9ff;
            animation: typing 1.4s infinite;
        }
        .typing-dot:nth-child(2) { animation-delay: 0.2s; }
        .typing-dot:nth-child(3) { animation-delay: 0.4s; }
        @keyframes typing {
            0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
            30% { transform: translateY(-10px); opacity: 1; }
        }
        #fileInput { display: none; }
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: #1a1a2e; }
        ::-webkit-scrollbar-thumb { background: #2a2a4e; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #3a3a5e; }
    </style>
</head>
<body>
    <div class="sidebar">
        <div class="logo">
            <h1>🤖 Hermes Agent</h1>
            <p>AI 智能助手</p>
        </div>
        <ul class="menu">
            <li class="menu-item active"><span class="menu-icon">💬</span>聊天对话</li>
            <li class="menu-item"><span class="menu-icon">🧠</span>记忆管理</li>
            <li class="menu-item"><span class="menu-icon">📚</span>技能列表</li>
            <li class="menu-item"><span class="menu-icon">📋</span>会话历史</li>
            <li class="menu-item"><span class="menu-icon">⏰</span>定时任务</li>
            <li class="menu-item"><span class="menu-icon">📊</span>项目跟踪</li>
            <li class="menu-item"><span class="menu-icon">💰</span>费用统计</li>
            <li class="menu-item"><span class="menu-icon">📈</span>使用模式</li>
        </ul>
    </div>
    <div class="main">
        <div class="chat-header"><h2>💬 聊天对话</h2></div>
        <div class="chat-messages" id="chatMessages">
            <div class="message assistant">
                <div class="message-avatar">🤖</div>
                <div class="message-content">
                    <div class="message-text">👋 你好！我是 Hermes Agent，有什么可以帮你的吗？
                    支持文字和图片提问，直接在输入框按 Ctrl+V / Cmd+V 粘贴图片即可。</div>
                </div>
            </div>
        </div>
        <div class="preview-container" id="previewContainer">
            <div class="preview-wrapper">
                <img class="preview-image" id="previewImage" src="" alt="预览">
                <button class="preview-remove" onclick="removeImage()">✕</button>
            </div>
        </div>
        <div class="input-container">
            <div class="input-wrapper">
                <textarea id="messageInput" placeholder="输入消息... (支持直接粘贴图片 Ctrl+V/Cmd+V)" rows="1" onkeydown="handleKeyDown(event)"></textarea>
                <input type="file" id="fileInput" accept="image/*" onchange="handleFileSelect(event)">
                <div class="input-actions">
                    <button class="action-btn upload-btn" onclick="document.getElementById('fileInput').click()" title="上传图片">📎</button>
                    <button class="action-btn send-btn" id="sendBtn" onclick="sendMessage()" title="发送">📤</button>
                </div>
            </div>
        </div>
    </div>
    <script>
        let currentImage = null;
        const chatMessages = document.getElementById('chatMessages');
        const messageInput = document.getElementById('messageInput');
        const previewContainer = document.getElementById('previewContainer');
        const previewImage = document.getElementById('previewImage');
        const sendBtn = document.getElementById('sendBtn');
        messageInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 150) + 'px';
        });
        messageInput.addEventListener('paste', async function(e) {
            const items = e.clipboardData.items;
            for (let item of items) {
                if (item.type.indexOf('image') !== -1) {
                    e.preventDefault();
                    const blob = item.getAsFile();
                    const reader = new FileReader();
                    reader.onload = function(event) {
                        currentImage = event.target.result;
                        showPreview(currentImage);
                    };
                    reader.readAsDataURL(blob);
                    break;
                }
            }
        });
        function showPreview(imageData) {
            previewImage.src = imageData;
            previewContainer.classList.add('show');
        }
        function removeImage() {
            currentImage = null;
            previewContainer.classList.remove('show');
            document.getElementById('fileInput').value = '';
        }
        function handleFileSelect(e) {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(event) {
                    currentImage = event.target.result;
                    showPreview(currentImage);
                };
                reader.readAsDataURL(file);
            }
        }
        function handleKeyDown(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        }
        function addMessage(content, isUser, imageData = null) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${isUser ? 'user' : 'assistant'}`;
            let imageHtml = '';
            if (imageData) {
                imageHtml = `<img class="message-image" src="${imageData}" alt="图片">`;
            }
            messageDiv.innerHTML = `
                <div class="message-avatar">${isUser ? '👤' : '🤖'}</div>
                <div class="message-content">
                    <div class="message-text">${content}</div>
                    ${imageHtml}
                </div>
            `;
            chatMessages.appendChild(messageDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
        function showLoading() {
            const loadingDiv = document.createElement('div');
            loadingDiv.className = 'message assistant';
            loadingDiv.id = 'loadingMessage';
            loadingDiv.innerHTML = `
                <div class="message-avatar">🤖</div>
                <div class="message-content">
                    <div class="typing-indicator">
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                    </div>
                </div>
            `;
            chatMessages.appendChild(loadingDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
        function removeLoading() {
            const loading = document.getElementById('loadingMessage');
            if (loading) loading.remove();
        }
        async function sendMessage() {
            const message = messageInput.value.trim();
            if (!message && !currentImage) return;
            sendBtn.disabled = true;
            addMessage(message || '[图片]', true, currentImage);
            messageInput.value = '';
            messageInput.style.height = 'auto';
            const imageData = currentImage;
            removeImage();
            showLoading();
            try {
                const formData = new FormData();
                formData.append('message', message || '请分析这张图片');
                if (imageData) {
                    const response = await fetch(imageData);
                    const blob = await response.blob();
                    formData.append('image', blob, 'image.png');
                }
                const res = await fetch('/api/chat', { method: 'POST', body: formData });
                const data = await res.json();
                removeLoading();
                addMessage(data.response, false);
            } catch (error) {
                removeLoading();
                addMessage('❌ 发送失败：' + error.message, false);
            }
            sendBtn.disabled = false;
            messageInput.focus();
        }
        document.querySelectorAll('.menu-item').forEach(item => {
            item.addEventListener('click', function() {
                document.querySelectorAll('.menu-item').forEach(i => i.classList.remove('active'));
                this.classList.add('active');
            });
        });
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def get_chat_page():
    return HTMLResponse(content=get_html_content())

@app.post("/api/chat")
async def chat(message: str = Form(...), image: UploadFile = File(None)):
    """处理聊天请求"""
    image_path = None
    if image:
        temp_path = tempfile.mktemp(suffix=".png", dir=str(UPLOAD_DIR))
        with open(temp_path, "wb") as f:
            content = await image.read()
            f.write(content)
        image_path = temp_path
    response = call_hermes(message, image_path)
    if image_path and os.path.exists(image_path):
        os.remove(image_path)
    return JSONResponse(content={"response": response})

if __name__ == "__main__":
    port = 8888
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except:
            pass
    
    print("\n" + "="*50)
    print("🤖 Hermes Agent Web Chat")
    print("="*50)
    print(f"📍 访问地址：http://localhost:{port}")
    print("📎 支持直接粘贴图片 (Ctrl+V / Cmd+V)")
    print("🇨🇳 中文友好界面")
    print("="*50 + "\n")
    
    uvicorn.run(app, host="127.0.0.1", port=port)
