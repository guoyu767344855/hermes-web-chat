"""
Hermes Agent Web Chat - 完整版
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
    
    # 解析记忆内容
    lines = content.split('\n')
    current_section = None
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
    
    # 获取长期记忆（MEMORY.md 开头的部分）
    memory_section = False
    for line in lines[:50]:
        if 'MEMORY.md' in line or '长期记忆' in line:
            memory_section = True
        elif memory_section and line.strip():
            long_term.append(line)
    
    return {
        "daily": daily[-20:],  # 最近 20 条
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
            
            # 提取会话信息
            session_id = Path(file_path).stem
            title = data.get("title", "未命名会话")
            created = data.get("created_at", "")
            message_count = len(data.get("messages", []))
            
            # 获取第一条用户消息作为预览
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
        except Exception as e:
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
    """获取项目数据（从记忆或配置中提取）"""
    memory_file = HERMES_HOME / "MEMORY.md"
    projects = []
    
    if memory_file.exists():
        content = memory_file.read_text()
        
        # 查找项目相关条目
        for line in content.split('\n'):
            if '🎯 重要项目' in line or '项目:' in line:
                projects.append(line.strip())
    
    # 如果没有找到，返回默认项目
    if not projects:
        projects = [
            "🎯 Hermes Web Chat - Web 聊天界面开发",
            "📊 小红书数据工具 - 数据获取与分析",
            "🏠 父亲健康照护系统 - 健康管理系统"
        ]
    
    return {"projects": projects, "count": len(projects)}

def get_costs_data():
    """获取费用统计"""
    # 从会话文件中统计
    sessions_dir = HERMES_HOME / "sessions"
    total_tokens = 0
    model_counts = {}
    
    if sessions_dir.exists():
        for file_path in glob.glob(str(sessions_dir / "*.json")):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 统计模型使用
                model = data.get("model", "unknown")
                model_counts[model] = model_counts.get(model, 0) + 1
                
                # 估算 token（简化）
                messages = data.get("messages", [])
                for msg in messages:
                    total_tokens += len(msg.get("content", "")) // 4
            except:
                continue
    
    return {
        "total_tokens": total_tokens,
        "sessions": sum(model_counts.values()),
        "models": model_counts,
        "estimated_cost": f"${total_tokens / 1000000 * 2:.4f}"  # 估算价格
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
                    # 解析时间
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

def get_html_content() -> str:
    """获取 HTML 页面内容"""
    return """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hermes Agent</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
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
            background-clip: text;
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
        .main { flex: 1; display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
        .content-area {
            flex: 1;
            overflow-y: auto;
            padding: 30px;
        }
        .page { display: none; animation: fadeIn 0.3s ease; }
        .page.active { display: block; }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .page-header {
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 1px solid #1f3a5f;
        }
        .page-header h2 {
            font-size: 24px;
            color: #00d9ff;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        /* 聊天页面布局 */
        #page-chat {
            display: flex;
            flex-direction: column;
            height: 100vh;
            overflow: hidden;
        }
        #page-chat.page.active {
            display: flex;
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
        .message-image, .message-file {
            max-width: 300px;
            border-radius: 10px;
            margin-top: 10px;
            border: 2px solid #2a2a4e;
        }
        .message-file {
            padding: 15px;
            background: #0f0f1a;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .file-icon {
            font-size: 32px;
        }
        .file-info {
            flex: 1;
            overflow: hidden;
        }
        .file-name {
            color: #00d9ff;
            font-size: 14px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .file-size {
            color: #666;
            font-size: 12px;
        }
        .input-container {
            padding: 20px 30px;
            background: rgba(15, 15, 26, 0.95);
            border-top: 1px solid #1f3a5f;
            position: sticky;
            bottom: 0;
            z-index: 100;
            backdrop-filter: blur(10px);
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
        .input-actions {
            display: flex;
            gap: 8px;
            padding-right: 8px;
            align-items: center;
        }
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
            position: sticky;
            bottom: 85px;
            z-index: 99;
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
        .file-preview-container {
            display: none;
            padding: 10px 30px;
            background: rgba(15, 15, 26, 0.95);
            border-top: 1px solid #1f3a5f;
        }
        .file-preview-container.show { display: block; }
        .file-preview-item {
            display: flex;
            align-items: center;
            gap: 15px;
            background: #1a1a2e;
            padding: 12px 20px;
            border-radius: 10px;
            border: 1px solid #2a2a4e;
        }
        .file-preview-icon {
            font-size: 32px;
        }
        .file-preview-info {
            flex: 1;
        }
        .file-preview-name {
            color: #e8e8e8;
            font-size: 14px;
        }
        .file-preview-size {
            color: #666;
            font-size: 12px;
        }
        .file-preview-remove {
            background: #ff4757;
            color: white;
            border: none;
            width: 28px;
            height: 28px;
            border-radius: 50%;
            cursor: pointer;
            font-size: 16px;
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
        #fileInput, #imageInput { display: none; }
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: #1a1a2e; }
        ::-webkit-scrollbar-thumb { background: #2a2a4e; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #3a3a5e; }
        
        /* 通用卡片样式 */
        .card {
            background: #1a1a2e;
            border: 1px solid #2a2a4e;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .card-title {
            font-size: 16px;
            color: #00d9ff;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .card-content {
            color: #a0a0a0;
            line-height: 1.6;
        }
        .data-list {
            list-style: none;
        }
        .data-list li {
            padding: 12px 15px;
            background: rgba(0, 217, 255, 0.05);
            border-radius: 8px;
            margin-bottom: 10px;
            border-left: 3px solid #00d9ff;
        }
        .data-list li code {
            background: #0f0f1a;
            padding: 2px 8px;
            border-radius: 4px;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 13px;
            color: #00ff88;
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
            background-clip: text;
            margin-bottom: 10px;
        }
        .stat-label {
            color: #888;
            font-size: 14px;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: #666;
        }
        .loading-spinner {
            width: 40px;
            height: 40px;
            border: 3px solid #2a2a4e;
            border-top-color: #00d9ff;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        .refresh-btn {
            background: #2a2a4e;
            color: #00d9ff;
            border: none;
            padding: 8px 16px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            margin-left: auto;
        }
        .refresh-btn:hover { background: #3a3a5e; }
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #666;
        }
        .empty-state-icon {
            font-size: 48px;
            margin-bottom: 20px;
        }
        .tag {
            display: inline-block;
            padding: 4px 12px;
            background: rgba(0, 217, 255, 0.1);
            color: #00d9ff;
            border-radius: 20px;
            font-size: 12px;
            margin-right: 8px;
        }
        .action-btn-sm {
            background: #2a2a4e;
            color: #888;
            border: none;
            padding: 6px 12px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 12px;
            margin-left: 10px;
        }
        .action-btn-sm:hover { background: #3a3a5e; color: #00d9ff; }
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
        <!-- 聊天页面 -->
        <div id="page-chat" class="page active">
            <div class="chat-messages" id="chatMessages">
                <div class="message assistant">
                    <div class="message-avatar">🤖</div>
                    <div class="message-content">
                        <div class="message-text">👋 你好！我是 Hermes Agent，有什么可以帮你的吗？
                        支持文字和图片提问，直接在输入框按 Ctrl+V / Cmd+V 粘贴图片即可。</div>
                    </div>
                </div>
            </div>
            <!-- 图片预览 -->
            <div class="preview-container" id="previewContainer">
                <div class="preview-wrapper">
                    <img class="preview-image" id="previewImage" src="" alt="预览">
                    <button class="preview-remove" onclick="removeImage()">✕</button>
                </div>
            </div>
            <!-- 文件预览 -->
            <div class="file-preview-container" id="filePreviewContainer">
                <div class="file-preview-item">
                    <div class="file-preview-icon" id="filePreviewIcon">📄</div>
                    <div class="file-preview-info">
                        <div class="file-preview-name" id="filePreviewName">filename.pdf</div>
                        <div class="file-preview-size" id="filePreviewSize">1.2 MB</div>
                    </div>
                    <button class="file-preview-remove" onclick="removeFile()">✕</button>
                </div>
            </div>
            <!-- 输入区域 -->
            <div class="input-container">
                <div class="input-wrapper">
                    <textarea id="messageInput" placeholder="输入消息... (支持粘贴图片 Ctrl+V/Cmd+V)" rows="1" onkeydown="handleKeyDown(event)"></textarea>
                    <input type="file" id="imageInput" accept="image/*" onchange="handleImageSelect(event)">
                    <input type="file" id="fileInput" onchange="handleFileSelect(event)">
                    <div class="input-actions">
                        <button class="action-btn upload-btn" onclick="document.getElementById('imageInput').click()" title="上传图片">🖼️</button>
                        <button class="action-btn upload-btn" onclick="document.getElementById('fileInput').click()" title="上传文件">📎</button>
                        <button class="action-btn send-btn" id="sendBtn" onclick="sendMessage()" title="发送">📤</button>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- 记忆管理页面 -->
        <div id="page-memory" class="page">
            <div class="page-header">
                <h2><span>🧠</span>记忆管理 <button class="refresh-btn" onclick="loadMemory()">🔄 刷新</button></h2>
            </div>
            <div id="memory-content">
                <div class="loading"><div class="loading-spinner"></div>加载中...</div>
            </div>
        </div>
        
        <!-- 技能列表页面 -->
        <div id="page-skills" class="page">
            <div class="page-header">
                <h2><span>📚</span>技能列表 <button class="refresh-btn" onclick="loadSkills()">🔄 刷新</button></h2>
            </div>
            <div id="skills-content">
                <div class="loading"><div class="loading-spinner"></div>加载中...</div>
            </div>
        </div>
        
        <!-- 会话历史页面 -->
        <div id="page-sessions" class="page">
            <div class="page-header">
                <h2><span>📋</span>会话历史 <button class="refresh-btn" onclick="loadSessions()">🔄 刷新</button></h2>
            </div>
            <div id="sessions-content">
                <div class="loading"><div class="loading-spinner"></div>加载中...</div>
            </div>
        </div>
        
        <!-- 定时任务页面 -->
        <div id="page-cron" class="page">
            <div class="page-header">
                <h2><span>⏰</span>定时任务 <button class="refresh-btn" onclick="loadCron()">🔄 刷新</button></h2>
            </div>
            <div id="cron-content">
                <div class="loading"><div class="loading-spinner"></div>加载中...</div>
            </div>
        </div>
        
        <!-- 项目跟踪页面 -->
        <div id="page-projects" class="page">
            <div class="page-header">
                <h2><span>📊</span>项目跟踪 <button class="refresh-btn" onclick="loadProjects()">🔄 刷新</button></h2>
            </div>
            <div id="projects-content">
                <div class="loading"><div class="loading-spinner"></div>加载中...</div>
            </div>
        </div>
        
        <!-- 费用统计页面 -->
        <div id="page-costs" class="page">
            <div class="page-header">
                <h2><span>💰</span>费用统计 <button class="refresh-btn" onclick="loadCosts()">🔄 刷新</button></h2>
            </div>
            <div id="costs-content">
                <div class="loading"><div class="loading-spinner"></div>加载中...</div>
            </div>
        </div>
        
        <!-- 使用模式页面 -->
        <div id="page-patterns" class="page">
            <div class="page-header">
                <h2><span>📈</span>使用模式 <button class="refresh-btn" onclick="loadPatterns()">🔄 刷新</button></h2>
            </div>
            <div id="patterns-content">
                <div class="loading"><div class="loading-spinner"></div>加载中...</div>
            </div>
        </div>
    </div>
    
    <script>
        // 页面切换
        document.querySelectorAll('.menu-item').forEach(item => {
            item.addEventListener('click', function() {
                const page = this.dataset.page;
                
                // 更新菜单状态
                document.querySelectorAll('.menu-item').forEach(i => i.classList.remove('active'));
                this.classList.add('active');
                
                // 切换页面
                document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
                document.getElementById('page-' + page).classList.add('active');
                
                // 加载页面数据
                if (page === 'memory') loadMemory();
                else if (page === 'skills') loadSkills();
                else if (page === 'sessions') loadSessions();
                else if (page === 'cron') loadCron();
                else if (page === 'projects') loadProjects();
                else if (page === 'costs') loadCosts();
                else if (page === 'patterns') loadPatterns();
            });
        });
        
        // 页面切换
        document.querySelectorAll('.menu-item').forEach(item => {
            item.addEventListener('click', function() {
                const page = this.dataset.page;
                
                // 更新菜单状态
                document.querySelectorAll('.menu-item').forEach(i => i.classList.remove('active'));
                this.classList.add('active');
                
                // 切换页面
                document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
                const targetPage = document.getElementById('page-' + page);
                if (targetPage) {
                    targetPage.classList.add('active');
                }
                
                // 加载页面数据
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
        let currentImage = null;
        let currentFile = null;
        const chatMessages = document.getElementById('chatMessages');
        const messageInput = document.getElementById('messageInput');
        const previewContainer = document.getElementById('previewContainer');
        const previewImage = document.getElementById('previewImage');
        const filePreviewContainer = document.getElementById('filePreviewContainer');
        const filePreviewIcon = document.getElementById('filePreviewIcon');
        const filePreviewName = document.getElementById('filePreviewName');
        const filePreviewSize = document.getElementById('filePreviewSize');
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
            document.getElementById('imageInput').value = '';
        }
        
        function removeFile() {
            currentFile = null;
            filePreviewContainer.classList.remove('show');
            document.getElementById('fileInput').value = '';
        }
        
        function getFileIcon(filename) {
            const ext = filename.split('.').pop().toLowerCase();
            const icons = {
                'pdf': '📕', 'doc': '📘', 'docx': '📘', 'txt': '📄',
                'xls': '📗', 'xlsx': '📗', 'csv': '📗',
                'ppt': '📙', 'pptx': '📙',
                'zip': '📦', 'rar': '📦', '7z': '📦',
                'jpg': '🖼️', 'jpeg': '🖼️', 'png': '🖼️', 'gif': '🖼️', 'webp': '🖼️',
                'mp3': '🎵', 'wav': '🎵', 'mp4': '🎬', 'mov': '🎬', 'avi': '🎬',
                'py': '🐍', 'js': '📜', 'html': '🌐', 'css': '🎨', 'json': '📋'
            };
            return icons[ext] || '📄';
        }
        
        function formatFileSize(bytes) {
            if (bytes < 1024) return bytes + ' B';
            if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
            return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
        }
        
        function handleFileSelect(e) {
            const file = e.target.files[0];
            if (file) {
                currentFile = file;
                filePreviewIcon.textContent = getFileIcon(file.name);
                filePreviewName.textContent = file.name;
                filePreviewSize.textContent = formatFileSize(file.size);
                filePreviewContainer.classList.add('show');
            }
        }
        
        function handleImageSelect(e) {
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
        
        function addMessage(content, isUser, imageData = null, fileData = null) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${isUser ? 'user' : 'assistant'}`;
            let mediaHtml = '';
            if (imageData) {
                mediaHtml = `<img class="message-image" src="${imageData}" alt="图片">`;
            }
            if (fileData) {
                mediaHtml += `
                    <div class="message-file">
                        <div class="file-icon">${getFileIcon(fileData.name)}</div>
                        <div class="file-info">
                            <div class="file-name">${fileData.name}</div>
                            <div class="file-size">${formatFileSize(fileData.size)}</div>
                        </div>
                    </div>
                `;
            }
            messageDiv.innerHTML = `
                <div class="message-avatar">${isUser ? '👤' : '🤖'}</div>
                <div class="message-content">
                    <div class="message-text">${content}</div>
                    ${mediaHtml}
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
            if (!message && !currentImage && !currentFile) return;
            
            sendBtn.disabled = true;
            
            // 构建用户消息显示
            let userMsg = message;
            let imageData = null;
            let fileData = null;
            
            if (currentImage) {
                userMsg = userMsg ? userMsg + '\n[图片]' : '[图片]';
                imageData = currentImage;
            }
            if (currentFile) {
                userMsg = userMsg ? userMsg + '\n[文件：' + currentFile.name + ']' : '[文件：' + currentFile.name + ']';
                fileData = currentFile;
            }
            
            addMessage(userMsg, true, imageData);
            messageInput.value = '';
            messageInput.style.height = 'auto';
            removeImage();
            removeFile();
            showLoading();
            
            try {
                const formData = new FormData();
                formData.append('message', message || (imageData ? '请分析这张图片' : '请处理这个文件'));
                if (imageData) {
                    const response = await fetch(imageData);
                    const blob = await response.blob();
                    formData.append('image', blob, 'image.png');
                }
                if (fileData) {
                    formData.append('file', fileData);
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
        
        // 加载各页面数据
        async function loadMemory() {
            const content = document.getElementById('memory-content');
            content.innerHTML = '<div class="loading"><div class="loading-spinner"></div>加载记忆中...</div>';
            
            try {
                const res = await fetch('/api/memory');
                const data = await res.json();
                
                let html = '';
                
                if (data.long_term && data.long_term.length > 0) {
                    html += '<div class="card"><div class="card-title">📌 长期记忆</div><ul class="data-list">';
                    data.long_term.forEach(item => {
                        html += `<li>${item}</li>`;
                    });
                    html += '</ul></div>';
                }
                
                if (data.daily && data.daily.length > 0) {
                    html += '<div class="card"><div class="card-title">📅 每日记忆</div><ul class="data-list">';
                    data.daily.forEach(item => {
                        html += `<li>${item.replace(/\\n/g, '<br>')}</li>`;
                    });
                    html += '</ul></div>';
                }
                
                if (!html) {
                    html = '<div class="empty-state"><div class="empty-state-icon">🧠</div><p>暂无记忆数据</p></div>';
                }
                
                content.innerHTML = html;
            } catch (error) {
                content.innerHTML = `<div class="empty-state">❌ 加载失败：${error.message}</div>`;
            }
        }
        
        async function loadSkills() {
            const content = document.getElementById('skills-content');
            content.innerHTML = '<div class="loading"><div class="loading-spinner"></div>加载技能列表...</div>';
            
            try {
                const res = await fetch('/api/skills');
                const data = await res.json();
                
                if (data.skills && data.skills.length > 0) {
                    let html = '<div class="card"><div class="card-title">📚 已安装技能 (' + data.count + ')</div><ul class="data-list">';
                    data.skills.forEach(skill => {
                        html += `<li><strong>${skill.name}</strong> <span class="tag">${skill.category}</span><br><small>${skill.description || ''}</small></li>`;
                    });
                    html += '</ul></div>';
                    content.innerHTML = html;
                } else {
                    content.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📚</div><p>暂无技能数据</p></div>';
                }
            } catch (error) {
                content.innerHTML = `<div class="empty-state">❌ 加载失败：${error.message}</div>`;
            }
        }
        
        async function loadSessions() {
            const content = document.getElementById('sessions-content');
            content.innerHTML = '<div class="loading"><div class="loading-spinner"></div>加载会话历史...</div>';
            
            try {
                const res = await fetch('/api/sessions');
                const data = await res.json();
                
                if (data.sessions && data.sessions.length > 0) {
                    let html = '<div class="card"><div class="card-title">📋 最近会话 (' + data.count + ')</div><ul class="data-list">';
                    data.sessions.forEach(session => {
                        html += `<li>
                            <strong>${session.title || '未命名会话'}</strong>
                            <br><small>📅 ${session.created} | 💬 ${session.messages} 条消息</small>
                            <br><small style="color: #666;">${session.preview}</small>
                            <button class="action-btn-sm" onclick="alert('会话文件：${session.file}')">📁 查看</button>
                        </li>`;
                    });
                    html += '</ul></div>';
                    content.innerHTML = html;
                } else {
                    content.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📋</div><p>暂无会话数据</p></div>';
                }
            } catch (error) {
                content.innerHTML = `<div class="empty-state">❌ 加载失败：${error.message}</div>`;
            }
        }
        
        async function loadCron() {
            const content = document.getElementById('cron-content');
            content.innerHTML = '<div class="loading"><div class="loading-spinner"></div>加载定时任务...</div>';
            
            try {
                const res = await fetch('/api/cron');
                const data = await res.json();
                
                if (data.raw) {
                    content.innerHTML = `<div class="card"><div class="card-title">⏰ 定时任务</div><div class="card-content"><pre style="background: #0f0f1a; padding: 15px; border-radius: 8px; overflow-x: auto;">${data.raw}</pre></div></div>`;
                } else if (data.jobs && data.jobs.length > 0) {
                    let html = '<div class="card"><div class="card-title">⏰ 定时任务</div><ul class="data-list">';
                    data.jobs.forEach(job => {
                        html += `<li><code>${job}</code></li>`;
                    });
                    html += '</ul></div>';
                    content.innerHTML = html;
                } else {
                    content.innerHTML = '<div class="empty-state"><div class="empty-state-icon">⏰</div><p>暂无定时任务</p></div>';
                }
            } catch (error) {
                content.innerHTML = `<div class="empty-state">❌ 加载失败：${error.message}</div>`;
            }
        }
        
        async function loadProjects() {
            const content = document.getElementById('projects-content');
            content.innerHTML = '<div class="loading"><div class="loading-spinner"></div>加载项目...</div>';
            
            try {
                const res = await fetch('/api/projects');
                const data = await res.json();
                
                if (data.projects && data.projects.length > 0) {
                    let html = '<div class="card"><div class="card-title">📊 项目列表 (' + data.count + ')</div><ul class="data-list">';
                    data.projects.forEach(project => {
                        html += `<li>${project}</li>`;
                    });
                    html += '</ul></div>';
                    content.innerHTML = html;
                } else {
                    content.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📊</div><p>暂无项目数据</p></div>';
                }
            } catch (error) {
                content.innerHTML = `<div class="empty-state">❌ 加载失败：${error.message}</div>`;
            }
        }
        
        async function loadCosts() {
            const content = document.getElementById('costs-content');
            content.innerHTML = '<div class="loading"><div class="loading-spinner"></div>加载费用统计...</div>';
            
            try {
                const res = await fetch('/api/costs');
                const data = await res.json();
                
                let html = '<div class="stats-grid">';
                html += `<div class="stat-card"><div class="stat-value">${data.sessions || 0}</div><div class="stat-label">总会话数</div></div>`;
                html += `<div class="stat-card"><div class="stat-value">${(data.total_tokens || 0).toLocaleString()}</div><div class="stat-label">估算 Token</div></div>`;
                html += `<div class="stat-card"><div class="stat-value">${data.estimated_cost || '$0'}</div><div class="stat-label">估算费用</div></div>`;
                html += '</div>';
                
                if (data.models && Object.keys(data.models).length > 0) {
                    html += '<div class="card"><div class="card-title">🤖 模型使用分布</div><ul class="data-list">';
                    for (const [model, count] of Object.entries(data.models)) {
                        html += `<li><strong>${model}</strong>: ${count} 次会话</li>`;
                    }
                    html += '</ul></div>';
                }
                
                content.innerHTML = html;
            } catch (error) {
                content.innerHTML = `<div class="empty-state">❌ 加载失败：${error.message}</div>`;
            }
        }
        
        async function loadPatterns() {
            const content = document.getElementById('patterns-content');
            content.innerHTML = '<div class="loading"><div class="loading-spinner"></div>加载使用模式...</div>';
            
            try {
                const res = await fetch('/api/patterns');
                const data = await res.json();
                
                let html = '<div class="stats-grid">';
                html += `<div class="stat-card"><div class="stat-value">${data.peak_hour || 'N/A'}:00</div><div class="stat-label">使用高峰时段</div></div>`;
                html += '</div>';
                
                if (data.daily && Object.keys(data.daily).length > 0) {
                    html += '<div class="card"><div class="card-title">📅 最近 14 天使用情况</div><ul class="data-list">';
                    for (const [day, count] of Object.entries(data.daily)) {
                        html += `<li><strong>${day}</strong>: ${count} 个会话</li>`;
                    }
                    html += '</ul></div>';
                }
                
                if (data.hourly && Object.keys(data.hourly).some(k => data.hourly[k] > 0)) {
                    html += '<div class="card"><div class="card-title">🕐 24 小时使用分布</div><ul class="data-list">';
                    for (let i = 0; i < 24; i++) {
                        const count = data.hourly[String(i)] || 0;
                        if (count > 0) {
                            html += `<li><strong>${i}:00</strong>: ${count} 个会话</li>`;
                        }
                    }
                    html += '</ul></div>';
                }
                
                content.innerHTML = html;
            } catch (error) {
                content.innerHTML = `<div class="empty-state">❌ 加载失败：${error.message}</div>`;
            }
        }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def get_chat_page():
    return HTMLResponse(content=get_html_content())

@app.post("/api/chat")
async def chat(message: str = Form(...), image: UploadFile = File(None), file: UploadFile = File(None)):
    """处理聊天请求"""
    image_path = None
    file_path = None
    
    # 处理图片
    if image:
        temp_path = tempfile.mktemp(suffix=".png", dir=str(UPLOAD_DIR))
        with open(temp_path, "wb") as f:
            content = await image.read()
            f.write(content)
        image_path = temp_path
    
    # 处理文件
    if file:
        temp_path = tempfile.mktemp(suffix=f"_{file.filename}", dir=str(UPLOAD_DIR))
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        file_path = temp_path
    
    # 构建消息
    full_message = message
    if file and file.filename:
        full_message = f"{message}\n\n[文件：{file.filename}]\n文件已上传，请分析或处理。"
    
    response = call_hermes(full_message, image_path)
    
    # 清理临时文件
    if image_path and os.path.exists(image_path):
        os.remove(image_path)
    if file_path and os.path.exists(file_path):
        os.remove(file_path)
    
    return JSONResponse(content={"response": response})

@app.get("/api/memory")
async def api_memory():
    """获取记忆数据"""
    return JSONResponse(content=get_memory_data())

@app.get("/api/skills")
async def api_skills():
    """获取技能列表"""
    return JSONResponse(content=get_skills_data())

@app.get("/api/sessions")
async def api_sessions():
    """获取会话历史"""
    return JSONResponse(content=get_sessions_data())

@app.get("/api/cron")
async def api_cron():
    """获取定时任务"""
    return JSONResponse(content=get_cron_data())

@app.get("/api/projects")
async def api_projects():
    """获取项目数据"""
    return JSONResponse(content=get_projects_data())

@app.get("/api/costs")
async def api_costs():
    """获取费用统计"""
    return JSONResponse(content=get_costs_data())

@app.get("/api/patterns")
async def api_patterns():
    """获取使用模式"""
    return JSONResponse(content=get_patterns_data())

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
