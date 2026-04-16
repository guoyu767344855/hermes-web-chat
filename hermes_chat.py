"""
Hermes Agent Web Chat - 跨平台版本 (Windows/Mac/Linux)
"""
from fastapi import FastAPI, Form, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pathlib import Path
import subprocess, tempfile, os, json, glob, sys, shutil, platform
from typing import Optional, Generator
import uvicorn
from datetime import datetime

app = FastAPI()

# 跨平台 HERMES_HOME 路径
if platform.system() == "Windows":
    # Windows: 使用用户目录
    HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".Hermes"))
else:
    # Mac/Linux
    HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".Hermes"))

UPLOAD_DIR = HERMES_HOME / "web-chat" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

def get_hermes_cmd():
    """跨平台查找 hermes 命令"""
    hermes_cmd = shutil.which("hermes")
    if not hermes_cmd:
        # Windows 额外检查
        if platform.system() == "Windows":
            # 检查常见安装位置
            possible_paths = [
                Path.home() / ".local" / "bin" / "hermes.exe",
                Path.home() / ".local" / "bin" / "hermes",
                Path("C:\\Program Files\\Hermes\\hermes.exe"),
                Path("C:\\Users\\Public\\Hermes\\hermes.exe"),
            ]
            for p in possible_paths:
                if p.exists():
                    return str(p)
    return hermes_cmd

def get_memory_data():
    possible_paths = [HERMES_HOME / "memories" / "MEMORY.md", HERMES_HOME / "MEMORY.md", Path.home() / ".hermes" / "memories" / "MEMORY.md"]
    memory_file = None
    for p in possible_paths:
        if p.exists(): memory_file = p; break
    if not memory_file: return {"daily": [], "long_term": [], "file_path": None}
    content = memory_file.read_text()
    daily, current = [], []
    for line in content.split('\n'):
        if line.startswith('> 2026-') or line.startswith('> 2025-') or (len(line) > 10 and line[0:4].isdigit() and line[4:5] == '-'):
            if current: daily.append('\n'.join(current))
            current = [line]
        elif line.strip() and current: current.append(line)
        elif line.startswith('§') or line.strip() == '---':
            if current: daily.append('\n'.join(current)); current = []
    if current: daily.append('\n'.join(current))
    daily = [d for d in daily if d.strip() and not d.startswith('> 这里保存')]
    return {"daily": daily[-20:], "long_term": [], "file_path": str(memory_file)}

def get_skills_data():
    try:
        hermes_cmd = get_hermes_cmd()
        if not hermes_cmd: return {"skills": [], "count": 0, "error": "hermes command not found"}
        result = subprocess.run([hermes_cmd, "skills", "list"], capture_output=True, text=True, timeout=30, env={**os.environ, "HERMES_HOME": str(HERMES_HOME)})
        skills = []
        for line in result.stdout.strip().split('\n'):
            # 只处理表格数据行（以│开头和结尾）
            if line.strip().startswith('│') and line.strip().endswith('│'):
                # 按│分割，去掉首尾空元素
                parts = [p.strip() for p in line.split('│')[1:-1]]
                # 表格格式：Name | Category | Source | Trust (4 列)
                if len(parts) >= 4 and parts[0] and not parts[0].startswith('━') and not parts[0].startswith('┃') and not parts[0].startswith('┡'):
                    skills.append({"name": parts[0], "category": parts[1] if parts[1] else "builtin", "source": parts[2], "trust": parts[3]})
        return {"skills": skills, "count": len(skills)}
    except Exception as e:
        print(f"Skills error: {e}")
        return {"skills": [], "count": 0}

def get_sessions_data():
    sessions_dir = HERMES_HOME / "sessions"
    if not sessions_dir.exists(): return {"sessions": []}
    sessions = []
    for fp in sorted(glob.glob(str(sessions_dir / "*.json")), reverse=True)[:50]:
        try:
            with open(fp, 'r', encoding='utf-8') as f: data = json.load(f)
            filename = Path(fp).stem
            parts = filename.split('_')
            time_str = ""
            if len(parts) >= 3:
                date = parts[1]
                time = parts[2]
                time_str = f"{date[:4]}-{date[4:6]}-{date[6:8]} {time[:2]}:{time[2:4]}"
            title = data.get("title", "")
            msgs = data.get("messages", [])
            if not title:
                for m in msgs:
                    if m.get("role") == "user":
                        title = m.get("content", "未命名会话")[:30]
                        break
                if not title: title = "未命名会话"
            preview = next((m.get("content","")[:100] for m in msgs[:3] if m.get("role")=="user"), "")
            sessions.append({"id": filename, "title": title, "created": data.get("created_at", time_str), "messages": len(msgs), "preview": preview})
        except: continue
    return {"sessions": sessions, "count": len(sessions)}

def get_session_detail(session_id):
    sessions_dir = HERMES_HOME / "sessions"
    fp = sessions_dir / f"{session_id}.json"
    if not fp.exists(): return {"error": "Session not found", "messages": []}
    try:
        with open(fp, 'r', encoding='utf-8') as f: data = json.load(f)
        msgs = data.get("messages", [])
        # 转换为前端格式
        messages = []
        for m in msgs:
            role = m.get("role", "assistant")
            content = m.get("content", "")
            is_user = (role == "user")
            messages.append({"content": content, "isUser": is_user, "imageData": None})
        return {"messages": messages, "title": data.get("title", ""), "created": data.get("created_at", "")}
    except Exception as e:
        return {"error": str(e), "messages": []}

def get_cron_data():
    try:
        hermes_cmd = get_hermes_cmd()
        if not hermes_cmd: return {"raw": "hermes command not found"}
        result = subprocess.run([hermes_cmd, "cronjob", "list"], capture_output=True, text=True, timeout=30, env={**os.environ, "HERMES_HOME": str(HERMES_HOME)})
        return {"raw": result.stdout}
    except: return {"raw": ""}

def get_projects_data():
    possible_paths = [HERMES_HOME / "memories" / "MEMORY.md", HERMES_HOME / "MEMORY.md", Path.home() / ".hermes" / "memories" / "MEMORY.md"]
    projects = []
    for p in possible_paths:
        if p.exists():
            content = p.read_text()
            current_project = []
            for line in content.split('\n'):
                if '🎯 重要项目' in line:
                    if current_project: projects.append(' '.join(current_project))
                    current_project = [line.strip()]
                elif current_project and ('**' in line or line.strip().startswith('-')):
                    current_project.append(line.strip())
                elif current_project and line.strip() == '---':
                    projects.append(' '.join(current_project)); current_project = []
            if current_project: projects.append(' '.join(current_project))
            break
    return {"projects": projects or ["暂无项目数据"], "count": len(projects)}

def get_costs_data():
    sessions_dir = HERMES_HOME / "sessions"
    total_tokens, model_counts = 0, {}
    if sessions_dir.exists():
        for fp in glob.glob(str(sessions_dir / "*.json")):
            try:
                with open(fp, 'r', encoding='utf-8') as f: data = json.load(f)
                model = data.get("model", "unknown")
                model_counts[model] = model_counts.get(model, 0) + 1
                total_tokens += sum(len(m.get("content",""))//4 for m in data.get("messages",[]))
            except: continue
    return {"total_tokens": total_tokens, "sessions": sum(model_counts.values()), "models": model_counts, "estimated_cost": f"${total_tokens/1000000*2:.2f}"}

def get_patterns_data():
    sessions_dir = HERMES_HOME / "sessions"
    hourly, daily = {str(i):0 for i in range(24)}, {}
    if sessions_dir.exists():
        for fp in glob.glob(str(sessions_dir / "*.json")):
            try:
                with open(fp, 'r', encoding='utf-8') as f: data = json.load(f)
                created = data.get("created_at", "")
                if created:
                    dt = datetime.fromisoformat(created.replace('Z','+00:00'))
                    hourly[str(dt.hour)] += 1
                    daily[dt.strftime('%Y-%m-%d')] = daily.get(dt.strftime('%Y-%m-%d'),0) + 1
            except: continue
    return {"hourly": hourly, "daily": dict(sorted(daily.items(), reverse=True)[:14]), "peak_hour": max(hourly.keys(), key=lambda k: hourly[k]) if any(hourly.values()) else "N/A"}

def call_hermes_stream(message: str, image_path: Optional[str] = None) -> Generator[str, None, None]:
    """流式调用 hermes，实时返回输出"""
    try:
        hermes_cmd = get_hermes_cmd()
        if not hermes_cmd:
            yield "错误：找不到 hermes 命令，请确认已正确安装\n"
            return
        
        # 使用 -Q 参数只输出回复，不显示工具列表等
        cmd = [hermes_cmd, "chat", "-q", message or "你好", "-Q", "--source", "web"]
        if image_path: cmd.extend(["--image", image_path])
        
        # 使用 Popen 实现流式输出
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env={**os.environ, "HERMES_HOME": str(HERMES_HOME)}
        )
        
        # 实时读取输出
        for line in process.stdout:
            if line.strip():
                yield line
        
        process.wait()
    except subprocess.TimeoutExpired:
        yield "请求超时\n"
    except Exception as e:
        yield f"错误：{e}\n"

def call_hermes(message: str, image_path: Optional[str] = None) -> str:
    try:
        # 跨平台查找 hermes 命令
        hermes_cmd = get_hermes_cmd()
        if not hermes_cmd:
            return "错误：找不到 hermes 命令，请确认已正确安装"
        cmd = [hermes_cmd, "chat", "-q", message or "你好", "-Q", "--source", "web"]
        if image_path: cmd.extend(["--image", image_path])
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, env={**os.environ, "HERMES_HOME": str(HERMES_HOME)})
        return result.stdout.strip() or result.stderr.strip() or "没有回复"
    except subprocess.TimeoutExpired: return "请求超时"
    except Exception as e: return f"错误：{e}"

@app.get("/", response_class=HTMLResponse)
async def get_chat_page(): return HTMLResponse(content=get_html_content())

@app.post("/api/chat")
async def chat(message: str = Form(...), image: UploadFile = File(None), file: UploadFile = File(None)):
    image_path, file_path = None, None
    file_content = None
    try:
        if image:
            content = await image.read()
            print(f"Received image: {image.filename}, size: {len(content)} bytes")
            tp = tempfile.mktemp(suffix=".png", dir=str(UPLOAD_DIR))
            with open(tp, "wb") as f: f.write(content)
            image_path = tp
            print(f"Image saved to: {image_path}")
        if file:
            content = await file.read()
            print(f"Received file: {file.filename}, size: {len(content)} bytes, content_type: {file.content_type}")
            file_path = tempfile.mktemp(suffix=f"_{file.filename}", dir=str(UPLOAD_DIR))
            with open(file_path, "wb") as f: f.write(content)
            try:
                file_content = content.decode('utf-8')
                print(f"File content (text): {len(file_content)} chars")
            except:
                print("File is binary, cannot read as text")
        msg = message or "请分析"
        if file and file.filename:
            if file_content:
                msg = f"{msg}\n\n[文件：{file.filename}]\n文件内容:\n{file_content[:10000]}"
            else:
                msg = f"{msg}\n\n[文件：{file.filename}]\n这是一个二进制文件，已保存到：{file_path}"
        print(f"Calling hermes with message: {msg[:100]}..., image_path: {image_path}")
        response = call_hermes(msg, image_path)
        print(f"Hermes response: {response[:200]}...")
        for p in [image_path, file_path]:
            if p and os.path.exists(p): os.remove(p)
        return JSONResponse(content={"response": response})
    except Exception as e:
        print(f"Chat error: {e}")
        return JSONResponse(content={"response": f"错误：{e}"})

@app.post("/api/chat_stream")
async def chat_stream(message: str = Form(...), image: UploadFile = File(None), file: UploadFile = File(None)):
    """流式聊天接口"""
    image_path, file_path = None, None
    file_content = None
    try:
        if image:
            content = await image.read()
            tp = tempfile.mktemp(suffix=".png", dir=str(UPLOAD_DIR))
            with open(tp, "wb") as f: f.write(content)
            image_path = tp
        if file:
            content = await file.read()
            file_path = tempfile.mktemp(suffix=f"_{file.filename}", dir=str(UPLOAD_DIR))
            with open(file_path, "wb") as f: f.write(content)
            try:
                file_content = content.decode('utf-8')
            except:
                pass
        msg = message or "请分析"
        if file and file.filename:
            if file_content:
                msg = f"{msg}\n\n[文件：{file.filename}]\n文件内容:\n{file_content[:10000]}"
            else:
                msg = f"{msg}\n\n[文件：{file.filename}]\n这是一个二进制文件"
        
        def generate():
            for chunk in call_hermes_stream(msg, image_path):
                yield f"data: {chunk}\n\n"
            # 清理临时文件
            for p in [image_path, file_path]:
                if p and os.path.exists(p): os.remove(p)
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(generate(), media_type="text/event-stream")
    except Exception as e:
        print(f"Stream error: {e}")
        return JSONResponse(content={"response": f"错误：{e}"})

@app.get("/api/memory")
async def api_memory(): return JSONResponse(content=get_memory_data())
@app.get("/api/skills")
async def api_skills(): return JSONResponse(content=get_skills_data())
@app.get("/api/sessions")
async def api_sessions(): return JSONResponse(content=get_sessions_data())
@app.get("/api/session_detail")
async def api_session_detail(session_id: str): return JSONResponse(content=get_session_detail(session_id))
@app.get("/api/cron")
async def api_cron(): return JSONResponse(content=get_cron_data())
@app.get("/api/projects")
async def api_projects(): return JSONResponse(content=get_projects_data())
@app.get("/api/costs")
async def api_costs(): return JSONResponse(content=get_costs_data())
@app.get("/api/patterns")
async def api_patterns(): return JSONResponse(content=get_patterns_data())

def get_html_content():
    return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <title>Hermes Agent</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js?v=2"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%); min-height: 100vh; display: flex; color: #e8e8e8; }
        .sidebar { width: 260px; background: linear-gradient(180deg, #0a0a1a 0%, #1a1a2e 100%); border-right: 1px solid #1f3a5f; flex-shrink: 0; display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
        .logo { text-align: center; padding: 20px; border-bottom: 1px solid #1f3a5f; position: relative; }
        .logo h1 { font-size: 24px; background: linear-gradient(135deg, #00d9ff 0%, #00ff88 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .logo p { color: #666; font-size: 12px; margin-top: 5px; }
        .page-header { padding: 20px 30px; border-bottom: 1px solid #1f3a5f; background: rgba(15, 15, 26, 0.8); display: flex; justify-content: space-between; align-items: center; }
        .page-header h2 { font-size: 18px; color: #e8e8e8; margin: 0; display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
        .header-actions { display: flex; gap: 8px; }
        .header-btn { width: 32px; height: 32px; border-radius: 8px; border: none; background: #2a2a4e; color: #888; cursor: pointer; font-size: 16px; transition: all 0.2s; }
        .header-btn:hover { background: #00d9ff; color: white; }
        .menu { list-style: none; padding: 10px; flex: 1; overflow-y: auto; }
        .menu-item { padding: 12px 16px; margin: 4px 0; border-radius: 8px; cursor: pointer; transition: all 0.2s; color: #888; }
        .menu-item:hover { background: rgba(0, 217, 255, 0.1); color: #00d9ff; }
        .menu-item.active { background: linear-gradient(135deg, #00d9ff 0%, #0099ff 100%); color: white; }
        .main { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
        .page { display: none; height: 100vh; flex-direction: column; }
        .page.active { display: flex; }
        .page-header { padding: 20px 30px; border-bottom: 1px solid #1f3a5f; background: rgba(15, 15, 26, 0.8); }
        .page-header h2 { font-size: 18px; color: #e8e8e8; }
        .chat-messages { flex: 1; overflow-y: auto; overflow-x: hidden; padding: 30px; display: flex; flex-direction: column; gap: 20px; }
        .message { display: flex; gap: 15px; max-width: 80%; }
        .message.user { align-self: flex-end; flex-direction: row-reverse; }
        .message-avatar { width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 20px; flex-shrink: 0; }
        .message-content { background: #1a1a2e; padding: 15px 20px; border-radius: 16px; border: 1px solid #2a2a4e; max-width: 100%; overflow-wrap: break-word; word-wrap: break-word; word-break: break-word; }
        .message-text { color: #e8e8e8; line-height: 1.6; font-size: 15px; overflow-wrap: break-word; word-wrap: break-word; word-break: break-word; max-width: 100%; }
        .message-text p { margin: 0.5em 0; }
        .message-text p:first-child { margin-top: 0; }
        .message-text p:last-child { margin-bottom: 0; }
        .message-text code { background: #2a2a4e; padding: 2px 6px; border-radius: 4px; font-family: 'Consolas', 'Monaco', monospace; font-size: 13px; }
        .message-text pre { background: #0f0f1a; padding: 12px; border-radius: 8px; overflow-x: auto; margin: 10px 0; }
        .message-text pre code { background: transparent; padding: 0; color: #e8e8e8; }
        .message-text ul, .message-text ol { margin: 10px 0; padding-left: 25px; }
        .message-text li { margin: 5px 0; }
        .message-text blockquote { border-left: 3px solid #00d9ff; padding-left: 15px; margin: 10px 0; color: #888; }
        .message-text strong { color: #00d9ff; font-weight: 600; }
        .message-text h1, .message-text h2, .message-text h3 { margin: 15px 0 10px; color: #00d9ff; }
        .message-text h1 { font-size: 18px; }
        .message-text h2 { font-size: 16px; }
        .message-text h3 { font-size: 15px; }
        .message-text a { color: #00d9ff; text-decoration: none; }
        .message-text a:hover { text-decoration: underline; }
        .message-image { max-width: 100%; max-height: 400px; border-radius: 10px; margin-top: 10px; border: 2px solid #2a2a4e; }
        .input-container { padding: 20px 30px; background: rgba(15, 15, 26, 0.95); border-top: 1px solid #1f3a5f; }
        .input-wrapper { display: flex; gap: 15px; align-items: flex-end; background: #1a1a2e; border: 2px solid #2a2a4e; border-radius: 24px; padding: 8px 8px 8px 20px; }
        #messageInput { flex: 1; background: transparent; border: none; outline: none; color: #e8e8e8; font-size: 15px; padding: 10px 0; resize: none; max-height: 150px; font-family: inherit; }
        .input-actions { display: flex; gap: 8px; }
        .action-btn { width: 44px; height: 44px; border-radius: 50%; border: none; cursor: pointer; background: #2a2a4e; color: #888; font-size: 20px; }
        .action-btn:hover { background: #3a3a5e; color: #00d9ff; }
        #sendBtn { background: linear-gradient(135deg, #00d9ff 0%, #0099ff 100%); color: white; }
        .preview-container, .file-preview-container { display: none; padding: 10px 30px; background: rgba(15, 15, 26, 0.95); border-top: 1px solid #1f3a5f; }
        .preview-container.show, .file-preview-container.show { display: block; }
        .preview-image { max-height: 150px; border-radius: 10px; border: 2px solid #00d9ff; }
        .preview-remove, .file-preview-remove { background: #ff4757; color: white; border: none; width: 24px; height: 24px; border-radius: 50%; cursor: pointer; float: right; }
        #fileInput, #imageInput { display: none; }
        .card { background: #1a1a2e; border: 1px solid #2a2a4e; border-radius: 12px; padding: 20px; margin-bottom: 20px; }
        .data-list { list-style: none; }
        .data-list li { padding: 12px 15px; background: rgba(0, 217, 255, 0.05); border-radius: 8px; margin-bottom: 10px; border-left: 3px solid #00d9ff; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }
        .stat-card { background: linear-gradient(135deg, #1a1a2e 0%, #1f3a5f 100%); border: 1px solid #2a4a6f; border-radius: 12px; padding: 25px; text-align: center; }
        .stat-value { font-size: 36px; font-weight: bold; color: #00d9ff; }
        .stat-label { color: #888; font-size: 14px; margin-top: 10px; }
        .loading { text-align: center; padding: 40px; color: #666; }
        .loading-spinner { width: 40px; height: 40px; border: 3px solid #2a2a4e; border-top-color: #00d9ff; border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 20px; }
        @keyframes spin { to { transform: rotate(360deg); } }
        .typing-indicator { display: flex; gap: 4px; padding: 15px 20px; align-items: center; }
        .typing-dot { width: 8px; height: 8px; border-radius: 50%; background: #00d9ff; animation: typing-bounce 1.4s infinite ease-in-out; }
        .typing-dot:nth-child(1) { animation-delay: 0s; }
        .typing-dot:nth-child(2) { animation-delay: 0.2s; }
        .typing-dot:nth-child(3) { animation-delay: 0.4s; }
        @keyframes typing-bounce { 0%, 80%, 100% { transform: translateY(0); opacity: 0.3; } 40% { transform: translateY(-6px); opacity: 1; } }
        .refresh-btn { background: #2a2a4e; color: #00d9ff; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 13px; }
        .refresh-btn:hover { background: #00d9ff; color: #0f0f1a; }
        .filter-bar { display: inline-flex; align-items: center; }
        .filter-select { background: #2a2a4e; color: #e8e8e8; border: 1px solid #3a3a5e; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 13px; }
        .filter-select:hover { border-color: #00d9ff; }
        .filter-select:focus { outline: none; border-color: #00d9ff; }
        .clear-btn { width: calc(100% - 20px); margin: 10px; padding: 10px; background: #2a2a4e; color: #ff6b6b; border: none; border-radius: 8px; cursor: pointer; }
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: #1a1a2e; }
        ::-webkit-scrollbar-thumb { background: #2a2a4e; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="sidebar">
        <div class="logo">
            <h1>Hermes Agent</h1>
            <p>AI 智能助手</p>
        </div>
        <ul class="menu">
            <li class="menu-item active" data-page="chat">💬 聊天对话</li>
            <li class="menu-item" data-page="memory">🧠 记忆管理</li>
            <li class="menu-item" data-page="skills">📚 技能列表</li>
            <li class="menu-item" data-page="sessions">📋 会话历史</li>
            <li class="menu-item" data-page="cron">⏰ 定时任务</li>
            <li class="menu-item" data-page="projects">📊 项目跟踪</li>
            <li class="menu-item" data-page="costs">💰 费用统计</li>
            <li class="menu-item" data-page="patterns">📈 使用模式</li>
        </ul>
        </div>
    <div class="main">
        <div id="page-chat" class="page active">
            <div class="page-header">
                <h2 id="currentSessionTitle">💬 当前会话</h2>
                <div class="header-actions">
                    <button class="header-btn" onclick="createNewSession()" title="新建会话">➕</button>
                    <button class="header-btn" onclick="clearChatHistory()" title="清空对话">🗑️</button>
                </div>
            </div>
            <div class="chat-messages" id="chatMessages"></div>
            <div class="preview-container" id="previewContainer"><img class="preview-image" id="previewImage" src=""><button class="preview-remove" onclick="removeImage()">X</button></div>
            <div class="file-preview-container" id="filePreviewContainer"><div style="display:flex;align-items:center;gap:10px;"><span id="filePreviewIcon" style="font-size:24px;"></span><div><div id="filePreviewName" style="color:#e8e8e8;font-size:14px;"></div><div id="filePreviewSize" style="color:#666;font-size:12px;"></div></div><button class="file-preview-remove" onclick="removeFile()">X</button></div></div>
            <div class="input-container">
                <div class="input-wrapper">
                    <textarea id="messageInput" placeholder="输入消息... (支持粘贴图片 Ctrl+V/Cmd+V)" rows="1"></textarea>
                    <input type="file" id="imageInput" accept="image/*">
                    <input type="file" id="fileInput">
                    <div class="input-actions">
                        <button class="action-btn" onclick="document.getElementById('imageInput').click()" title="上传图片">🖼️</button>
                        <button class="action-btn" onclick="document.getElementById('fileInput').click()" title="上传文件">📎</button>
                        <button class="action-btn" id="sendBtn" onclick="sendMessage()" title="发送">📤</button>
                    </div>
                </div>
            </div>
        </div>
        <div id="page-memory" class="page">
            <div class="page-header">
                <h2>
                    🧠 记忆管理 
                    <button class="refresh-btn" onclick="loadMemory()">刷新</button>
                    <div class="filter-bar">
                        <select class="filter-select" id="memoryDateFilter" onchange="filterMemory()">
                            <option value="all">全部时间</option>
                            <option value="7">最近 7 天</option>
                            <option value="30">最近 30 天</option>
                            <option value="90">最近 90 天</option>
                        </select>
                    </div>
                </h2>
            </div>
            <div class="chat-messages" id="memory-content"><div class="loading"><div class="loading-spinner"></div>加载中...</div></div>
        </div>
        <div id="page-skills" class="page"><div class="page-header"><h2>📚 技能列表 <button class="refresh-btn" onclick="loadSkills()">刷新</button></h2></div><div class="chat-messages" id="skills-content"><div class="loading"><div class="loading-spinner"></div>加载中...</div></div></div>
        <div id="page-sessions" class="page">
            <div class="page-header">
                <h2>
                    📋 会话历史 
                    <button class="refresh-btn" onclick="loadSessions()">刷新</button>
                    <div class="filter-bar">
                        <select class="filter-select" id="sessionDateFilter" onchange="filterSessions()">
                            <option value="all">全部时间</option>
                            <option value="7">最近 7 天</option>
                            <option value="30">最近 30 天</option>
                            <option value="90">最近 90 天</option>
                        </select>
                    </div>
                </h2>
            </div>
            <div class="chat-messages" id="sessions-content"><div class="loading"><div class="loading-spinner"></div>加载中...</div></div>
        </div>
        <div id="page-cron" class="page"><div class="page-header"><h2>⏰ 定时任务 <button class="refresh-btn" onclick="loadCron()">刷新</button></h2></div><div class="chat-messages" id="cron-content"><div class="loading"><div class="loading-spinner"></div>加载中...</div></div></div>
        <div id="page-projects" class="page"><div class="page-header"><h2>📊 项目跟踪 <button class="refresh-btn" onclick="loadProjects()">刷新</button></h2></div><div class="chat-messages" id="projects-content"><div class="loading"><div class="loading-spinner"></div>加载中...</div></div></div>
        <div id="page-costs" class="page"><div class="page-header"><h2>💰 费用统计 <button class="refresh-btn" onclick="loadCosts()">刷新</button></h2></div><div class="chat-messages" id="costs-content"><div class="loading"><div class="loading-spinner"></div>加载中...</div></div></div>
        <div id="page-patterns" class="page"><div class="page-header"><h2>📈 使用模式 <button class="refresh-btn" onclick="loadPatterns()">刷新</button></h2></div><div class="chat-messages" id="patterns-content"><div class="loading"><div class="loading-spinner"></div>加载中...</div></div></div>
    </div>
    <script>
var CURRENT_SESSION='session_current';
var currentImage=null,currentFile=null;
var chatMessages,messageInput,previewContainer,previewImage,filePreviewContainer,sendBtn;

window.onload=function(){
    chatMessages=document.getElementById('chatMessages');
    messageInput=document.getElementById('messageInput');
    previewContainer=document.getElementById('previewContainer');
    previewImage=document.getElementById('previewImage');
    filePreviewContainer=document.getElementById('filePreviewContainer');
    sendBtn=document.getElementById('sendBtn');
    initMenu();
    loadChatHistory();
    setupInput();
};

function initMenu(){
    var items=document.querySelectorAll('.menu-item');
    for(var i=0;i<items.length;i++){
        items[i].onclick=function(){
            var page=this.getAttribute('data-page');
            var allItems=document.querySelectorAll('.menu-item');
            for(var j=0;j<allItems.length;j++)allItems[j].classList.remove('active');
            this.classList.add('active');
            var allPages=document.querySelectorAll('.page');
            for(var j=0;j<allPages.length;j++)allPages[j].classList.remove('active');
            document.getElementById('page-'+page).classList.add('active');
            if(page==='memory')loadMemory();
            else if(page==='skills')loadSkills();
            else if(page==='sessions')loadSessions();
            else if(page==='cron')loadCron();
            else if(page==='projects')loadProjects();
            else if(page==='costs')loadCosts();
            else if(page==='patterns')loadPatterns();
        };
    }
}

function createNewSession(){
    var now=new Date();
    var sessionName='session_'+now.toISOString().replace(/[:-]/g,'').split('.')[0].replace('T','_');
    CURRENT_SESSION=sessionName;
    chatMessages.innerHTML='';
    addMessage('✨ 新会话已创建！有什么可以帮你的吗？',false,null,false);
    updateSessionTitle();
}

function updateSessionTitle(){
    var title=CURRENT_SESSION.replace(/_/g,' ').replace('session ','');
    document.getElementById('currentSessionTitle').textContent='💬 '+title;
}

function switchSession(sessionId){
    CURRENT_SESSION=sessionId;
    loadChatHistory();
    updateSessionTitle();
    var allItems=document.querySelectorAll('.menu-item');
    for(var j=0;j<allItems.length;j++)allItems[j].classList.remove('active');
    allItems[0].classList.add('active');
    var allPages=document.querySelectorAll('.page');
    for(var j=0;j<allPages.length;j++)allPages[j].classList.remove('active');
    document.getElementById('page-chat').classList.add('active');
}

function setupInput(){
    messageInput.addEventListener('input',function(){this.style.height='auto';this.style.height=Math.min(this.scrollHeight,150)+'px';});
    messageInput.addEventListener('paste',function(e){
        var items=e.clipboardData.items;
        for(var i=0;i<items.length;i++){
            if(items[i].type.indexOf('image')!==-1){
                e.preventDefault();
                var blob=items[i].getAsFile();
                var reader=new FileReader();
                reader.onload=function(evt){currentImage=evt.target.result;showPreview(currentImage);};
                reader.readAsDataURL(blob);
                break;
            }
        }
    });
    messageInput.addEventListener('keydown',function(e){if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendMessage();}});
    document.getElementById('imageInput').addEventListener('change',handleImageSelect);
    document.getElementById('fileInput').addEventListener('change',handleFileSelect);
}

function showPreview(data){previewImage.src=data;previewContainer.classList.add('show');}
function removeImage(){currentImage=null;previewContainer.classList.remove('show');document.getElementById('imageInput').value='';}
function removeFile(){currentFile=null;filePreviewContainer.classList.remove('show');document.getElementById('fileInput').value='';}
function getFileIcon(name){var ext=name.split('.').pop().toLowerCase();var icons={pdf:'PDF',doc:'DOC',txt:'TXT',zip:'ZIP',jpg:'IMG',png:'IMG'};return icons[ext]||'FILE';}
function formatFileSize(bytes){if(bytes<1024)return bytes+' B';if(bytes<1048576)return (bytes/1024).toFixed(1)+' KB';return (bytes/1048576).toFixed(1)+' MB';}
function handleImageSelect(e){var file=e.target.files[0];if(file){var reader=new FileReader();reader.onload=function(evt){currentImage=evt.target.result;showPreview(currentImage);};reader.readAsDataURL(file);}}
function handleFileSelect(e){var file=e.target.files[0];if(file){currentFile=file;document.getElementById('filePreviewIcon').innerHTML=getFileIcon(file.name);document.getElementById('filePreviewName').textContent=file.name;document.getElementById('filePreviewSize').textContent=formatFileSize(file.size);filePreviewContainer.classList.add('show');}}

function loadChatHistory(){
    var sessionKey='hermes_chat_'+CURRENT_SESSION;
    try{
        var saved=localStorage.getItem(sessionKey);
        if(saved){
            var history=JSON.parse(saved);
            chatMessages.innerHTML='';
            for(var i=0;i<history.length;i++){
                var msg=history[i];
                var div=document.createElement('div');
                div.className='message '+(msg.isUser?'user':'assistant');
                // 用户消息保留换行，助手消息用 marked 渲染
                var renderedContent=msg.isUser?msg.content.split('\\n').join('<br>'):marked.parse(msg.content);
                var html='<div class="message-avatar">'+(msg.isUser?'👤':'🤖')+'</div><div class="message-content"><div class="message-text">'+renderedContent+'</div>';
                if(msg.imageData)html+='<img class="message-image" src="'+msg.imageData+'">';
                html+='</div>';
                div.innerHTML=html;
                if(msg.isUser){div.style.cursor='pointer';div.title='右键点击重新编辑';div.oncontextmenu=function(e){e.preventDefault();editMessage(this);};}
                chatMessages.appendChild(div);
            }
            chatMessages.scrollTop=chatMessages.scrollHeight;
        }else{
            chatMessages.innerHTML='';
            addMessage('👋 你好！我是 Hermes Agent，有什么可以帮你的吗？',false,null,false);
        }
    }catch(e){console.error('Load error:',e);}
}

function saveChatHistory(){
    var sessionKey='hermes_chat_'+CURRENT_SESSION;
    try{
        var msgs=[];
        var divs=chatMessages.querySelectorAll('.message');
        for(var i=0;i<divs.length;i++){
            var div=divs[i];
            var isUser=div.classList.contains('user');
            var textDiv=div.querySelector('.message-text');
            var content=textDiv?textDiv.textContent:'';
            var img=div.querySelector('.message-image');
            msgs.push({content:content,isUser:isUser,imageData:img?img.src:null});
        }
        if(msgs.length>100)msgs=msgs.slice(-100);
        localStorage.setItem(sessionKey,JSON.stringify(msgs));
    }catch(e){console.error('Save error:',e);}
}

function addMessage(content,isUser,imageData,save){
    if(save===undefined)save=true;
    var div=document.createElement('div');
    div.className='message '+(isUser?'user':'assistant');
    // 使用 marked 渲染 Markdown（包括换行）
    var renderedContent=isUser?content:marked.parse(content);
    var html='<div class="message-avatar">'+(isUser?'👤':'🤖')+'</div><div class="message-content"><div class="message-text">'+renderedContent+'</div>';
    if(imageData)html+='<img class="message-image" src="'+imageData+'">';
    html+='</div>';
    div.innerHTML=html;
    if(isUser){div.style.cursor='pointer';div.title='右键点击重新编辑';div.oncontextmenu=function(e){e.preventDefault();editMessage(this);};}
    chatMessages.appendChild(div);
    chatMessages.scrollTop=chatMessages.scrollHeight;
    if(save)saveChatHistory();
}

function editMessage(msgDiv){
    var textDiv=msgDiv.querySelector('.message-text');
    var content=textDiv?textDiv.textContent:'';
    if(confirm('确定要重新编辑这条消息吗？')){
        messageInput.value=content;
        messageInput.style.height='auto';
        messageInput.style.height=Math.min(messageInput.scrollHeight,150)+'px';
        messageInput.focus();
        msgDiv.remove();
        saveChatHistory();
    }
}

function typeMessage(content){
    var div=document.createElement('div');
    div.className='message assistant';
    var html='<div class="message-avatar">🤖</div><div class="message-content"><div class="message-text"></div></div>';
    div.innerHTML=html;
    chatMessages.appendChild(div);
    var textDiv=div.querySelector('.message-text');
    // 使用 marked 渲染 Markdown 内容（保留换行和格式）
    textDiv.innerHTML=marked.parse(content);
    chatMessages.scrollTop=chatMessages.scrollHeight;
    saveChatHistory();
}

function sendMessage(){
    var message=messageInput.value.trim();
    if(!message&&!currentImage&&!currentFile)return;
    sendBtn.disabled=true;
    var userMsg=message;
    var imgData=currentImage;
    if(currentImage)userMsg+=(userMsg?' [图片]':'[图片]');
    if(currentFile)userMsg+=(userMsg?' [文件:'+currentFile.name+']':'[文件:'+currentFile.name+']');
    addMessage(userMsg,true,imgData);
    messageInput.value='';
    messageInput.style.height='auto';
    var fileToSend=currentFile;
    var imageToSend=currentImage;
    removeImage();
    removeFile();
    var formData=new FormData();
    formData.append('message',message||'请分析');
    if(imageToSend){
        dataURLtoBlob(imageToSend).then(function(blob){
            formData.append('image',blob,'image.png');
            sendStreamRequest(formData,fileToSend);
        }).catch(function(err){
            console.error('Convert image error:',err);
            sendStreamRequest(formData,fileToSend);
        });
    }else{sendStreamRequest(formData,fileToSend);}
}

// 将 dataURL 或 URL 转换为 blob
function dataURLtoBlob(dataURL){
    return new Promise(function(resolve,reject){
        if(dataURL.startsWith('data:')){
            // base64 data URL
            var parts=dataURL.split(',');
            var mime=parts[0].match(/:(.*?);/)[1];
            var bstr=atob(parts[1]);
            var n=bstr.length;
            var u8arr=new Uint8Array(n);
            while(n--){u8arr[n]=bstr.charCodeAt(n);}
            resolve(new Blob([u8arr],{type:mime}));
        }else{
            // HTTP URL
            fetch(dataURL).then(function(r){return r.blob();}).then(resolve).catch(reject);
        }
    });
}

function sendRequest(formData,file){
    if(file)formData.append('file',file);
    fetch('/api/chat',{method:'POST',body:formData}).then(function(r){return r.json();}).then(function(data){
        removeLoading();
        typeMessage(data.response);
        sendBtn.disabled=false;
        messageInput.focus();
    }).catch(function(err){
        removeLoading();
        addMessage('发送失败：'+err.message,false,null);
        sendBtn.disabled=false;
    });
}

function sendStreamRequest(formData,file){
    if(file)formData.append('file',file);
    showLoading(); // 显示打字动画
    var buffer='';
    var assistantDiv=null;
    var textDiv=null;
    
    var xhr=new XMLHttpRequest();
    xhr.open('POST','/api/chat_stream',true);
    
    var position=0;
    xhr.onprogress=function(){
        // 移除加载动画，创建消息框（第一次收到数据时）
        if(!assistantDiv){
            removeLoading();
            assistantDiv=createAssistantMessage();
            textDiv=assistantDiv.querySelector('.message-text');
        }
        
        var text=xhr.responseText.substring(position);
        position=xhr.responseText.length;
        buffer+=text;
        
        // 按 SSE 协议格式解析：每行以 data: 开头
        var lines=buffer.split('\n');
        buffer=lines.pop()||'';
        
        for(var i=0;i<lines.length;i++){
            var line=lines[i].trim();
            if(line.startsWith('data: ')){
                var data=line.substring(6);
                if(data==='[DONE]'){
                    sendBtn.disabled=false;
                    messageInput.focus();
                    saveChatHistory();
                    return;
                }
                // 保留换行符，让 marked 正确解析 Markdown
                if(textDiv.textContent.length>0 && !textDiv.textContent.endsWith('\n')){
                    textDiv.textContent+='\n';
                }
                textDiv.textContent+=data;
                // 实时渲染 Markdown
                textDiv.innerHTML=marked.parse(textDiv.textContent);
                chatMessages.scrollTop=chatMessages.scrollHeight;
            }
        }
    };
    
    xhr.onload=function(){
        if(xhr.status!==200){
            if(textDiv) textDiv.textContent+='\n[发送失败]';
        }
        sendBtn.disabled=false;
        messageInput.focus();
        saveChatHistory();
    };
    
    xhr.onerror=function(){
        if(textDiv) textDiv.textContent+='\n[网络错误]';
        sendBtn.disabled=false;
        messageInput.focus();
    };
    
    xhr.send(formData);
}

// 打字机效果显示文本
function typeText(text, textDiv){
    var chars=text.split('');
    var index=0;
    function type(){
        if(index<chars.length){
            textDiv.textContent+=chars[index];
            index++;
            chatMessages.scrollTop=chatMessages.scrollHeight;
            setTimeout(type, 10+Math.random()*20); // 随机打字速度
        }
    }
    type();
}

function createAssistantMessage(){
    var div=document.createElement('div');
    div.className='message assistant';
    var html='<div class="message-avatar">🤖</div><div class="message-content"><div class="message-text"></div></div>';
    div.innerHTML=html;
    chatMessages.appendChild(div);
    chatMessages.scrollTop=chatMessages.scrollHeight;
    return div;
}

function showLoading(){
    var div=document.createElement('div');
    div.className='message assistant';
    div.id='loadingMsg';
    div.innerHTML='<div class="message-avatar">🤖</div><div class="message-content"><div class="typing-indicator"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div></div>';
    chatMessages.appendChild(div);
    chatMessages.scrollTop=chatMessages.scrollHeight;
}

function removeLoading(){var div=document.getElementById('loadingMsg');if(div)div.remove();}
function clearChatHistory(){if(confirm('确定清空当前对话？')){var sessionKey='hermes_chat_'+CURRENT_SESSION;localStorage.removeItem(sessionKey);chatMessages.innerHTML='';addMessage('对话已清空',false,null,false);}}

// 存储原始数据用于筛选
var allSessionsData=[];
var allMemoryData=[];

function loadMemory(){
    renderList.currentPage='memory';
    fetch('/api/memory').then(function(r){return r.json();}).then(function(data){
        allMemoryData=data;
        renderList(data);
    });
}
function loadSessions(){
    renderList.currentPage='sessions';
    fetch('/api/sessions').then(function(r){return r.json();}).then(function(data){
        allSessionsData=data;
        renderList(data);
    });
}
function filterSessions(){
    var days=document.getElementById('sessionDateFilter').value;
    if(days==='all'){renderList(allSessionsData);return;}
    var cutoff=new Date();
    cutoff.setDate(cutoff.getDate()-parseInt(days));
    var filtered={sessions:allSessionsData.sessions.filter(function(s){
        var d=new Date(s.created||'');
        return d>=cutoff;
    })};
    renderList(filtered);
}
function filterMemory(){
    var days=document.getElementById('memoryDateFilter').value;
    if(days==='all'){renderList(allMemoryData);return;}
    var cutoff=new Date();
    cutoff.setDate(cutoff.getDate()-parseInt(days));
    var filtered={daily:allMemoryData.daily.filter(function(item){
        var match=item.match(/^> (\\d{4}-\\d{2}-\\d{2})/);
        if(!match)return false;
        var d=new Date(match[1]);
        return d>=cutoff;
    }),long_term:allMemoryData.long_term,file_path:allMemoryData.file_path};
    renderList(filtered);
}
function loadSkills(){renderList.currentPage='skills';fetch('/api/skills').then(function(r){return r.json();}).then(renderList);}
function loadCron(){renderRaw.currentPage='cron';fetch('/api/cron').then(function(r){return r.json();}).then(renderRaw);}
function loadProjects(){renderList.currentPage='projects';fetch('/api/projects').then(function(r){return r.json();}).then(renderList);}
function loadCosts(){renderStats.currentPage='costs';fetch('/api/costs').then(function(r){return r.json();}).then(renderStats);}
function loadPatterns(){renderStats.currentPage='patterns';fetch('/api/patterns').then(function(r){return r.json();}).then(renderStats);}
function renderList(data){
    var html='<div class="card"><ul class="data-list">';
    if(data.skills){
        // 按分类分组
        var byCategory={};
        for(var i=0;i<data.skills.length;i++){
            var s=data.skills[i];
            var cat=s.category||'其他';
            if(!byCategory[cat])byCategory[cat]=[];
            byCategory[cat].push(s);
        }
        // 排序分类
        var categories=Object.keys(byCategory).sort();
        for(var j=0;j<categories.length;j++){
            var cat=categories[j];
            html+='<li style="background:rgba(0,217,255,0.15);border-left-color:#00ff88;"><strong style="color:#00ff88;">📁 '+cat+' ('+byCategory[cat].length+')</strong></li>';
            for(var i=0;i<byCategory[cat].length;i++){
                var s=byCategory[cat][i];
                var badge=s.source==='local'?'<span style="background:#00d9ff;color:#0f0f1a;padding:2px 6px;border-radius:4px;font-size:11px;margin-left:8px;">本地</span>':'';
                html+='<li style="padding:8px 15px;"><code style="background:#0f0f1a;padding:4px 8px;border-radius:4px;color:#00d9ff;">'+s.name+'</code>'+badge+'</li>';
            }
        }
    }
    else if(data.sessions){
        for(var i=0;i<data.sessions.length;i++){
            var s=data.sessions[i];
            html+='<li class="session-item" data-session-id="'+s.id+'" data-session-title="'+(s.title||'未命名').replace(/"/g,'&quot;')+'" style="cursor:pointer;">';
            html+='<strong>'+(s.title||'未命名')+'</strong><br>';
            html+='<small>'+(s.created||'')+' | '+s.messages+'条</small>';
            html+='</li>';
        }
    }
    else if(data.projects||data.daily){
        var items=data.projects||data.daily;
        if(items && items.length>0){
            for(var i=0;i<items.length;i++)html+='<li>'+items[i]+'</li>';
        }else{
            html+='<li style="color:#666;text-align:center;padding:20px;">暂无数据</li>';
        }
    }
    else if(data.skills!==undefined && data.skills.length===0){
        html+='<li style="color:#666;text-align:center;padding:20px;">暂无技能数据</li>';
    }
    else if(data.sessions!==undefined && data.sessions.length===0){
        html+='<li style="color:#666;text-align:center;padding:20px;">暂无会话数据</li>';
    }
    else{html+='<li>暂无数据</li>';}
    html+='</ul></div>';
    var page=renderList.currentPage||'memory';
    var contentDiv=document.getElementById(page+'-content');
    contentDiv.innerHTML=html;
    // 绑定会话点击事件
    if(data.sessions){
        var items=contentDiv.querySelectorAll('.session-item');
        for(var i=0;i<items.length;i++){
            items[i].onclick=function(){
                var sessionId=this.getAttribute('data-session-id');
                var sessionTitle=this.getAttribute('data-session-title');
                openSession(sessionId,sessionTitle);
            };
        }
    }
}

function openSession(sessionId,sessionTitle){
    CURRENT_SESSION=sessionId;
    updateSessionTitle();
    loadSessionDetail();
    // 切换到聊天页面
    var allItems=document.querySelectorAll('.menu-item');
    for(var j=0;j<allItems.length;j++)allItems[j].classList.remove('active');
    allItems[0].classList.add('active');
    var allPages=document.querySelectorAll('.page');
    for(var j=0;j<allPages.length;j++)allPages[j].classList.remove('active');
    document.getElementById('page-chat').classList.add('active');
}

function loadSessionDetail(){
    var sessionKey='hermes_chat_'+CURRENT_SESSION;
    // 先尝试从 localStorage 加载
    var saved=localStorage.getItem(sessionKey);
    if(saved){
        var history=JSON.parse(saved);
        renderChatHistory(history);
        return;
    }
    // 从服务器加载历史会话
    fetch('/api/session_detail?session_id='+encodeURIComponent(CURRENT_SESSION))
        .then(function(r){return r.json();})
        .then(function(data){
            if(data.messages && data.messages.length>0){
                renderChatHistory(data.messages);
                // 保存到 localStorage
                localStorage.setItem(sessionKey,JSON.stringify(data.messages));
            }else{
                chatMessages.innerHTML='';
                addMessage('👋 你好！我是 Hermes Agent，有什么可以帮你的吗？',false,null,false);
            }
        })
        .catch(function(e){
            console.error('Load session detail error:',e);
            chatMessages.innerHTML='';
            addMessage('👋 你好！我是 Hermes Agent，有什么可以帮你的吗？',false,null,false);
        });
}

function renderChatHistory(history){
    chatMessages.innerHTML='';
    for(var i=0;i<history.length;i++){
        var msg=history[i];
        var div=document.createElement('div');
        div.className='message '+(msg.isUser?'user':'assistant');
        // 用户消息保留换行，助手消息用 marked 渲染
        var renderedContent=msg.isUser?msg.content.split('\\n').join('<br>'):marked.parse(msg.content);
        var html='<div class="message-avatar">'+(msg.isUser?'👤':'🤖')+'</div><div class="message-content"><div class="message-text">'+renderedContent+'</div>';
        if(msg.imageData)html+='<img class="message-image" src="'+msg.imageData+'">';
        html+='</div>';
        div.innerHTML=html;
        if(msg.isUser){div.style.cursor='pointer';div.title='右键点击重新编辑';div.oncontextmenu=function(e){e.preventDefault();editMessage(this);};}
        chatMessages.appendChild(div);
    }
    chatMessages.scrollTop=chatMessages.scrollHeight;
}

function renderRaw(data){
    var html='<div class="card"><pre style="background:#0f0f1a;padding:15px;border-radius:8px;white-space:pre-wrap;">'+(data.raw||'暂无数据')+'</pre></div>';
    var page=renderRaw.currentPage||'cron';
    document.getElementById(page+'-content').innerHTML=html;
}

function renderStats(data){
    var html='<div class="stats-grid">';
    if(data.sessions!==undefined)html+='<div class="stat-card"><div class="stat-value">'+data.sessions+'</div><div class="stat-label">会话数</div></div>';
    if(data.total_tokens!==undefined)html+='<div class="stat-card"><div class="stat-value">'+data.total_tokens+'</div><div class="stat-label">Token</div></div>';
    if(data.estimated_cost)html+='<div class="stat-card"><div class="stat-value">'+data.estimated_cost+'</div><div class="stat-label">费用</div></div>';
    if(data.peak_hour)html+='<div class="stat-card"><div class="stat-value">'+data.peak_hour+':00</div><div class="stat-label">高峰时段</div></div>';
    html+='</div>';
    var page=renderStats.currentPage||'costs';
    document.getElementById(page+'-content').innerHTML=html;
}
    </script>
</body>
</html>'''

if __name__ == "__main__":
    port = 8888
    if len(sys.argv) > 1:
        try: port = int(sys.argv[1])
        except: pass
    
    # 确保 PATH 包含常见安装路径
    if platform.system() == "Windows":
        extra_paths = [
            str(Path.home() / ".local" / "bin"),
            r"C:\Program Files\Hermes",
            r"C:\Users\Public\Hermes",
        ]
    else:
        extra_paths = [
            str(Path.home() / ".local" / "bin"),
            "/opt/homebrew/bin",
            "/usr/local/bin",
        ]
    
    current_path = os.environ.get("PATH", "")
    new_path = os.pathsep.join(extra_paths + [current_path])
    os.environ["PATH"] = new_path
    
    print("\n" + "="*50 + "\n Hermes Agent Web Chat\n" + "="*50 + f"\n Access: http://localhost:{port}\n" + "="*50 + "\n")
    uvicorn.run(app, host="127.0.0.1", port=port)
