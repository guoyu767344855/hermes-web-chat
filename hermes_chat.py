"""
Hermes Agent Web Chat - 跨平台版本 (Windows/Mac/Linux)
"""
from fastapi import FastAPI, Form, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pathlib import Path
import subprocess, tempfile, os, json, glob, sys, shutil, platform, time
from typing import Optional, Generator
import uvicorn
from datetime import datetime
import base64
import httpx
import asyncio
import logging

# ── 日志配置 ──
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)

# ── 配置文件支持 ──
CONFIG_FILE = Path(__file__).parent / "hermes_chat_config.json"
DEFAULT_CONFIG = {
    "port": 8888,
    "max_file_size": 10 * 1024 * 1024,  # 10MB
    "allowed_origins": ["*"],
}

def load_config() -> dict:
    """加载配置文件，不存在则使用默认值"""
    config = DEFAULT_CONFIG.copy()
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
            config.update(user_config)
            logger.info("已加载配置文件: %s", CONFIG_FILE)
        except Exception as e:
            logger.warning("配置文件加载失败 (%s)，使用默认值", e)
    return config

CONFIG = load_config()
MAX_FILE_SIZE = CONFIG.get("max_file_size", 10 * 1024 * 1024)

# ── 启动时间 (用于健康检查) ──
START_TIME = time.time()

app = FastAPI()

# TikHub API 配置（备用）
# TIKHUB_API_KEY="qbUzWv...AQ=="
# TIKHUB_API_URL = "https://api.tikhub.io/v1/chat/completions"


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
        logger.error("Skills error: %s", e)
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
    """费用统计 - 优先使用 session JSON 中的 usage 字段"""
    sessions_dir = HERMES_HOME / "sessions"
    total_tokens = 0
    model_counts = {}
    has_real_usage = False
    total_input_tokens = 0
    total_output_tokens = 0

    if sessions_dir.exists():
        for fp in glob.glob(str(sessions_dir / "*.json")):
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                model = data.get("model", "unknown")
                model_counts[model] = model_counts.get(model, 0) + 1

                # 尝试读取真实 usage 数据
                usage = data.get("usage")
                if usage and isinstance(usage, dict):
                    has_real_usage = True
                    total_input_tokens += usage.get("prompt_tokens", 0) or usage.get("input_tokens", 0)
                    total_output_tokens += usage.get("completion_tokens", 0) or usage.get("output_tokens", 0)
                    total_tokens += usage.get("total_tokens", 0)
                else:
                    # 回退：基于字符数估算
                    for m in data.get("messages", []):
                        total_tokens += len(m.get("content", "")) // 4
            except:
                continue

    # 估算费用：如果没有真实 usage 数据则标注
    if has_real_usage:
        total = total_input_tokens + total_output_tokens
        estimated_cost = f"${total / 1_000_000 * 2:.2f}"
        cost_note = "基于真实 token 用量估算"
    else:
        estimated_cost = f"${total_tokens / 1_000_000 * 2:.2f}"
        cost_note = "N/A (仅基于字符数估算)"

    return {
        "total_tokens": total_tokens,
        "input_tokens": total_input_tokens if has_real_usage else None,
        "output_tokens": total_output_tokens if has_real_usage else None,
        "sessions": sum(model_counts.values()),
        "models": model_counts,
        "estimated_cost": estimated_cost,
        "cost_note": cost_note,
    }

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


# ── 过滤函数 (消除 call_hermes 和 call_hermes_stream 中的重复) ──
def should_filter_line(line: str) -> bool:
    """判断一行输出是否应该被过滤掉"""
    if not line.strip():
        return True
    if line.startswith(('session_id:', 'Query:', 'Initializing', '|', 'Hermes Agent', '===', '---', 'Tools:', 'Available Skills:')):
        return True
    if 'upstream' in line:
        return True
    return False


def call_hermes_stream(message: str, image_path: Optional[str] = None) -> Generator[str, None, None]:
    """流式调用 hermes，实时返回输出（仅回复内容，不含思考过程）"""
    try:
        hermes_cmd = get_hermes_cmd()
        if not hermes_cmd:
            yield "错误：找不到 hermes 命令，请确认已正确安装\n"
            return

        # 使用 -Q 参数获取纯净回复（过滤终端输出和思考过程）
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

        # 实时读取输出，使用提取的过滤函数
        has_output = False

        for line in process.stdout:
            line = line.rstrip('\n\r')

            if should_filter_line(line):
                continue

            # 输出行
            yield line
            has_output = True

        # 如果没有任何输出，返回提示
        if not has_output:
            yield "没有收到回复\n"

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
        # 使用 -q 和 -Q 参数获取纯净回复
        cmd = [hermes_cmd, "chat", "-q", message or "你好", "-Q", "--source", "web"]
        if image_path: cmd.extend(["--image", image_path])
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, env={**os.environ, "HERMES_HOME": str(HERMES_HOME)})
        # 使用提取的过滤函数
        lines = []
        for line in (result.stdout or '').split('\n'):
            line = line.rstrip('\n\r')
            if should_filter_line(line):
                continue
            lines.append(line)
        return '\n'.join(lines) or result.stderr.strip() or "没有回复"
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
            # 文件大小检查
            if len(content) > MAX_FILE_SIZE:
                logger.warning("图片文件过大: %d bytes (限制: %d)", len(content), MAX_FILE_SIZE)
                return JSONResponse(status_code=413, content={"response": f"文件过大，最大允许 {MAX_FILE_SIZE // (1024*1024)}MB"})
            logger.debug("Received image: %s, size: %d bytes", image.filename, len(content))
            tp = tempfile.mktemp(suffix=".png", dir=str(UPLOAD_DIR))
            with open(tp, "wb") as f: f.write(content)
            image_path = tp
            logger.debug("Image saved to: %s", image_path)
        if file:
            content = await file.read()
            # 文件大小检查
            if len(content) > MAX_FILE_SIZE:
                logger.warning("文件过大: %d bytes (限制: %d)", len(content), MAX_FILE_SIZE)
                return JSONResponse(status_code=413, content={"response": f"文件过大，最大允许 {MAX_FILE_SIZE // (1024*1024)}MB"})
            logger.debug("Received file: %s, size: %d bytes, content_type: %s", file.filename, len(content), file.content_type)
            file_path = tempfile.mktemp(suffix=f"_{file.filename}", dir=str(UPLOAD_DIR))
            with open(file_path, "wb") as f: f.write(content)
            try:
                file_content = content.decode('utf-8')
                logger.debug("File content (text): %d chars", len(file_content))
            except:
                logger.debug("File is binary, cannot read as text")
        msg = message or "请分析"
        if file and file.filename:
            if file_content:
                msg = f"{msg}\n\n[文件：{file.filename}]\n文件内容:\n{file_content[:10000]}"
            else:
                msg = f"{msg}\n\n[文件：{file.filename}]\n这是一个二进制文件，已保存到：{file_path}"
        logger.debug("Calling hermes with message: %s..., image_path: %s", msg[:100], image_path)

        # 使用 asyncio.to_thread 避免阻塞事件循环
        response = await asyncio.to_thread(call_hermes, msg, image_path)
        logger.debug("Hermes response: %s...", response[:200])

        for p in [image_path, file_path]:
            if p and os.path.exists(p): os.remove(p)
        return JSONResponse(content={"response": response})
    except Exception as e:
        logger.error("Chat error: %s", e, exc_info=True)
        return JSONResponse(content={"response": f"错误：{e}"})

@app.post("/api/chat_stream")
async def chat_stream(message: str = Form(...), image: UploadFile = File(None), file: UploadFile = File(None)):
    """流式聊天接口"""
    image_path, file_path = None, None
    file_content = None
    try:
        if image:
            content = await image.read()
            if len(content) > MAX_FILE_SIZE:
                return JSONResponse(status_code=413, content={"response": f"文件过大，最大允许 {MAX_FILE_SIZE // (1024*1024)}MB"})
            tp = tempfile.mktemp(suffix=".png", dir=str(UPLOAD_DIR))
            with open(tp, "wb") as f: f.write(content)
            image_path = tp
        if file:
            content = await file.read()
            if len(content) > MAX_FILE_SIZE:
                return JSONResponse(status_code=413, content={"response": f"文件过大，最大允许 {MAX_FILE_SIZE // (1024*1024)}MB"})
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
            # 使用 asyncio.to_thread 包装流式调用，避免阻塞
            # 由于 call_hermes_stream 是 generator，我们用线程池执行
            import queue
            q = queue.Queue()

            def _run():
                try:
                    for chunk in call_hermes_stream(msg, image_path):
                        q.put(chunk)
                except Exception as e:
                    q.put(f"错误：{e}")
                finally:
                    # 清理临时文件
                    for p in [image_path, file_path]:
                        if p and os.path.exists(p):
                            os.remove(p)
                    q.put(None)  # sentinel

            # 在线程中运行
            thread = __import__('threading').Thread(target=_run, daemon=True)
            thread.start()

            while True:
                chunk = q.get()
                if chunk is None:
                    break
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream")
    except Exception as e:
        logger.error("Stream error: %s", e, exc_info=True)
        return JSONResponse(content={"response": f"错误：{e}"})

# ── 健康检查端点 ──
@app.get("/api/health")
async def health_check():
    """健康检查：返回服务状态"""
    import shutil as _shutil
    sessions_dir = HERMES_HOME / "sessions"
    sessions_count = 0
    if sessions_dir.exists():
        sessions_count = len(glob.glob(str(sessions_dir / "*.json")))

    # 磁盘空闲空间
    try:
        statvfs = os.statvfs(str(HERMES_HOME))
        disk_free_gb = round((statvfs.f_frsize * statvfs.f_bavail) / (1024 ** 3), 2)
    except Exception:
        disk_free_gb = -1.0

    return JSONResponse(content={
        "status": "ok",
        "uptime": round(time.time() - START_TIME, 1),
        "hermes_path": str(HERMES_HOME),
        "disk_free_gb": disk_free_gb,
        "sessions_count": sessions_count,
    })

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

@app.get("/api/plugin/update/check")
async def check_plugin_update():
    """检查插件更新"""
    import subprocess
    plugin_dir = Path(__file__).parent
    try:
        # 检查是否是 git 仓库
        if not (plugin_dir / ".git").exists():
            return JSONResponse(content={"has_update": False, "current_version": "unknown", "latest_version": "unknown", "error": "非 git 仓库"})

        # 获取当前版本信息
        result = subprocess.run(["git", "-C", str(plugin_dir), "log", "-1", "--format=%h %s"], capture_output=True, text=True, timeout=10)
        current_version = result.stdout.strip() if result.returncode == 0 else "unknown"

        # 获取远程更新信息
        result = subprocess.run(["git", "-C", str(plugin_dir), "fetch", "origin"], capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return JSONResponse(content={"has_update": False, "current_version": current_version, "latest_version": "unknown", "error": "无法连接远程仓库"})

        # 比较本地和远程
        result = subprocess.run(["git", "-C", str(plugin_dir), "rev-list", "HEAD..origin/main", "--count"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            ahead_count = int(result.stdout.strip())
            if ahead_count > 0:
                # 获取最新版本信息
                result = subprocess.run(["git", "-C", str(plugin_dir), "log", "origin/main", "-1", "--format=%h %s"], capture_output=True, text=True, timeout=10)
                latest_version = result.stdout.strip() if result.returncode == 0 else "unknown"
                return JSONResponse(content={"has_update": True, "current_version": current_version, "latest_version": latest_version, "commits_behind": ahead_count})

        return JSONResponse(content={"has_update": False, "current_version": current_version, "latest_version": current_version, "commits_behind": 0})
    except Exception as e:
        return JSONResponse(content={"has_update": False, "error": str(e)})

@app.post("/api/plugin/update/execute")
async def execute_plugin_update():
    """执行插件更新"""
    import subprocess
    plugin_dir = Path(__file__).parent
    try:
        # 拉取最新代码
        result = subprocess.run(["git", "-C", str(plugin_dir), "pull", "origin", "main"], capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            # 尝试安装依赖
            requirements_file = plugin_dir / "requirements.txt"
            if requirements_file.exists():
                venv_python = Path(HERMES_HOME) / "venvs" / "hermes-web-chat" / "bin" / "python"
                if venv_python.exists():
                    subprocess.run([str(venv_python), "-m", "pip", "install", "-r", str(requirements_file), "-q"], timeout=30)
            return JSONResponse(content={"success": True, "output": result.stdout, "message": "更新成功！建议重启服务以应用更改。"})
        else:
            return JSONResponse(content={"success": False, "error": result.stderr, "message": "更新失败"})
    except subprocess.TimeoutExpired:
        return JSONResponse(content={"success": False, "error": "更新超时", "message": "更新操作超时，请检查网络连接"})
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e), "message": "更新失败"})

# 静态文件服务
from fastapi.staticfiles import StaticFiles
import os as _os
static_dir = _os.path.join(_os.path.dirname(__file__), 'static')
if _os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

def get_html_content():
    import time
    timestamp = int(time.time())
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <title>Hermes Agent</title>
    <!-- marked.js for Markdown rendering (CDN + fallback) -->
    <!-- KaTeX for math rendering -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css?v={timestamp}">
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js?v={timestamp}"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js?v={timestamp}"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js?v={timestamp}"></script>
    <!-- KaTeX + marked CDN fallback -->
    <script>
    if (typeof marked === 'undefined') {{
        console.warn('marked.js CDN 加载失败，使用内置简易 Markdown 解析器');
        // 内置简易 Markdown 解析器作为 CDN 回退
        window.marked = {{
            parse: function(text) {{
                if (!text) return '';
                var html = text;
                // 代码块
                html = html.replace(/```([\\s\\S]*?)```/g, function(m, code) {{
                    return '<pre><code>' + code.replace(/</g,'&lt;').replace(/>/g,'&gt;') + '</code></pre>';
                }});
                // 行内代码
                html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
                // 粗体
                html = html.replace(/\\*\\*([^*]+)\\*\\*/g, '<strong>$1</strong>');
                // 斜体
                html = html.replace(/\\*([^*]+)\\*/g, '<em>$1</em>');
                // 标题
                html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
                html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
                html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
                // 链接
                html = html.replace(/\\[([^\\]]+)\\]\\(([^)]+)\\)/g, '<a href="$2" target="_blank">$1</a>');
                // 换行
                html = html.replace(/\\n/g, '<br>');
                return html;
            }}
        }};
    }}
    </script>
    <!-- highlight.js for syntax highlighting (CDN + fallback) -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/styles/atom-one-dark.min.css">
    <script src="https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/lib/core.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/lib/languages/python.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/lib/languages/javascript.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/lib/languages/typescript.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/lib/languages/bash.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/lib/languages/json.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/lib/languages/yaml.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/lib/languages/sql.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/lib/languages/java.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/lib/languages/go.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/lib/languages/rust.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/lib/languages/cpp.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/lib/languages/c.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/lib/languages/csharp.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/lib/languages/php.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/lib/languages/ruby.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/lib/languages/swift.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/lib/languages/kotlin.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/lib/languages/shell.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/lib/languages/xml.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/lib/languages/css.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/lib/languages/diff.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/lib/languages/markdown.min.js"></script>
    <script>
    if (typeof hljs === 'undefined') {{
        console.warn('highlight.js CDN 加载失败，代码高亮功能不可用');
        window.hljs = {{
            highlightElement: function(el) {{ }},
            highlightAll: function() {{ }}
        }};
    }}
    </script>
    <style>
        :root {{
            /* 默认主题 - 浅色 */
            --bg-primary: #f5f5f5;
            --bg-secondary: #ffffff;
            --bg-sidebar: #e8e8e8;
            --bg-gradient: linear-gradient(135deg, #f5f5f5 0%, #e8e8e8 50%, #d0d0d0 100%);
            --sidebar-gradient: linear-gradient(180deg, #e8e8e8 0%, #f5f5f5 100%);
            --text-primary: #1a1a2e;
            --text-secondary: #555;
            --text-muted: #888;
            --accent-primary: #0066cc;
            --accent-secondary: #00aa55;
            --accent-gradient: linear-gradient(135deg, #0066cc 0%, #0099ff 100%);
            --border-color: #cccccc;
            --border-light: #dddddd;
            --message-bg: #ffffff;
            --code-bg: #f0f0f0;
            --code-text: #d63384;
            --pre-bg: #1a1a2e;
            --pre-text: #f8f8f2;
            --blockquote-bg: rgba(0, 102, 204, 0.1);
            --table-header-bg: rgba(0, 102, 204, 0.1);
            --hover-bg: rgba(0, 102, 204, 0.1);
            --italic-text: #997a00;
        }}
        /* 深空蓝主题 */
        [data-theme="blue"] {{
            --bg-primary: #0f0f1a;
            --bg-secondary: #1a1a2e;
            --bg-sidebar: #0a0a1a;
            --bg-gradient: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
            --sidebar-gradient: linear-gradient(180deg, #0a0a1a 0%, #1a1a2e 100%);
            --text-primary: #e8e8e8;
            --text-secondary: #888;
            --text-muted: #666;
            --accent-primary: #00d9ff;
            --accent-secondary: #00ff88;
            --accent-gradient: linear-gradient(135deg, #00d9ff 0%, #0099ff 100%);
            --border-color: #1f3a5f;
            --border-light: #2a2a4e;
            --message-bg: #1a1a2e;
            --code-bg: #2a2a4e;
            --code-text: #ff79c6;
            --pre-bg: #0f0f1a;
            --pre-text: #f8f8f2;
            --blockquote-bg: rgba(0, 217, 255, 0.05);
            --table-header-bg: rgba(0, 217, 255, 0.1);
            --hover-bg: rgba(0, 217, 255, 0.1);
            --italic-text: #f1fa8c;
        }}
        /* 暗色主题 - 纯黑 */
        [data-theme="dark"] {{
            --bg-primary: #000000;
            --bg-secondary: #121212;
            --bg-sidebar: #0a0a0a;
            --bg-gradient: linear-gradient(135deg, #000000 0%, #121212 50%, #1a1a1a 100%);
            --sidebar-gradient: linear-gradient(180deg, #0a0a0a 0%, #121212 100%);
            --text-primary: #e0e0e0;
            --text-secondary: #a0a0a0;
            --text-muted: #707070;
            --accent-primary: #bb86fc;
            --accent-secondary: #03dac6;
            --accent-gradient: linear-gradient(135deg, #bb86fc 0%, #9965f4 100%);
            --border-color: #333333;
            --border-light: #2a2a2a;
            --message-bg: #121212;
            --code-bg: #2a2a2a;
            --code-text: #ff79c6;
            --pre-bg: #0a0a0a;
            --pre-text: #f8f8f2;
            --blockquote-bg: rgba(187, 134, 252, 0.1);
            --table-header-bg: rgba(187, 134, 252, 0.1);
            --hover-bg: rgba(187, 134, 252, 0.1);
            --italic-text: #ffd700;
        }}
        /* 护眼主题 - 绿色 */
        [data-theme="green"] {{
            --bg-primary: #1a2f1a;
            --bg-secondary: #2d4a2d;
            --bg-sidebar: #152515;
            --bg-gradient: linear-gradient(135deg, #1a2f1a 0%, #2d4a2d 50%, #3d5a3d 100%);
            --sidebar-gradient: linear-gradient(180deg, #152515 0%, #2d4a2d 100%);
            --text-primary: #d0e8d0;
            --text-secondary: #a0c0a0;
            --text-muted: #709070;
            --accent-primary: #7ec87e;
            --accent-secondary: #a0e8a0;
            --accent-gradient: linear-gradient(135deg, #7ec87e 0%, #5cb85c 100%);
            --border-color: #3d5a3d;
            --border-light: #4a6a4a;
            --message-bg: #2d4a2d;
            --code-bg: #3d5a3d;
            --code-text: #ff9ec6;
            --pre-bg: #152515;
            --pre-text: #f8f8f2;
            --blockquote-bg: rgba(126, 200, 126, 0.1);
            --table-header-bg: rgba(126, 200, 126, 0.1);
            --hover-bg: rgba(126, 200, 126, 0.1);
            --italic-text: #e8f87e;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: var(--bg-gradient); min-height: 100vh; display: flex; color: var(--text-primary); }}
        .sidebar {{ width: 260px; background: var(--sidebar-gradient); border-right: 1px solid var(--border-color); flex-shrink: 0; display: flex; flex-direction: column; height: 100vh; overflow: hidden; }}
        .logo {{ text-align: center; padding: 20px; border-bottom: 1px solid var(--border-color); position: relative; }}
        .logo h1 {{ font-size: 24px; background: var(--accent-gradient); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .logo p {{ color: var(--text-muted); font-size: 12px; margin-top: 5px; }}
        .page-header {{ padding: 20px 30px; border-bottom: 1px solid var(--border-color); background: var(--bg-secondary); display: flex; justify-content: space-between; align-items: center; }}
        .page-header h2 {{ font-size: 18px; color: var(--text-primary); margin: 0; display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }}
        .header-actions {{ display: flex; gap: 8px; }}
        .header-btn {{ width: 32px; height: 32px; border-radius: 8px; border: none; background: var(--code-bg); color: var(--text-secondary); cursor: pointer; font-size: 16px; transition: all 0.2s; }}
        .header-btn:hover {{ background: var(--accent-primary); color: white; }}
        .menu {{ list-style: none; padding: 10px; flex: 1; overflow-y: auto; }}
        .menu-item {{ padding: 12px 16px; margin: 4px 0; border-radius: 8px; cursor: pointer; transition: all 0.2s; color: var(--text-secondary); }}
        .menu-item:hover {{ background: var(--hover-bg); color: var(--accent-primary); }}
        .menu-item.active {{ background: var(--accent-gradient); color: white; }}
        .main {{ flex: 1; display: flex; flex-direction: column; overflow: hidden; }}
        .page {{ display: none; height: 100vh; flex-direction: column; }}
        .page.active {{ display: flex; }}
        .page-header {{ padding: 20px 30px; border-bottom: 1px solid var(--border-color); background: var(--bg-secondary); }}
        .page-header h2 {{ font-size: 18px; color: var(--text-primary); }}
        .chat-messages {{ flex: 1; overflow-y: auto; overflow-x: hidden; padding: 24px 30px; display: flex; flex-direction: column; gap: 24px; }}
        .message {{ display: flex; gap: 15px; max-width: 80%; }}
        .message.user {{ align-self: flex-end; flex-direction: row-reverse; }}
        .message-avatar {{ width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 20px; flex-shrink: 0; }}
        .message-content {{ background: var(--message-bg); padding: 18px 22px; border-radius: 16px; border: 1px solid var(--border-light); max-width: 100%; overflow-wrap: break-word; word-wrap: break-word; word-break: break-word; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }}
        .message-text {{ color: var(--text-primary); line-height: 1.75; font-size: 15px; overflow-wrap: break-word; word-wrap: break-word; word-break: break-word; max-width: 100%; }}
        .message-text p {{ margin: 0.75em 0; }}
        .message-text p:first-child {{ margin-top: 0; }}
        .message-text p:last-child {{ margin-bottom: 0; }}
        .message-text code {{ background: var(--code-bg); padding: 3px 7px; border-radius: 5px; font-family: 'Consolas', 'Monaco', 'Courier New', monospace; font-size: 13px; color: var(--code-text); border: 1px solid var(--border-light); }}
        .message-text pre {{ background: var(--pre-bg); padding: 16px 16px 8px; border-radius: 10px; overflow-x: auto; margin: 14px 0; border: 1px solid var(--border-light); position: relative; }}
        .message-text pre code {{ background: transparent; padding: 15px; color: inherit; font-size: 13px; line-height: 1.5; display: block; }}
        /* highlight.js 高亮样式覆盖 */
        /* hljs compatibility */
        .message-text pre code {{ color: var(--pre-text); }}
        .message-text pre code .hljs {{ background: transparent; padding: 0; color: inherit; }}
        .message-text pre code .hljs-comment {{ color: #6a9955; font-style: italic; }}
        .message-text pre code .hljs-keyword {{ color: #569cd6; font-weight: bold; }}
        .message-text pre code .hljs-string {{ color: #ce9178; }}
        .message-text pre code .hljs-function {{ color: #dcdcaa; }}
        .message-text pre code .hljs-number {{ color: #b5cea8; }}
        .message-text pre code .hljs-class {{ color: #4ec9b0; }}
        .message-text pre code .hljs-variable {{ color: #9cdcfe; }}
        .message-text pre code .hljs-operator {{ color: #d4d4d4; }}
        .message-text pre code .hljs-punctuation {{ color: #d4d4d4; }}
        /* 代码块语言标签 */
        /* position: relative removed - merged above */
        .message-text pre::before {{ 
            content: attr(data-language); 
            position: absolute; 
            top: 0; 
            right: 0; 
            background: rgba(255,255,255,0.1); 
            color: #888; 
            padding: 4px 8px; 
            font-size: 11px; 
            border-radius: 0 8px 0 8px;
            text-transform: uppercase;
            font-weight: 600;
        }}
        .message-text ul, .message-text ol {{ margin: 12px 0; padding-left: 24px; }}
        .message-text ul ul, .message-text ol ol {{ margin: 4px 0; }}
        .message-text li {{ margin: 6px 0; line-height: 1.7; }}
        .message-text li > p {{ margin: 4px 0; }}
        .message-text li {{ margin: 5px 0; }}
        .message-text li::marker {{ color: var(--text-secondary); }}
        .message-text blockquote {{ border-left: 4px solid var(--accent-primary); padding: 12px 16px; margin: 14px 0; color: var(--text-secondary); background: var(--blockquote-bg); border-radius: 0 8px 8px 0; font-style: italic; }}
        .message-text strong {{ color: var(--text-primary); font-weight: 700; }}
        .message-text em {{ color: var(--italic-text); font-style: italic; }}
        /* Headings - clear hierarchy */
        .message-text h1 {{ margin: 20px 0 12px; color: var(--text-primary); font-size: 22px; font-weight: 700; border-bottom: 2px solid var(--border-color); padding-bottom: 8px; }}
        .message-text h2 {{ margin: 18px 0 10px; color: var(--text-primary); font-size: 19px; font-weight: 600; border-bottom: 1px solid var(--border-light); padding-bottom: 6px; }}
        .message-text h3 {{ margin: 14px 0 8px; color: var(--accent-primary); font-size: 16px; font-weight: 600; }}
        .message-text h4 {{ margin: 12px 0 6px; color: var(--accent-primary); font-size: 15px; font-weight: 600; }}
        .message-text a {{ color: var(--accent-primary); text-decoration: none; }}
        .message-text a:hover {{ text-decoration: underline; }}
        .message-text table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
        .message-text th, .message-text td {{ border: 1px solid var(--border-light); padding: 8px 12px; text-align: left; }}
        .message-text th {{ background: var(--table-header-bg); color: var(--accent-primary); font-weight: 600; }}
        .message-text tr:nth-child(even) {{ background: rgba(255, 255, 255, 0.02); }}
        .message-text tr:hover {{ background: var(--hover-bg); }}
        .message-text hr {{ border: none; border-top: 2px solid var(--border-light); margin: 24px 0; }}
        .message-text img {{ max-width: 100%; border-radius: 8px; margin: 10px 0; }}
        .message-image {{ max-width: 100%; max-height: 400px; border-radius: 10px; margin-top: 10px; border: 2px solid var(--border-light); }}
        .input-container {{ padding: 20px 30px; background: var(--bg-secondary); border-top: 1px solid var(--border-color); }}
        .input-wrapper {{ display: flex; gap: 15px; align-items: flex-end; background: var(--message-bg); border: 2px solid var(--border-light); border-radius: 24px; padding: 8px 8px 8px 20px; }}
        #messageInput {{ flex: 1; background: transparent; border: none; outline: none; color: var(--text-primary); font-size: 15px; padding: 10px 0; resize: none; max-height: 150px; font-family: inherit; }}
        .input-actions {{ display: flex; gap: 8px; }}
        .action-btn {{ width: 44px; height: 44px; border-radius: 50%; border: none; cursor: pointer; background: var(--code-bg); color: var(--text-secondary); font-size: 20px; transition: all 0.2s; }}
        .action-btn:hover {{ background: var(--border-light); color: var(--accent-primary); }}
        #sendBtn {{ background: var(--accent-gradient); color: white; font-size: 18px; font-weight: bold; }}
        #sendBtn:hover {{ transform: scale(1.05); }}
        #sendBtn:disabled {{ opacity: 0.6; cursor: not-allowed; transform: none; }}
        #sendBtn.thinking {{ background: #ff9500; animation: pulse 1.5s ease-in-out infinite; }}
        @keyframes pulse {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.7; }} }}
        .preview-container, .file-preview-container {{ display: none; padding: 10px 30px; background: var(--bg-secondary); border-top: 1px solid var(--border-color); }}
        .preview-container.show, .file-preview-container.show {{ display: block; }}
        .preview-image {{ max-height: 150px; border-radius: 10px; border: 2px solid var(--accent-primary); }}
        .preview-remove, .file-preview-remove {{ background: #ff4757; color: white; border: none; width: 24px; height: 24px; border-radius: 50%; cursor: pointer; float: right; }}
        #fileInput, #imageInput {{ display: none; }}
        .card {{ background: var(--message-bg); border: 1px solid var(--border-light); border-radius: 12px; padding: 20px; margin-bottom: 20px; }}
        .data-list {{ list-style: none; }}
        .data-list li {{ padding: 12px 15px; background: var(--hover-bg); border-radius: 8px; margin-bottom: 10px; border-left: 3px solid var(--accent-primary); }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }}
        .stat-card {{ background: var(--sidebar-gradient); border: 1px solid var(--border-color); border-radius: 12px; padding: 25px; text-align: center; }}
        .stat-value {{ font-size: 36px; font-weight: bold; color: var(--accent-primary); }}
        .stat-label {{ color: var(--text-secondary); font-size: 14px; margin-top: 10px; }}
        .loading {{ text-align: center; padding: 40px; color: var(--text-muted); }}
        .loading-spinner {{ width: 40px; height: 40px; border: 3px solid var(--border-light); border-top-color: var(--accent-primary); border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 20px; }}
        @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
        .typing-indicator {{ display: flex; gap: 4px; padding: 15px 20px; align-items: center; }}
        .typing-dot {{ width: 8px; height: 8px; border-radius: 50%; background: var(--accent-primary); animation: typing-bounce 1.4s infinite ease-in-out; }}
        .typing-dot:nth-child(1) {{ animation-delay: 0s; }}
        .typing-dot:nth-child(2) {{ animation-delay: 0.2s; }}
        .typing-dot:nth-child(3) {{ animation-delay: 0.4s; }}
        @keyframes typing-bounce {{ 0%, 80%, 100% {{ transform: translateY(0); opacity: 0.3; }} 40% {{ transform: translateY(-6px); opacity: 1; }} }}
        /* 思考过程显示框 */
        .thinking-container {{ 
            background: var(--bg-secondary); 
            border: 1px solid var(--border-light); 
            border-left: 3px solid var(--accent-primary);
            border-radius: 8px; 
            padding: 12px 16px; 
            margin: 10px 0;
            max-width: 100%;
        }}
        .thinking-header {{ 
            display: flex; 
            align-items: center; 
            gap: 8px; 
            margin-bottom: 8px; 
            font-size: 13px; 
            color: var(--accent-primary);
            font-weight: 600;
        }}
        .thinking-icon {{ 
            width: 16px; 
            height: 16px; 
            animation: thinking-pulse 1.5s ease-in-out infinite;
        }}
        @keyframes thinking-pulse {{ 
            0%, 100% {{ transform: scale(1); opacity: 1; }} 
            50% {{ transform: scale(1.2); opacity: 0.7; }} 
        }}
        .thinking-content {{ 
            background: var(--pre-bg); 
            border-radius: 6px; 
            padding: 12px; 
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 13px;
            line-height: 1.5;
            color: var(--text-secondary);
            max-height: 200px;
            overflow-y: auto;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        .thinking-content::-webkit-scrollbar {{ width: 6px; }}
        .thinking-content::-webkit-scrollbar-track {{ background: var(--bg-secondary); }}
        .thinking-content::-webkit-scrollbar-thumb {{ background: var(--border-light); border-radius: 3px; }}
        .thinking-content::-webkit-scrollbar-thumb:hover {{ background: var(--accent-primary); }}
        .refresh-btn {{ background: var(--code-bg); color: var(--accent-primary); border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 13px; }}
        .refresh-btn:hover {{ background: var(--accent-primary); color: var(--bg-primary); }}
        .filter-bar {{ display: inline-flex; align-items: center; }}
        .filter-select {{ background: var(--code-bg); color: var(--text-primary); border: 1px solid var(--border-light); padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 13px; }}
        .filter-select:hover {{ border-color: var(--accent-primary); }}
        .filter-select:focus {{ outline: none; border-color: var(--accent-primary); }}
        .clear-btn {{ width: calc(100% - 20px); margin: 10px; padding: 10px; background: var(--code-bg); color: #ff6b6b; border: none; border-radius: 8px; cursor: pointer; }}
        ::-webkit-scrollbar {{ width: 8px; }}
        ::-webkit-scrollbar-track {{ background: var(--bg-secondary); }}
        ::-webkit-scrollbar-thumb {{ background: var(--border-light); border-radius: 4px; }}
        /* 设置页面样式 */
        .settings-container {{ max-width: 900px; margin: 0 auto; padding: 10px; }}
        .setting-section {{ 
            background: var(--message-bg); 
            border: 1px solid var(--border-light); 
            border-radius: 16px; 
            padding: 24px; 
            margin-bottom: 24px;
            transition: all 0.3s ease;
        }}
        .setting-section:hover {{ border-color: var(--accent-primary); box-shadow: 0 4px 20px rgba(0,217,255,0.1); }}
        .setting-header {{ display: flex; align-items: center; gap: 10px; margin-bottom: 16px; }}
        .setting-icon {{ font-size: 24px; }}
        .setting-title {{ font-size: 18px; color: var(--accent-primary); font-weight: 600; margin: 0; }}
        .setting-description {{ color: var(--text-secondary); font-size: 14px; margin: 8px 0 16px 34px; line-height: 1.6; }}
        .theme-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 20px; margin-top: 16px; }}
        .theme-card {{ 
            background: linear-gradient(135deg, var(--bg-secondary) 0%, var(--message-bg) 100%); 
            border: 2px solid var(--border-light); 
            border-radius: 16px; 
            padding: 24px 20px; 
            cursor: pointer; 
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); 
            text-align: center; 
            position: relative; 
            overflow: hidden;
        }}
        .theme-card::before {{ content: ''; position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: linear-gradient(135deg, transparent 0%, rgba(0,217,255,0.05) 100%); opacity: 0; transition: opacity 0.3s ease; }}
        .theme-card:hover {{ border-color: var(--accent-primary); transform: translateY(-6px); box-shadow: 0 12px 40px rgba(0,217,255,0.15); }}
        .theme-card:hover::before {{ opacity: 1; }}
        .theme-card:hover .theme-preview {{ transform: scale(1.08); box-shadow: 0 8px 25px rgba(0,0,0,0.3); }}
        .theme-card:active {{ transform: translateY(-3px) scale(0.98); }}
        .theme-card.active {{ border-color: var(--accent-primary); box-shadow: 0 0 30px rgba(0,217,255,0.2); background: linear-gradient(135deg, rgba(0,217,255,0.05) 0%, rgba(0,217,255,0.1) 100%); }}
        .theme-card.active::after {{ content: '✓'; position: absolute; top: 12px; right: 12px; width: 28px; height: 28px; background: linear-gradient(135deg, #00d9ff 0%, #0099ff 100%); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-size: 16px; font-weight: bold; box-shadow: 0 4px 15px rgba(0,217,255,0.4); animation: checkmark-pop 0.3s cubic-bezier(0.68, -0.55, 0.265, 1.55); }}
        @keyframes checkmark-pop {{ 0% {{ transform: scale(0); opacity: 0; }} 70% {{ transform: scale(1.2); }} 100% {{ transform: scale(1); opacity: 1; }} }}
        .theme-preview {{ width: 70px; height: 70px; border-radius: 16px; margin: 0 auto 14px; border: 3px solid var(--border-light); transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); position: relative; z-index: 1; box-shadow: 0 4px 15px rgba(0,0,0,0.2); }}
        .theme-name {{ color: var(--text-primary); font-size: 15px; font-weight: 500; transition: all 0.3s ease; position: relative; z-index: 1; }}
        .theme-card.active .theme-name {{ color: var(--accent-primary); font-weight: 700; text-shadow: 0 0 10px rgba(0,217,255,0.3); }}
        .about-section {{ line-height: 1.8; color: var(--text-secondary); }}
        .about-section p {{ margin-bottom: 12px; }}
        .version-badge {{ display: inline-block; background: linear-gradient(135deg, #00d9ff 0%, #0099ff 100%); color: white; padding: 4px 14px; border-radius: 20px; font-size: 12px; font-weight: 600; margin-left: 10px; box-shadow: 0 2px 10px rgba(0,217,255,0.3); }}
        .storage-action-btn {{ 
            background: linear-gradient(135deg, #ff4444 0%, #ff6666 100%); 
            color: white; 
            border: none; 
            border-radius: 10px; 
            padding: 12px 24px; 
            font-size: 14px; 
            font-weight: 500; 
            cursor: pointer; 
            transition: all 0.3s ease;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            margin-top: 12px;
            box-shadow: 0 4px 15px rgba(255,68,68,0.3);
        }}
        .storage-action-btn:hover {{ transform: translateY(-2px); box-shadow: 0 6px 25px rgba(255,68,68,0.4); }}
        .storage-action-btn:active {{ transform: translateY(0); }}
        .storage-info {{ margin-top: 16px; padding: 12px 16px; background: var(--bg-secondary); border-radius: 10px; font-size: 13px; color: var(--text-secondary); border-left: 3px solid var(--accent-primary); }}
        /* Code block copy button */
        .code-block-wrapper {{ position: relative; margin: 10px 0; }}
        .code-copy-btn {{ position: absolute; top: 8px; right: 8px; background: rgba(255,255,255,0.1); color: #888; border: none; padding: 4px 10px; border-radius: 6px; cursor: pointer; font-size: 12px; transition: all 0.2s; z-index: 10; }}
        .code-copy-btn:hover {{ background: var(--accent-primary); color: white; }}
        .code-copy-btn.copied {{ background: var(--accent-secondary); color: white; }}
        /* Responsive code blocks */
        .message-text pre {{ overflow-x: auto; max-width: 100%; }}
        .message-text pre code {{ display: block; min-width: 0; }}
        /* KaTeX styles */
        .katex-display {{ margin: 10px 0; overflow-x: auto; }}
        .katex {{ font-size: 1.1em; }}
        .message-text .katex-display {{ background: transparent; padding: 16px 0; border-radius: 8px; text-align: center; border-left: 3px solid var(--accent-primary); margin: 16px 0; }}
        /* Task list checkboxes */
        .task-list-item {{ list-style: none !important; margin-left: -24px !important; padding-left: 4px !important; }}
        .task-list-item::marker {{ content: none !important; display: none !important; }}
        .task-list-item::before {{ content: none !important; }}
        ul > .task-list-item {{ list-style-type: none !important; }}
        /* Remove bullets from any list containing task items */
        ul:has(.task-list-item) {{ list-style: none !important; padding-left: 0 !important; }}
        ul:has(> .task-list-item) {{ list-style: none !important; padding-left: 0 !important; }}
        /* Hide bullets on any list item containing a checkbox */
        .message-text ul li:has(input[type="checkbox"]) {{ list-style: none !important; }}
        .message-text ul li:has(input[type="checkbox"])::marker {{ content: none !important; display: none !important; }}
        /* Alternative: hide all markers in task list context */
        .message-text li input[type="checkbox"] {{ margin-right: 8px; }}
        .message-text li input[type="checkbox"]::before {{ content: ''; }}
        .message-text ul li.task-list-item {{ list-style: none !important; }}
        .task-list-item input[type="checkbox"] {{ margin-right: 6px; accent-color: var(--accent-primary); }}
        /* Stream update animation (prevent flash) */
        .streaming-content {{ transition: opacity 0.1s; }}
        /* Update checkmark animation */
        @keyframes copy-check {{ 0% {{ transform: scale(0); }} 50% {{ transform: scale(1.2); }} 100% {{ transform: scale(1); }} }}
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
            <li class="menu-item" data-page="sessions">📋 会话历史</li>
            <li class="menu-item" data-page="memory">🧠 记忆管理</li>
            <li class="menu-item" data-page="skills">📚 技能列表</li>
            <li class="menu-item" data-page="cron">⏰ 定时任务</li>
            <li class="menu-item" data-page="projects">📊 项目跟踪</li>
            <li class="menu-item" data-page="costs">💰 费用统计</li>
            <li class="menu-item" data-page="patterns">📈 使用模式</li>
            <li class="menu-item" data-page="settings">⚙️ 设置</li>
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
                        <button class="action-btn" id="sendBtn" onclick="sendMessage()" title="发送">⬆️</button>
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
        <div id="page-settings" class="page">
            <div class="page-header">
                <h2>⚙️ 设置</h2>
            </div>
            <div class="chat-messages">
                <div class="settings-container">
                    <div class="setting-section">
                        <div class="setting-header">
                            <span class="setting-icon">🗄️</span>
                            <h3 class="setting-title">存储管理</h3>
                        </div>
                        <div class="setting-description">清理本地存储的会话数据，释放浏览器空间。此操作仅影响浏览器缓存，服务器上的会话文件不受影响。</div>
                        <button class="storage-action-btn" onclick="clearAllLocalStorage()">
                            <span>🗑️</span>
                            <span>清理所有本地会话数据</span>
                        </button>
                        <div id="storageInfo" class="storage-info"></div>
                    </div>
                    <div class="setting-section">
                        <div class="setting-header">
                            <span class="setting-icon">🎨</span>
                            <h3 class="setting-title">主题选择</h3>
                        </div>
                        <div class="setting-description">选择您喜欢的界面主题，偏好会自动保存，下次访问时自动应用。</div>
                        <div class="theme-grid">
                            <div class="theme-card" data-theme="light" onclick="switchTheme('light')">
                                <div class="theme-preview" style="background: linear-gradient(135deg, #f5f5f5 0%, #e8e8e8 50%, #d0d0d0 100%);"></div>
                                <div class="theme-name">浅色主题</div>
                            </div>
                            <div class="theme-card" data-theme="blue" onclick="switchTheme('blue')">
                                <div class="theme-preview" style="background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);"></div>
                                <div class="theme-name">深空蓝</div>
                            </div>
                            <div class="theme-card" data-theme="dark" onclick="switchTheme('dark')">
                                <div class="theme-preview" style="background: linear-gradient(135deg, #000000 0%, #121212 50%, #1a1a1a 100%);"></div>
                                <div class="theme-name">纯黑主题</div>
                            </div>
                            <div class="theme-card" data-theme="green" onclick="switchTheme('green')">
                                <div class="theme-preview" style="background: linear-gradient(135deg, #1a2f1a 0%, #2d4a2d 50%, #3d5a3d 100%);"></div>
                                <div class="theme-name">护眼绿</div>
                            </div>
                        </div>
                    </div>
                    <div class="setting-section">
                        <div class="setting-header">
                            <span class="setting-icon">🔄</span>
                            <h3 class="setting-title">插件更新</h3>
                        </div>
                        <div class="setting-description">检查并安装 Hermes Web Chat 的最新版本。更新会自动拉取最新代码并安装依赖。</div>
                        <div style="display: flex; gap: 12px; align-items: center; flex-wrap: wrap;">
                            <button class="refresh-btn" id="checkUpdateBtn" onclick="checkForUpdates()" style="padding: 10px 20px; font-size: 14px;">
                                🔍 检查更新
                            </button>
                            <button class="refresh-btn" id="updateNowBtn" onclick="executeUpdate()" style="padding: 10px 20px; font-size: 14px; display: none; background: linear-gradient(135deg, #00d9ff 0%, #0099ff 100%); color: white;">
                                🚀 立即更新
                            </button>
                            <span id="updateStatus" style="color: var(--text-secondary); font-size: 14px; margin-left: 10px;"></span>
                        </div>
                        <div id="updateInfo" style="margin-top: 16px; padding: 16px; background: var(--bg-secondary); border-radius: 10px; font-size: 14px; display: none;">
                            <div style="margin-bottom: 8px;"><strong>当前版本：</strong><span id="currentVersion"></span></div>
                            <div style="margin-bottom: 8px;"><strong>最新版本：</strong><span id="latestVersion"></span></div>
                            <div id="commitsBehind" style="color: var(--accent-primary);"></div>
                        </div>
                        <div id="updateOutput" style="margin-top: 16px; padding: 16px; background: var(--pre-bg); border-radius: 10px; font-size: 13px; font-family: 'Consolas', 'Monaco', monospace; color: var(--pre-text); max-height: 300px; overflow-y: auto; display: none;"></div>
                    </div>
                    <div class="setting-section">
                        <div class="setting-header">
                            <span class="setting-icon">📖</span>
                            <h3 class="setting-title">关于</h3>
                        </div>
                        <div class="about-section">
                            <p><strong>Hermes Web Chat</strong> <span class="version-badge">v1.12.0</span></p>
                            <p>Hermes Agent 的现代化 Web 聊天界面插件，支持 Markdown 渲染、多主题切换、文件/图片上传、流式响应等功能。</p>
                            <p>📍 数据存储在本地浏览器 (localStorage) 和 Hermes 会话文件中</p>
                            <p>🔧 主题偏好会自动保存，下次访问时自动应用</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <script src="/static/app.js?v={timestamp}"></script>
</body>
</html>'''

if __name__ == "__main__":
    # 从配置文件或命令行参数获取端口
    port = CONFIG.get("port", 8888)
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

    logger.info("Hermes Agent Web Chat v1.12.0")
    logger.info("Access: http://localhost:%d", port)
    logger.info("HERMES_HOME: %s", HERMES_HOME)
    logger.info("Config: %s", CONFIG_FILE if CONFIG_FILE.exists() else "using defaults")
    uvicorn.run(app, host="127.0.0.1", port=port)
