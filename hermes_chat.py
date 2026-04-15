"""
Hermes Agent Web Chat - FastAPI 版本
支持剪贴板图片粘贴，现代化 UI 设计，完整功能菜单
"""

from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from pathlib import Path
import subprocess
import tempfile
import os
import json
import glob
from typing import Optional
import uvicorn
import sys
import re
from datetime import datetime

app = FastAPI()

# 获取插件目录
PLUGIN_DIR = Path(__file__).parent
HERMES_HOME = Path.home() / ".Hermes"
UPLOAD_DIR = HERMES_HOME / "web-chat" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ============ 数据获取函数 ============

def get_memory_data():
    """获取记忆数据"""
    memory_file = HERMES_HOME / "MEMORY.md"
    if not memory_file.exists():
        return {"daily": [], "long_term": []}
    
    content = memory_file.read_text()
    daily = []
    long_term = []
    
    lines = content.split('\n')
    current_item = []
    
    for line in lines:
        if line.startswith('> 2026-') or line.startswith('> 2025-'):
            if current_item:
                daily.append('\n'.join(current_item))
            current_item = [line]
        elif line.strip() and current_item:
            current_item.append(line)
        elif line.startswith('§'):
            if current_item:
                daily.append('\n'.join(current_item))
                current_item = []
    
    if current_item:
        daily.append('\n'.join(current_item))
    
    return {
        "daily": daily[-20:],
        "long_term": long_term[:20],
        "file_path": str(memory_file)
    }

def get_skills_data():
    """获取技能列表"""
    try:
        result = subprocess.run(
            ["hermes", "skills", "list"],
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "HERMES_HOME": str(HERMES_HOME)}
        )
        
        skills = []
        for line in result.stdout.strip().split('\n'):
            if line.strip() and '│' in line:
                parts = [p.strip() for p in line.split('│') if p.strip()]
                if len(parts) >= 2:
                    skills.append({
                        "name": parts[0],
                        "category": parts[1] if len(parts) > 1 else "unknown",
                        "description": parts[2] if len(parts) > 2 else ""
                    })
        
        return {"skills": skills, "count": len(skills)}
    except Exception as e:
        return {"skills": [], "error": str(e)}

def get_sessions_data():
    """获取会话历史"""
    sessions_dir = HERMES_HOME / "sessions"
    if not sessions_dir.exists():
        return {"sessions": []}
    
    sessions = []
    session_files = sorted(glob.glob(str(sessions_dir / "*.json")), reverse=True)[:50]
    
    for file_path in session_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            session_id = Path(file_path).stem
            title = data.get("title", "未命名会话")
            created = data.get("created_at", "")
            message_count = len(data.get("messages", []))
            
            preview = ""
            for msg in data.get("messages", [])[:3]:
                if msg.get("role") == "user":
                    preview = msg.get("content", "")[:100]
                    break
            
            sessions.append({
                "id": session_id,
                "title": title,
                "created": created,
                "messages": message_count,
                "preview": preview + "..." if len(preview) > 100 else preview,
                "file": file_path
            })
        except:
            continue
    
    return {"sessions": sessions, "count": len(sessions)}

def get_cron_data():
    """获取定时任务"""
    try:
        result = subprocess.run(
            ["hermes", "cronjob", "list"],
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "HERMES_HOME": str(HERMES_HOME)}
        )
        
        jobs = []
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                jobs.append(line)
        
        return {"jobs": jobs, "raw": result.stdout}
    except Exception as e:
        return {"jobs": [], "error": str(e)}

def get_projects_data():
    """获取项目数据"""
    memory_file = HERMES_HOME / "MEMORY.md"
    projects = []
    
    if memory_file.exists():
        content = memory_file.read_text()
        for line in content.split('\n'):
            if '🎯 重要项目' in line or '项目:' in line:
                projects.append(line.strip())
    
    if not projects:
        projects = [
            "🎯 Hermes Web Chat - Web 聊天界面开发",
            "📊 小红书数据工具 - 数据获取与分析",
            "🏠 父亲健康照护系统 - 健康管理系统"
        ]
    
    return {"projects": projects, "count": len(projects)}

def get_costs_data():
    """获取费用统计"""
    sessions_dir = HERMES_HOME / "sessions"
    total_tokens = 0
    model_counts = {}
    
    if sessions_dir.exists():
        for file_path in glob.glob(str(sessions_dir / "*.json")):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                model = data.get("model", "unknown")
                model_counts[model] = model_counts.get(model, 0) + 1
                
                messages = data.get("messages", [])
                for msg in messages:
                    total_tokens += len(msg.get("content", "")) // 4
            except:
                continue
    
    return {
        "total_tokens": total_tokens,
        "sessions": sum(model_counts.values()),
        "models": model_counts,
        "estimated_cost": f"${total_tokens / 1000000 * 2:.4f}"
    }

def get_patterns_data():
    """获取使用模式分析"""
    sessions_dir = HERMES_HOME / "sessions"
    hourly_usage = {str(i): 0 for i in range(24)}
    daily_usage = {}
    
    if sessions_dir.exists():
        for file_path in glob.glob(str(sessions_dir / "*.json")):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                created = data.get("created_at", "")
                if created:
                    try:
                        dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                        hour = str(dt.hour)
                        day = dt.strftime('%Y-%m-%d')
                        
                        hourly_usage[hour] = hourly_usage.get(hour, 0) + 1
                        daily_usage[day] = daily_usage.get(day, 0) + 1
                    except:
                        pass
            except:
                continue
    
    return {
        "hourly": hourly_usage,
        "daily": dict(sorted(daily_usage.items(), reverse=True)[:14]),
        "peak_hour": max(hourly_usage.keys(), key=lambda k: hourly_usage[k]) if any(hourly_usage.values()) else "N/A"
    }

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

@app.get("/", response_class=HTMLResponse)
async def get_chat_page():
    return HTMLResponse(content=get_html_content())

@app.post("/api/chat")
async def chat(message: str = Form(...), image: UploadFile = File(None), file: UploadFile = File(None)):
    """处理聊天请求"""
    image_path = None
    file_path = None
    
    if image:
        temp_path = tempfile.mktemp(suffix=".png", dir=str(UPLOAD_DIR))
        with open(temp_path, "wb") as f:
            content = await image.read()
            f.write(content)
        image_path = temp_path
    
    if file:
        temp_path = tempfile.mktemp(suffix=f"_{file.filename}", dir=str(UPLOAD_DIR))
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        file_path = temp_path
    
    full_message = message
    if file and file.filename:
        full_message = f"{message}\n\n[文件：{file.filename}]\n文件已上传，请分析或处理。"
    
    response = call_hermes(full_message, image_path)
    
    if image_path and os.path.exists(image_path):
        os.remove(image_path)
    if file_path and os.path.exists(file_path):
        os.remove(file_path)
    
    return JSONResponse(content={"response": response})

@app.get("/api/memory")
async def api_memory():
    return JSONResponse(content=get_memory_data())

@app.get("/api/skills")
async def api_skills():
    return JSONResponse(content=get_skills_data())

@app.get("/api/sessions")
async def api_sessions():
    return JSONResponse(content=get_sessions_data())

@app.put("/api/sessions/{session_id}")
async def api_update_session(session_id: str, request: Request):
    """更新会话标题"""
    try:
        body = await request.json()
        new_title = body.get("title", "").strip()
        
        if not new_title:
            return JSONResponse(status_code=400, content={"error": "标题不能为空"})
        
        sessions_dir = HERMES_HOME / "sessions"
        session_file = sessions_dir / f"{session_id}.json"
        
        if not session_file.exists():
            return JSONResponse(status_code=404, content={"error": "会话不存在"})
        
        with open(session_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        data["title"] = new_title
        
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return JSONResponse(content={"success": True, "title": new_title})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/cron")
async def api_cron():
    return JSONResponse(content=get_cron_data())

@app.get("/api/projects")
async def api_projects():
    return JSONResponse(content=get_projects_data())

@app.get("/api/costs")
async def api_costs():
    return JSONResponse(content=get_costs_data())

@app.get("/api/patterns")
async def api_patterns():
    return JSONResponse(content=get_patterns_data())

def get_html_content():
    """获取 HTML 页面内容"""
    return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hermes Agent</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
            min-height: 100vh;
            display: flex;
            color: #e8e8e8;
        }
        .sidebar {
            width: 260px;
            background: linear-gradient(180deg, #0a0a1a 0%, #1a1a2e 100%);
            border-right: 1px solid #1f3a5f;
            padding: 20px 0;
            flex-shrink: 0;
            display: flex;
            flex-direction: column;
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
        }
        .logo p { color: #666; font-size: 12px; margin-top: 5px; }
        .menu { list-style: none; padding: 0 10px; flex: 1; }
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
        .main { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
        .page { display: none; height: 100vh; flex-direction: column; }
        .page.active { display: flex; }
        .page-header {
            padding: 20px 30px;
            border-bottom: 1px solid #1f3a5f;
            background: rgba(15, 15, 26, 0.8);
        }
        .page-header h2 {
            font-size: 24px;
            color: #00d9ff;
            display: flex;
            align-items: center;
            gap: 10px;
        }
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
        .message.assistant .message-avatar { background: linear-gradient(135deg, #00d9ff 0%, #0099ff 100%); }
        .message.user .message-avatar { background: linear-gradient(135deg, #ff6b6b 0%, #ff8e53 100%); }
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
        .message-text { color: #e8e8e8; line-height: 1.6; font-size: 15px; white-space: pre-wrap; }
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
        }
        .input-wrapper:focus-within { border-color: #00d9ff; box-shadow: 0 0 20px rgba(0, 217, 255, 0.2); }
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
        .send-btn:hover { transform: scale(1.05); box-shadow: 0 4px 15px rgba(0, 217, 255, 0.4); }
        .send-btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        .preview-container, .file-preview-container {
            display: none;
            padding: 10px 30px;
            background: rgba(15, 15, 26, 0.95);
            border-top: 1px solid #1f3a5f;
        }
        .preview-container.show, .file-preview-container.show { display: block; }
        .preview-wrapper, .file-preview-item { display: inline-block; position: relative; }
        .file-preview-item {
            display: flex;
            align-items: center;
            gap: 15px;
            background: #1a1a2e;
            padding: 12px 20px;
            border-radius: 10px;
            border: 1px solid #2a2a4e;
        }
        .preview-image { max-height: 150px; border-radius: 10px; border: 2px solid #00d9ff; }
        .preview-remove, .file-preview-remove {
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
        }
        .file-preview-remove { position: static; width: 28px; height: 28px; }
        .typing-indicator { display: flex; gap: 5px; padding: 15px 20px; }
        .typing-dot {
            width: 8px; height: 8px;
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
        #fileInput, #imageInput { display: none; }
        .card {
            background: #1a1a2e;
            border: 1px solid #2a2a4e;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .card-title { font-size: 16px; color: #00d9ff; margin-bottom: 15px; }
        .data-list { list-style: none; }
        .data-list li {
            padding: 12px 15px;
            background: rgba(0, 217, 255, 0.05);
            border-radius: 8px;
            margin-bottom: 10px;
            border-left: 3px solid #00d9ff;
        }
        .session-item {
            position: relative;
        }
        .session-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }
        .session-title {
            font-weight: bold;
            color: #e8e8e8;
            font-size: 15px;
        }
        .edit-btn {
            background: linear-gradient(135deg, #00d9ff 0%, #0f3460 100%);
            border: none;
            border-radius: 6px;
            padding: 4px 12px;
            color: white;
            font-size: 13px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .edit-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(0, 217, 255, 0.4);
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: linear-gradient(135deg, #1a1a2e 0%, #1f3a5f 100%);
            border: 1px solid #2a4a6f;
            border-radius: 12px;
            padding: 25px;
            text-align: center;
        }
        .stat-value {
            font-size: 36px;
            font-weight: bold;
            background: linear-gradient(135deg, #00d9ff 0%, #00ff88 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .stat-label { color: #888; font-size: 14px; }
        .loading { text-align: center; padding: 40px; color: #666; }
        .loading-spinner {
            width: 40px; height: 40px;
            border: 3px solid #2a2a4e;
            border-top-color: #00d9ff;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .refresh-btn {
            background: #2a2a4e;
            color: #00d9ff;
            border: none;
            padding: 8px 16px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
        }
        .refresh-btn:hover { background: #3a3a5e; }
        .empty-state { text-align: center; padding: 60px 20px; color: #666; }
        .empty-state-icon { font-size: 48px; margin-bottom: 20px; }
        .tag {
            display: inline-block;
            padding: 4px 12px;
            background: rgba(0, 217, 255, 0.1);
            color: #00d9ff;
            border-radius: 20px;
            font-size: 12px;
        }
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: #1a1a2e; }
        ::-webkit-scrollbar-thumb { background: #2a2a4e; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="sidebar">
        <div class="logo">
            <h1>🤖 Hermes Agent</h1>
            <p>AI 智能助手</p>
        </div>
        <ul class="menu">
            <li class="menu-item active" data-page="chat"><span class="menu-icon">💬</span>聊天对话</li>
        </ul>
        <div style="padding:10px; border-top:1px solid #1f3a5f;">
            <button onclick="clearChatHistory()" style="width:100%; padding:10px; background:#2a2a4e; color:#ff6b6b; border:none; border-radius:8px; cursor:pointer; font-size:14px;">🗑️ 清空对话</button>
        </div>
            <li class="menu-item" data-page="memory"><span class="menu-icon">🧠</span>记忆管理</li>
            <li class="menu-item" data-page="skills"><span class="menu-icon">📚</span>技能列表</li>
            <li class="menu-item" data-page="sessions"><span class="menu-icon">📋</span>会话历史</li>
            <li class="menu-item" data-page="cron"><span class="menu-icon">⏰</span>定时任务</li>
            <li class="menu-item" data-page="projects"><span class="menu-icon">📊</span>项目跟踪</li>
            <li class="menu-item" data-page="costs"><span class="menu-icon">💰</span>费用统计</li>
            <li class="menu-item" data-page="patterns"><span class="menu-icon">📈</span>使用模式</li>
        </ul>
    </div>
    
    <div class="main">
        <div id="page-chat" class="page active">
            <div class="chat-messages" id="chatMessages">
                <div class="message assistant">
                    <div class="message-avatar">🤖</div>
                    <div class="message-content">
                        <div class="message-text">👋 你好！我是 Hermes Agent，有什么可以帮你的吗？支持文字和图片提问。</div>
                    </div>
                </div>
            </div>
            <div class="preview-container" id="previewContainer">
                <div class="preview-wrapper">
                    <img class="preview-image" id="previewImage" src="" alt="预览">
                    <button class="preview-remove" onclick="removeImage()">✕</button>
                </div>
            </div>
            <div class="file-preview-container" id="filePreviewContainer">
                <div class="file-preview-item">
                    <span id="filePreviewIcon" style="font-size:24px;">📄</span>
                    <div>
                        <div id="filePreviewName" style="color:#e8e8e8;font-size:14px;">filename</div>
                        <div id="filePreviewSize" style="color:#666;font-size:12px;">0 KB</div>
                    </div>
                    <button class="file-preview-remove" onclick="removeFile()">✕</button>
                </div>
            </div>
            <div class="input-container">
                <div class="input-wrapper">
                    <textarea id="messageInput" placeholder="输入消息... (支持粘贴图片 Ctrl+V/Cmd+V)" rows="1"></textarea>
                    <input type="file" id="imageInput" accept="image/*">
                    <input type="file" id="fileInput">
                    <div class="input-actions">
                        <button class="action-btn upload-btn" onclick="document.getElementById('imageInput').click()" title="上传图片">🖼️</button>
                        <button class="action-btn upload-btn" onclick="document.getElementById('fileInput').click()" title="上传文件">📎</button>
                        <button class="action-btn send-btn" id="sendBtn" onclick="sendMessage()" title="发送">📤</button>
                    </div>
                </div>
            </div>
        </div>
        
        <div id="page-memory" class="page">
            <div class="page-header"><h2>🧠 记忆管理 <button class="refresh-btn" onclick="loadMemory()">🔄 刷新</button></h2></div>
            <div class="chat-messages" id="memory-content"><div class="loading"><div class="loading-spinner"></div>加载中...</div></div>
        </div>
        
        <div id="page-skills" class="page">
            <div class="page-header"><h2>📚 技能列表 <button class="refresh-btn" onclick="loadSkills()">🔄 刷新</button></h2></div>
            <div class="chat-messages" id="skills-content"><div class="loading"><div class="loading-spinner"></div>加载中...</div></div>
        </div>
        
        <div id="page-sessions" class="page">
            <div class="page-header"><h2>📋 会话历史 <button class="refresh-btn" onclick="loadSessions()">🔄 刷新</button></h2></div>
            <div class="chat-messages" id="sessions-content"><div class="loading"><div class="loading-spinner"></div>加载中...</div></div>
        </div>
        
        <div id="page-cron" class="page">
            <div class="page-header"><h2>⏰ 定时任务 <button class="refresh-btn" onclick="loadCron()">🔄 刷新</button></h2></div>
            <div class="chat-messages" id="cron-content"><div class="loading"><div class="loading-spinner"></div>加载中...</div></div>
        </div>
        
        <div id="page-projects" class="page">
            <div class="page-header"><h2>📊 项目跟踪 <button class="refresh-btn" onclick="loadProjects()">🔄 刷新</button></h2></div>
            <div class="chat-messages" id="projects-content"><div class="loading"><div class="loading-spinner"></div>加载中...</div></div>
        </div>
        
        <div id="page-costs" class="page">
            <div class="page-header"><h2>💰 费用统计 <button class="refresh-btn" onclick="loadCosts()">🔄 刷新</button></h2></div>
            <div class="chat-messages" id="costs-content"><div class="loading"><div class="loading-spinner"></div>加载中...</div></div>
        </div>
        
        <div id="page-patterns" class="page">
            <div class="page-header"><h2>📈 使用模式 <button class="refresh-btn" onclick="loadPatterns()">🔄 刷新</button></h2></div>
            <div class="chat-messages" id="patterns-content"><div class="loading"><div class="loading-spinner"></div>加载中...</div></div>
        </div>
    </div>
    
    <script>
        // 页面切换
        document.querySelectorAll('.menu-item').forEach(function(item) {
            item.addEventListener('click', function() {
                var page = this.getAttribute('data-page');
                document.querySelectorAll('.menu-item').forEach(function(i) { i.classList.remove('active'); });
                this.classList.add('active');
                document.querySelectorAll('.page').forEach(function(p) { p.classList.remove('active'); });
                document.getElementById('page-' + page).classList.add('active');
                if (page === 'memory') loadMemory();
                else if (page === 'skills') loadSkills();
                else if (page === 'sessions') loadSessions();
                else if (page === 'cron') loadCron();
                else if (page === 'projects') loadProjects();
                else if (page === 'costs') loadCosts();
                else if (page === 'patterns') loadPatterns();
            });
        });
        
        // 聊天功能
        var currentImage = null;
        var currentFile = null;
        var chatMessages = document.getElementById('chatMessages');
        var messageInput = document.getElementById('messageInput');
        var previewContainer = document.getElementById('previewContainer');
        var previewImage = document.getElementById('previewImage');
        var filePreviewContainer = document.getElementById('filePreviewContainer');
        var sendBtn = document.getElementById('sendBtn');
        
        // 从 localStorage 加载聊天历史
        var CHAT_STORAGE_KEY = 'hermes_chat_history';
        function loadChatHistory() {
            try {
                var saved = localStorage.getItem(CHAT_STORAGE_KEY);
                if (saved) {
                    var history = JSON.parse(saved);
                    history.forEach(function(msg) {
                        addMessage(msg.content, msg.isUser, msg.imageData, false);
                    });
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                }
            } catch (e) {
                console.error('加载聊天历史失败:', e);
            }
        }
        
        // 保存聊天历史到 localStorage
        function saveChatHistory() {
            try {
                var messages = [];
                chatMessages.querySelectorAll('.message').forEach(function(div) {
                    var isUser = div.classList.contains('user');
                    var content = div.querySelector('.message-text').textContent;
                    var img = div.querySelector('.message-image');
                    var imageData = img ? img.src : null;
                    messages.push({ content: content, isUser: isUser, imageData: imageData });
                });
                // 只保存最近 50 条
                if (messages.length > 50) messages = messages.slice(-50);
                localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(messages));
            } catch (e) {
                console.error('保存聊天历史失败:', e);
            }
        }
        
        // 页面加载时恢复聊天记录
        loadChatHistory();
        
        // 自动调整输入框高度
        messageInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 150) + 'px';
        });
        
        // 粘贴图片
        messageInput.addEventListener('paste', function(e) {
            var items = e.clipboardData.items;
            for (var i = 0; i < items.length; i++) {
                if (items[i].type.indexOf('image') !== -1) {
                    e.preventDefault();
                    var blob = items[i].getAsFile();
                    var reader = new FileReader();
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
            document.getElementById('imageInput').value = '';
        }
        
        function removeFile() {
            currentFile = null;
            filePreviewContainer.classList.remove('show');
            document.getElementById('fileInput').value = '';
        }
        
        function getFileIcon(filename) {
            var ext = filename.split('.').pop().toLowerCase();
            var icons = {
                'pdf': '📕', 'doc': '📘', 'docx': '📘', 'txt': '📄',
                'xls': '📗', 'xlsx': '📗', 'csv': '📗',
                'zip': '📦', 'rar': '📦', '7z': '📦',
                'jpg': '🖼️', 'jpeg': '🖼️', 'png': '🖼️', 'gif': '🖼️',
                'mp3': '🎵', 'mp4': '🎬',
                'py': '🐍', 'js': '📜', 'html': '🌐', 'json': '📋'
            };
            return icons[ext] || '📄';
        }
        
        function formatFileSize(bytes) {
            if (bytes < 1024) return bytes + ' B';
            if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
            return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
        }
        
        function handleImageSelect(e) {
            var file = e.target.files[0];
            if (file) {
                var reader = new FileReader();
                reader.onload = function(event) {
                    currentImage = event.target.result;
                    showPreview(currentImage);
                };
                reader.readAsDataURL(file);
            }
        }
        
        function handleFileSelect(e) {
            var file = e.target.files[0];
            if (file) {
                currentFile = file;
                document.getElementById('filePreviewIcon').textContent = getFileIcon(file.name);
                document.getElementById('filePreviewName').textContent = file.name;
                document.getElementById('filePreviewSize').textContent = formatFileSize(file.size);
                filePreviewContainer.classList.add('show');
            }
        }
        
        function handleKeyDown(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        }
        
        messageInput.addEventListener('keydown', handleKeyDown);
        
        function addMessage(content, isUser, imageData, saveToStorage) {
            if (saveToStorage === undefined) saveToStorage = true;
            var messageDiv = document.createElement('div');
            messageDiv.className = 'message ' + (isUser ? 'user' : 'assistant');
            var mediaHtml = '';
            if (imageData) {
                mediaHtml = '<img class="message-image" src="' + imageData + '" alt="图片">';
            }
            messageDiv.innerHTML = '<div class="message-avatar">' + (isUser ? '👤' : '🤖') + '</div>' +
                '<div class="message-content"><div class="message-text">' + content + '</div>' + mediaHtml + '</div>';
            chatMessages.appendChild(messageDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
            if (saveToStorage) saveChatHistory();
        }
        
        function showLoading() {
            var loadingDiv = document.createElement('div');
            loadingDiv.className = 'message assistant';
            loadingDiv.id = 'loadingMessage';
            loadingDiv.innerHTML = '<div class="message-avatar">🤖</div>' +
                '<div class="message-content"><div class="typing-indicator">' +
                '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div></div>';
            chatMessages.appendChild(loadingDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
        
        function removeLoading() {
            var loading = document.getElementById('loadingMessage');
            if (loading) loading.remove();
        }
        
        function sendMessage() {
            var message = messageInput.value.trim();
            if (!message && !currentImage && !currentFile) return;
            
            sendBtn.disabled = true;
            var userMsg = message;
            var imageData = currentImage;
            
            if (currentImage) {
                userMsg = userMsg ? userMsg + ' [图片]' : '[图片]';
            }
            if (currentFile) {
                userMsg = userMsg ? userMsg + ' [文件：' + currentFile.name + ']' : '[文件：' + currentFile.name + ']';
            }
            
            addMessage(userMsg, true, imageData);
            messageInput.value = '';
            messageInput.style.height = 'auto';
            
            var fileToSend = currentFile;
            removeImage();
            removeFile();
            showLoading();
            
            var formData = new FormData();
            formData.append('message', message || '请分析');
            if (imageData) {
                fetch(imageData).then(function(r) { return r.blob(); }).then(function(blob) {
                    formData.append('image', blob, 'image.png');
                    sendRequest(formData, fileToSend);
                });
            } else {
                sendRequest(formData, fileToSend);
            }
        }
        
        function sendRequest(formData, file) {
            if (file) {
                formData.append('file', file);
            }
            
            fetch('/api/chat', { method: 'POST', body: formData })
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    removeLoading();
                    addMessage(data.response, false, null);
                    sendBtn.disabled = false;
                    messageInput.focus();
                })
                .catch(function(error) {
                    removeLoading();
                    addMessage('❌ 发送失败：' + error.message, false, null);
                    sendBtn.disabled = false;
                });
        }
        
        // 加载各页面数据
        function loadMemory() {
            fetch('/api/memory').then(function(r) { return r.json(); }).then(function(data) {
                var html = '';
                if (data.long_term && data.long_term.length > 0) {
                    html += '<div class="card"><div class="card-title">📌 长期记忆</div><ul class="data-list">';
                    data.long_term.forEach(function(item) { html += '<li>' + item + '</li>'; });
                    html += '</ul></div>';
                }
                if (data.daily && data.daily.length > 0) {
                    html += '<div class="card"><div class="card-title">📅 每日记忆</div><ul class="data-list">';
                    data.daily.forEach(function(item) { html += '<li>' + item.replace(/\\n/g, '<br>') + '</li>'; });
                    html += '</ul></div>';
                }
                document.getElementById('memory-content').innerHTML = html || '<div class="empty-state">🧠 暂无记忆数据</div>';
            });
        }
        
        function loadSkills() {
            fetch('/api/skills').then(function(r) { return r.json(); }).then(function(data) {
                if (data.skills && data.skills.length > 0) {
                    var html = '<div class="card"><div class="card-title">📚 已安装技能 (' + data.count + ')</div><ul class="data-list">';
                    data.skills.forEach(function(skill) {
                        html += '<li><strong>' + skill.name + '</strong> <span class="tag">' + skill.category + '</span><br><small>' + (skill.description || '') + '</small></li>';
                    });
                    html += '</ul></div>';
                    document.getElementById('skills-content').innerHTML = html;
                } else {
                    document.getElementById('skills-content').innerHTML = '<div class="empty-state">📚 暂无技能数据</div>';
                }
            });
        }
        
        function loadSessions() {
            fetch('/api/sessions').then(function(r) { return r.json(); }).then(function(data) {
                if (data.sessions && data.sessions.length > 0) {
                    var html = '<div class="card"><div class="card-title">📋 最近会话 (' + data.count + ')</div><ul class="data-list">';
                    data.sessions.forEach(function(s) {
                        var sessionId = s.id.replace('session_', '').split('_').slice(0, 3).join('_');
                        html += '<li class="session-item">';
                        html += '<div class="session-header">';
                        html += '<span class="session-title" id="title-' + s.id + '">' + (s.title || '未命名') + '</span>';
                        html += '<button class="edit-btn" onclick="editSessionTitle(\'' + s.id + '\', \'' + (s.title || '未命名').replace(/'/g, "\\'") + '\')">✏️ 编辑</button>';
                        html += '</div>';
                        html += '<small>📅 ' + s.created + ' | 💬 ' + s.messages + ' 条</small>';
                        html += '<small style="color:#666;">' + s.preview + '</small>';
                        html += '</li>';
                    });
                    html += '</ul></div>';
                    document.getElementById('sessions-content').innerHTML = html;
                } else {
                    document.getElementById('sessions-content').innerHTML = '<div class="empty-state">📋 暂无会话数据</div>';
                }
            });
        }
        
        function editSessionTitle(sessionId, currentTitle) {
            var newTitle = prompt('请输入新的会话名称:', currentTitle);
            if (newTitle && newTitle !== currentTitle) {
                fetch('/api/sessions/' + sessionId, {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({title: newTitle})
                }).then(function(r) { return r.json(); }).then(function(data) {
                    if (data.success) {
                        document.getElementById('title-' + sessionId).textContent = newTitle;
                        alert('✅ 会话名称已更新！');
                    } else {
                        alert('❌ 更新失败：' + (data.error || '未知错误'));
                    }
                }).catch(function(e) {
                    alert('❌ 更新失败：' + e.message);
                });
            }
        }
        
        function loadCron() {
            fetch('/api/cron').then(function(r) { return r.json(); }).then(function(data) {
                if (data.raw) {
                    document.getElementById('cron-content').innerHTML = '<div class="card"><div class="card-title">⏰ 定时任务</div><pre style="background:#0f0f1a;padding:15px;border-radius:8px;overflow-x:auto;">' + data.raw + '</pre></div>';
                } else {
                    document.getElementById('cron-content').innerHTML = '<div class="empty-state">⏰ 暂无定时任务</div>';
                }
            });
        }
        
        function loadProjects() {
            fetch('/api/projects').then(function(r) { return r.json(); }).then(function(data) {
                if (data.projects && data.projects.length > 0) {
                    var html = '<div class="card"><div class="card-title">📊 项目列表 (' + data.count + ')</div><ul class="data-list">';
                    data.projects.forEach(function(p) { html += '<li>' + p + '</li>'; });
                    html += '</ul></div>';
                    document.getElementById('projects-content').innerHTML = html;
                } else {
                    document.getElementById('projects-content').innerHTML = '<div class="empty-state">📊 暂无项目数据</div>';
                }
            });
        }
        
        function loadCosts() {
            fetch('/api/costs').then(function(r) { return r.json(); }).then(function(data) {
                var html = '<div class="stats-grid">';
                html += '<div class="stat-card"><div class="stat-value">' + (data.sessions || 0) + '</div><div class="stat-label">会话数</div></div>';
                html += '<div class="stat-card"><div class="stat-value">' + ((data.total_tokens || 0).toLocaleString()) + '</div><div class="stat-label">Token</div></div>';
                html += '<div class="stat-card"><div class="stat-value">' + (data.estimated_cost || '$0') + '</div><div class="stat-label">估算费用</div></div>';
                html += '</div>';
                document.getElementById('costs-content').innerHTML = html;
            });
        }
        
        function loadPatterns() {
            fetch('/api/patterns').then(function(r) { return r.json(); }).then(function(data) {
                var html = '<div class="stats-grid"><div class="stat-card"><div class="stat-value">' + (data.peak_hour || 'N/A') + ':00</div><div class="stat-label">高峰时段</div></div></div>';
                document.getElementById('patterns-content').innerHTML = html;
            });
        }
        
        // 清空对话历史
        function clearChatHistory() {
            if (confirm('确定要清空所有聊天记录吗？')) {
                localStorage.removeItem(CHAT_STORAGE_KEY);
                chatMessages.innerHTML = '<div class="message assistant"><div class="message-avatar">🤖</div><div class="message-content"><div class="message-text">👋 对话已清空，有什么可以帮你的吗？</div></div></div>';
            }
        }
    </script>
</body>
</html>'''

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
