"""
Hermes Agent Web Chat - Fixed Version
"""
from fastapi import FastAPI, Form, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from pathlib import Path
import subprocess, tempfile, os, json, glob, sys
from typing import Optional
import uvicorn
from datetime import datetime

app = FastAPI()
HERMES_HOME = Path.home() / ".Hermes"
UPLOAD_DIR = HERMES_HOME / "web-chat" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

def get_memory_data():
    memory_file = HERMES_HOME / "MEMORY.md"
    if not memory_file.exists(): return {"daily": [], "long_term": []}
    content = memory_file.read_text()
    daily, long_term, current = [], [], []
    for line in content.split('\n'):
        if line.startswith('> 2026-') or line.startswith('> 2025-'):
            if current: daily.append('\n'.join(current))
            current = [line]
        elif line.strip() and current: current.append(line)
        elif line.startswith('§'):
            if current: daily.append('\n'.join(current))
            current = []
    if current: daily.append('\n'.join(current))
    return {"daily": daily[-20:], "long_term": long_term[:20]}

def get_skills_data():
    try:
        result = subprocess.run(["hermes", "skills", "list"], capture_output=True, text=True, timeout=30, env={**os.environ, "HERMES_HOME": str(HERMES_HOME)})
        skills = []
        for line in result.stdout.strip().split('\n'):
            if line.strip() and '|' in line:
                parts = [p.strip() for p in line.split('|') if p.strip()]
                if len(parts) >= 2: skills.append({"name": parts[0], "category": parts[1], "description": parts[2] if len(parts) > 2 else ""})
        return {"skills": skills, "count": len(skills)}
    except: return {"skills": [], "count": 0}

def get_sessions_data():
    sessions_dir = HERMES_HOME / "sessions"
    if not sessions_dir.exists(): return {"sessions": []}
    sessions = []
    for fp in sorted(glob.glob(str(sessions_dir / "*.json")), reverse=True)[:50]:
        try:
            with open(fp, 'r', encoding='utf-8') as f: data = json.load(f)
            preview = next((m.get("content","")[:100] for m in data.get("messages",[])[:3] if m.get("role")=="user"), "")
            sessions.append({"id": Path(fp).stem, "title": data.get("title",""), "created": data.get("created_at",""), "messages": len(data.get("messages",[])), "preview": preview})
        except: continue
    return {"sessions": sessions, "count": len(sessions)}

def get_cron_data():
    try:
        result = subprocess.run(["hermes", "cronjob", "list"], capture_output=True, text=True, timeout=30, env={**os.environ, "HERMES_HOME": str(HERMES_HOME)})
        return {"raw": result.stdout}
    except: return {"raw": ""}

def get_projects_data():
    memory_file = HERMES_HOME / "MEMORY.md"
    projects = [line.strip() for line in memory_file.read_text().split('\n') if '项目' in line] if memory_file.exists() else []
    return {"projects": projects or ["项目 1", "项目 2"], "count": len(projects)}

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

def call_hermes(message: str, image_path: Optional[str] = None) -> str:
    try:
        cmd = ["hermes", "chat", "-q", message or "你好", "-Q", "--source", "web"]
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
    if image:
        tp = tempfile.mktemp(suffix=".png", dir=str(UPLOAD_DIR))
        with open(tp, "wb") as f: f.write(await image.read())
        image_path = tp
    if file:
        tp = tempfile.mktemp(suffix=f"_{file.filename}", dir=str(UPLOAD_DIR))
        with open(tp, "wb") as f: f.write(await file.read())
        file_path = tp
    msg = f"{message}\n\n[文件：{file.filename}]" if file and file.filename else message
    response = call_hermes(msg or "请分析", image_path)
    for p in [image_path, file_path]:
        if p and os.path.exists(p): os.remove(p)
    return JSONResponse(content={"response": response})

@app.get("/api/memory")
async def api_memory(): return JSONResponse(content=get_memory_data())

@app.get("/api/skills")
async def api_skills(): return JSONResponse(content=get_skills_data())

@app.get("/api/sessions")
async def api_sessions(): return JSONResponse(content=get_sessions_data())

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
    <title>Hermes Agent</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%); min-height: 100vh; display: flex; color: #e8e8e8; }
        .sidebar { width: 260px; background: linear-gradient(180deg, #0a0a1a 0%, #1a1a2e 100%); border-right: 1px solid #1f3a5f; padding: 20px 0; flex-shrink: 0; display: flex; flex-direction: column; }
        .logo { text-align: center; padding: 20px; border-bottom: 1px solid #1f3a5f; margin-bottom: 20px; }
        .logo h1 { font-size: 24px; background: linear-gradient(135deg, #00d9ff 0%, #00ff88 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .logo p { color: #666; font-size: 12px; margin-top: 5px; }
        .menu { list-style: none; padding: 0 10px; flex: 1; }
        .menu-item { padding: 12px 16px; margin: 4px 0; border-radius: 8px; cursor: pointer; transition: all 0.2s ease; color: #888; display: flex; align-items: center; gap: 12px; font-size: 14px; }
        .menu-item:hover { background: rgba(0, 217, 255, 0.1); color: #00d9ff; }
        .menu-item.active { background: linear-gradient(135deg, #00d9ff 0%, #0099ff 100%); color: white; box-shadow: 0 4px 15px rgba(0, 217, 255, 0.3); }
        .main { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
        .page { display: none; height: 100vh; flex-direction: column; }
        .page.active { display: flex; }
        .page-header { padding: 20px 30px; border-bottom: 1px solid #1f3a5f; background: rgba(15, 15, 26, 0.8); }
        .page-header h2 { font-size: 24px; color: #00d9ff; }
        .chat-messages { flex: 1; overflow-y: auto; padding: 30px; display: flex; flex-direction: column; gap: 20px; }
        .message { display: flex; gap: 15px; max-width: 80%; }
        .message.user { align-self: flex-end; flex-direction: row-reverse; }
        .message-avatar { width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 20px; flex-shrink: 0; background: #00d9ff; }
        .message-content { background: #1a1a2e; padding: 15px 20px; border-radius: 16px; border: 1px solid #2a2a4e; }
        .message.user .message-content { background: linear-gradient(135deg, #1f3a5f 0%, #2a4a6f 100%); }
        .message-text { color: #e8e8e8; line-height: 1.6; font-size: 15px; white-space: pre-wrap; }
        .message-image { max-width: 300px; border-radius: 10px; margin-top: 10px; border: 2px solid #2a2a4e; }
        .input-container { padding: 20px 30px; background: rgba(15, 15, 26, 0.95); border-top: 1px solid #1f3a5f; }
        .input-wrapper { display: flex; gap: 15px; align-items: flex-end; background: #1a1a2e; border: 2px solid #2a2a4e; border-radius: 24px; padding: 8px 8px 8px 20px; }
        .input-wrapper:focus-within { border-color: #00d9ff; box-shadow: 0 0 20px rgba(0, 217, 255, 0.2); }
        #messageInput { flex: 1; background: transparent; border: none; outline: none; color: #e8e8e8; font-size: 15px; padding: 10px 0; resize: none; max-height: 150px; font-family: inherit; }
        #messageInput::placeholder { color: #666; }
        .input-actions { display: flex; gap: 8px; padding-right: 8px; }
        .action-btn { width: 44px; height: 44px; border-radius: 50%; border: none; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 20px; background: #2a2a4e; color: #888; }
        .action-btn:hover { background: #3a3a5e; color: #00d9ff; }
        #sendBtn { background: linear-gradient(135deg, #00d9ff 0%, #0099ff 100%); color: white; }
        #sendBtn:hover { transform: scale(1.05); }
        #sendBtn:disabled { opacity: 0.5; cursor: not-allowed; }
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
        .refresh-btn { background: #2a2a4e; color: #00d9ff; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer; }
        .clear-btn { width: 100%; padding: 10px; background: #2a2a4e; color: #ff6b6b; border: none; border-radius: 8px; cursor: pointer; margin-top: 10px; }
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: #1a1a2e; }
        ::-webkit-scrollbar-thumb { background: #2a2a4e; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="sidebar">
        <div class="logo"><h1>Hermes Agent</h1><p>AI 智能助手</p></div>
        <ul class="menu">
            <li class="menu-item active" data-page="chat">聊天对话</li>
            <li class="menu-item" data-page="memory">记忆管理</li>
            <li class="menu-item" data-page="skills">技能列表</li>
            <li class="menu-item" data-page="sessions">会话历史</li>
            <li class="menu-item" data-page="cron">定时任务</li>
            <li class="menu-item" data-page="projects">项目跟踪</li>
            <li class="menu-item" data-page="costs">费用统计</li>
            <li class="menu-item" data-page="patterns">使用模式</li>
        </ul>
        <div style="padding:10px; border-top:1px solid #1f3a5f;"><button class="clear-btn" onclick="clearChatHistory()">清空对话</button></div>
    </div>
    <div class="main">
        <div id="page-chat" class="page active">
            <div class="chat-messages" id="chatMessages"></div>
            <div class="preview-container" id="previewContainer"><img class="preview-image" id="previewImage" src=""><button class="preview-remove" onclick="removeImage()">X</button></div>
            <div class="file-preview-container" id="filePreviewContainer"><div style="display:flex;align-items:center;gap:10px;"><span id="filePreviewIcon" style="font-size:24px;"></span><div><div id="filePreviewName" style="color:#e8e8e8;font-size:14px;"></div><div id="filePreviewSize" style="color:#666;font-size:12px;"></div></div><button class="file-preview-remove" onclick="removeFile()">X</button></div></div>
            <div class="input-container">
                <div class="input-wrapper">
                    <textarea id="messageInput" placeholder="输入消息... (支持粘贴图片 Ctrl+V/Cmd+V)" rows="1"></textarea>
                    <input type="file" id="imageInput" accept="image/*">
                    <input type="file" id="fileInput">
                    <div class="input-actions">
                        <button class="action-btn" onclick="document.getElementById('imageInput').click()">Img</button>
                        <button class="action-btn" onclick="document.getElementById('fileInput').click()">File</button>
                        <button class="action-btn" id="sendBtn" onclick="sendMessage()">Send</button>
                    </div>
                </div>
            </div>
        </div>
        <div id="page-memory" class="page"><div class="page-header"><h2>记忆管理 <button class="refresh-btn" onclick="loadMemory()">刷新</button></h2></div><div class="chat-messages" id="memory-content"><div class="loading"><div class="loading-spinner"></div>加载中...</div></div></div>
        <div id="page-skills" class="page"><div class="page-header"><h2>技能列表 <button class="refresh-btn" onclick="loadSkills()">刷新</button></h2></div><div class="chat-messages" id="skills-content"><div class="loading"><div class="loading-spinner"></div>加载中...</div></div></div>
        <div id="page-sessions" class="page"><div class="page-header"><h2>会话历史 <button class="refresh-btn" onclick="loadSessions()">刷新</button></h2></div><div class="chat-messages" id="sessions-content"><div class="loading"><div class="loading-spinner"></div>加载中...</div></div></div>
        <div id="page-cron" class="page"><div class="page-header"><h2>定时任务 <button class="refresh-btn" onclick="loadCron()">刷新</button></h2></div><div class="chat-messages" id="cron-content"><div class="loading"><div class="loading-spinner"></div>加载中...</div></div></div>
        <div id="page-projects" class="page"><div class="page-header"><h2>项目跟踪 <button class="refresh-btn" onclick="loadProjects()">刷新</button></h2></div><div class="chat-messages" id="projects-content"><div class="loading"><div class="loading-spinner"></div>加载中...</div></div></div>
        <div id="page-costs" class="page"><div class="page-header"><h2>费用统计 <button class="refresh-btn" onclick="loadCosts()">刷新</button></h2></div><div class="chat-messages" id="costs-content"><div class="loading"><div class="loading-spinner"></div>加载中...</div></div></div>
        <div id="page-patterns" class="page"><div class="page-header"><h2>使用模式 <button class="refresh-btn" onclick="loadPatterns()">刷新</button></h2></div><div class="chat-messages" id="patterns-content"><div class="loading"><div class="loading-spinner"></div>加载中...</div></div></div>
    </div>
    <script>
var CHAT_KEY='hermes_chat_v1';
var currentImage=null,currentFile=null,chatMessages,messageInput,previewContainer,previewImage,filePreviewContainer,sendBtn;
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
    try{
        var saved=localStorage.getItem(CHAT_KEY);
        if(saved){
            var history=JSON.parse(saved);
            for(var i=0;i<history.length;i++){
                var msg=history[i];
                var div=document.createElement('div');
                div.className='message '+(msg.isUser?'user':'assistant');
                var html='<div class="message-avatar">'+(msg.isUser?'U':'AI')+'</div><div class="message-content"><div class="message-text">'+msg.content+'</div>';
                if(msg.imageData)html+='<img class="message-image" src="'+msg.imageData+'">';
                html+='</div>';
                div.innerHTML=html;
                chatMessages.appendChild(div);
            }
            chatMessages.scrollTop=chatMessages.scrollHeight;
        }else{addMessage('你好！我是 Hermes Agent，有什么可以帮你的吗？',false,null,false);}
    }catch(e){console.error('Load error:',e);}
}
function saveChatHistory(){
    try{
        var msgs=[];
        var divs=chatMessages.querySelectorAll('.message');
        for(var i=0;i<divs.length;i++){
            var div=divs[i];
            var isUser=div.classList.contains('user');
            var content=div.querySelector('.message-text').textContent;
            var img=div.querySelector('.message-image');
            msgs.push({content:content,isUser:isUser,imageData:img?img.src:null});
        }
        if(msgs.length>50)msgs=msgs.slice(-50);
        localStorage.setItem(CHAT_KEY,JSON.stringify(msgs));
    }catch(e){console.error('Save error:',e);}
}
function addMessage(content,isUser,imageData,save){
    if(save===undefined)save=true;
    var div=document.createElement('div');
    div.className='message '+(isUser?'user':'assistant');
    var html='<div class="message-avatar">'+(isUser?'U':'AI')+'</div><div class="message-content"><div class="message-text">'+content+'</div>';
    if(imageData)html+='<img class="message-image" src="'+imageData+'">';
    html+='</div>';
    div.innerHTML=html;
    chatMessages.appendChild(div);
    chatMessages.scrollTop=chatMessages.scrollHeight;
    if(save)saveChatHistory();
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
    removeImage();
    removeFile();
    showLoading();
    var formData=new FormData();
    formData.append('message',message||'请分析');
    if(currentImage){
        fetch(currentImage).then(function(r){return r.blob();}).then(function(blob){
            formData.append('image',blob,'image.png');
            sendRequest(formData,fileToSend);
        });
    }else{sendRequest(formData,fileToSend);}
}
function sendRequest(formData,file){
    if(file)formData.append('file',file);
    fetch('/api/chat',{method:'POST',body:formData}).then(function(r){return r.json();}).then(function(data){
        removeLoading();
        addMessage(data.response,false,null);
        sendBtn.disabled=false;
        messageInput.focus();
    }).catch(function(err){
        removeLoading();
        addMessage('发送失败：'+err.message,false,null);
        sendBtn.disabled=false;
    });
}
function showLoading(){
    var div=document.createElement('div');
    div.className='message assistant';
    div.id='loadingMsg';
    div.innerHTML='<div class="message-avatar">AI</div><div class="message-content"><div class="typing-indicator"><div class="typing-dot" style="width:8px;height:8px;border-radius:50%;background:#00d9ff;display:inline-block;margin:0 2px;"></div><div class="typing-dot" style="width:8px;height:8px;border-radius:50%;background:#00d9ff;display:inline-block;margin:0 2px;"></div><div class="typing-dot" style="width:8px;height:8px;border-radius:50%;background:#00d9ff;display:inline-block;margin:0 2px;"></div></div></div>';
    chatMessages.appendChild(div);
    chatMessages.scrollTop=chatMessages.scrollHeight;
}
function removeLoading(){var div=document.getElementById('loadingMsg');if(div)div.remove();}
function clearChatHistory(){if(confirm('确定清空所有聊天记录？')){localStorage.removeItem(CHAT_KEY);chatMessages.innerHTML='';addMessage('对话已清空',false,null,false);}}
function loadMemory(){renderMemory.currentPage="memory";fetch('/api/memory').then(function(r){return r.json();}).then(renderList);}
function loadSkills(){renderSkills.currentPage="skills";fetch('/api/skills').then(function(r){return r.json();}).then(renderList);}
function loadSessions(){renderSessions.currentPage="sessions";fetch('/api/sessions').then(function(r){return r.json();}).then(renderList);}
function loadCron(){renderCron.currentPage="cron";fetch('/api/cron').then(function(r){return r.json();}).then(renderRaw);}
function loadProjects(){renderProjects.currentPage="projects";fetch('/api/projects').then(function(r){return r.json();}).then(renderList);}
function loadCosts(){renderCosts.currentPage="costs";fetch('/api/costs').then(function(r){return r.json();}).then(renderStats);}
function loadPatterns(){renderPatterns.currentPage="patterns";fetch('/api/patterns').then(function(r){return r.json();}).then(renderStats);}
function renderList(data){
    var html='<div class="card"><ul class="data-list">';
    if(data.skills){for(var i=0;i<data.skills.length;i++){var s=data.skills[i];html+='<li><strong>'+s.name+'</strong> <span style="color:#00d9ff;">'+s.category+'</span><br><small>'+(s.description||'')+'</small></li>';}}
    else if(data.sessions){for(var i=0;i<data.sessions.length;i++){var s=data.sessions[i];html+='<li><strong>'+(s.title||'未命名')+'</strong><br><small>'+(s.created||'')+' | '+s.messages+'条消息</small></li>';}}
    else if(data.projects||data.daily){var items=data.projects||data.daily;for(var i=0;i<items.length;i++)html+='<li>'+items[i]+'</li>';}
    else{html+='<li>暂无数据</li>';}
    html+='</ul></div>';
    var page=renderList.currentPage||'memory';
    document.getElementById(page+'-content').innerHTML=html;
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
    print("\n" + "="*50 + "\n Hermes Agent Web Chat\n" + "="*50 + "\n Access: http://localhost:" + str(port) + "\n" + "="*50 + "\n")
    uvicorn.run(app, host="127.0.0.1", port=port)
