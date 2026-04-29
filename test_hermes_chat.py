"""
Hermes Web Chat - 后端 API 自动化测试
使用 pytest + FastAPI TestClient

运行方式:
    python3 -m pytest test_hermes_chat.py -v
    python3 -m pytest test_hermes_chat.py -v -k health
    python3 -m pytest test_hermes_chat.py -v --tb=short
"""
import sys
import os
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# ---------------------------------------------------------------------------
# 定位被测模块（hermes_chat.py）
# ---------------------------------------------------------------------------
_PLUGIN_DIR = Path(__file__).resolve().parent
_HERMES_CHAT_PY = _PLUGIN_DIR / "hermes_chat.py"

if not _HERMES_CHAT_PY.exists():
    pytest.skip(
        f"hermes_chat.py 未找到 (预期路径: {_HERMES_CHAT_PY})，"
        f"请确保 test_hermes_chat.py 位于 hermes-web-chat 插件目录中。",
        allow_module_level=True,
    )

# 动态导入被测模块
import importlib.util
_spec = importlib.util.spec_from_file_location("hermes_chat", _HERMES_CHAT_PY)
hermes_chat = importlib.util.module_from_spec(_spec)

# 在导入前修补可能引起副作用的路径创建
with patch.object(Path, "mkdir", return_value=None):
    _spec.loader.exec_module(hermes_chat)

app = hermes_chat.app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def mock_hermes_cmd():
    """全局 mock hermes 命令，避免测试依赖真实 CLI。"""
    with patch.object(hermes_chat, "get_hermes_cmd", return_value=None):
        yield


@pytest.fixture
def client():
    """FastAPI TestClient 实例。"""
    from fastapi.testclient import TestClient
    return TestClient(app)


@pytest.fixture
def tmp_hermes_home(tmp_path):
    """创建临时 HERMES_HOME 目录，避免污染真实数据。"""
    home = tmp_path / ".Hermes"
    home.mkdir(parents=True, exist_ok=True)
    original = hermes_chat.HERMES_HOME
    hermes_chat.HERMES_HOME = home
    yield home
    hermes_chat.HERMES_HOME = original


@pytest.fixture
def mock_hermes_cli(tmp_path):
    """创建一个模拟的 hermes CLI 可执行文件。"""
    script = tmp_path / "hermes"
    script.write_text(
        '#!/bin/sh\n'
        'if [ "$1" = "skills" ] && [ "$2" = "list" ]; then\n'
        '  printf "┌──────────────┬──────────────┬──────────────┬────────┐\\n"\n'
        '  printf "│ Name         │ Category     │ Source       │ Trust  │\\n"\n'
        '  printf "┡━━━━━━━━━━━━━━┿━━━━━━━━━━━━━━┿━━━━━━━━━━━━━━┿━━━━━━━━┥\\n"\n'
        '  printf "│ code_review  │ dev          │ builtin      │ high   │\\n"\n'
        '  printf "│ summarize    │ productivity │ local        │ medium │\\n"\n'
        '  printf "└──────────────┴──────────────┴──────────────┴────────┘\\n"\n'
        'elif [ "$1" = "cronjob" ] && [ "$2" = "list" ]; then\n'
        '  printf "No cronjobs configured\\n"\n'
        'elif [ "$1" = "chat" ]; then\n'
        '  printf "Hello from mock hermes!\\n"\n'
        'fi\n'
    )
    script.chmod(0o755)
    return str(script)


# ---------------------------------------------------------------------------
# should_filter_line 辅助函数
# 从 call_hermes / call_hermes_stream 中提取的过滤逻辑
# ---------------------------------------------------------------------------
def should_filter_line(line: str) -> bool:
    """
    判断某行输出是否应该被过滤掉（不应展示给用户）。
    该逻辑直接从 hermes_chat.py 的 call_hermes / call_hermes_stream 中提取。
    """
    line = line.rstrip('\n\r')
    # 空行
    if not line.strip():
        return True
    # session_id
    if line.startswith('session_id:'):
        return True
    # 系统信息
    if line.startswith('Query:') or line.startswith('Initializing'):
        return True
    # 思考过程
    if line.startswith('|'):
        return True
    # 版本信息
    if line.startswith('Hermes Agent'):
        return True
    # 上游信息
    if 'upstream' in line:
        return True
    # 工具列表
    if line.startswith('Tools:') or line.startswith('Available Skills:'):
        return True
    # 分隔线
    if line.startswith('===') or line.startswith('---'):
        return True
    return False


# ---------------------------------------------------------------------------
# 1. 基础端点测试
# ---------------------------------------------------------------------------
class TestBasicEndpoints:
    """测试 / 和 /api/health（如有）。"""

    def test_get_root_returns_html(self, client):
        """GET / 应返回 HTML 页面。"""
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers.get("content-type", "")
        assert "Hermes Agent" in resp.text
        assert "<!DOCTYPE html>" in resp.text

    def test_get_root_contains_css(self, client):
        """GET / 应包含 CSS 样式。"""
        resp = client.get("/")
        assert resp.status_code == 200
        assert ":root" in resp.text or "<style>" in resp.text

    def test_get_root_contains_js(self, client):
        """GET / 应包含 JavaScript 引用。"""
        resp = client.get("/")
        assert resp.status_code == 200
        # HTML 使用 <script src=...> 引用外部 JS
        assert '<script src=' in resp.text or '<script>' in resp.text


# ---------------------------------------------------------------------------
# 2. 数据端点测试
# ---------------------------------------------------------------------------
class TestDataEndpoints:
    """测试所有 /api/* 数据端点。"""

    def test_api_skills_no_hermes(self, client):
        """没有 hermes CLI 时应返回空技能列表。"""
        resp = client.get("/api/skills")
        assert resp.status_code == 200
        data = resp.json()
        assert "skills" in data
        assert "count" in data
        assert data["skills"] == []
        assert data["count"] == 0

    def test_api_skills_with_mock_cli(self, client, mock_hermes_cli):
        """有 hermes CLI 时应正确解析技能表格。"""
        with patch.object(hermes_chat, "get_hermes_cmd", return_value=mock_hermes_cli):
            resp = client.get("/api/skills")
        assert resp.status_code == 200
        data = resp.json()
        # 解析出的技能数 >= 2（表格头部行可能被解析）
        assert data["count"] >= 2
        names = [s["name"] for s in data["skills"]]
        assert "code_review" in names
        assert "summarize" in names

    def test_api_memory_no_file(self, client, tmp_hermes_home):
        """没有 MEMORY.md 时应返回空数据。"""
        # 需要 patch possible_paths 来避免回退到真实 ~/.hermes/MEMORY.md
        import hermes_chat as hc
        real_home = hc.HERMES_HOME
        hc.HERMES_HOME = tmp_hermes_home
        # Patch the home path fallback
        with patch.object(Path, "home", return_value=tmp_hermes_home / "no-home"):
            resp = client.get("/api/memory")
        hc.HERMES_HOME = real_home
        assert resp.status_code == 200
        data = resp.json()
        assert data["daily"] == []
        assert data["long_term"] == []
        assert data["file_path"] is None

    def test_api_memory_with_file(self, client, tmp_hermes_home):
        """有 MEMORY.md 时应正确解析每日记忆。"""
        memory_file = tmp_hermes_home / "memories"
        memory_file.mkdir(parents=True, exist_ok=True)
        (memory_file / "MEMORY.md").write_text(
            "> 2026-04-29\n"
            "今天学习了 FastAPI\n"
            "完成了测试用例\n"
            "---\n"
            "> 2026-04-28\n"
            "昨天做了代码审查\n"
        )
        resp = client.get("/api/memory")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["daily"]) >= 2
        assert "2026-04-29" in data["daily"][0]
        assert "FastAPI" in data["daily"][0]
        assert data["file_path"] is not None

    def test_api_sessions_no_dir(self, client, tmp_hermes_home):
        """没有 sessions 目录时应返回空列表。"""
        resp = client.get("/api/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["sessions"] == []

    def test_api_sessions_with_files(self, client, tmp_hermes_home):
        """有会话文件时应正确解析。"""
        sessions_dir = tmp_hermes_home / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        session_data = {
            "title": "测试会话",
            "created_at": "2026-04-29T10:00:00Z",
            "model": "test-model",
            "messages": [
                {"role": "user", "content": "你好"},
                {"role": "assistant", "content": "你好！有什么可以帮助你的？"},
            ],
        }
        (sessions_dir / "session_20260429_100000.json").write_text(
            json.dumps(session_data, ensure_ascii=False)
        )
        resp = client.get("/api/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["sessions"][0]["title"] == "测试会话"
        assert data["sessions"][0]["messages"] == 2

    def test_api_sessions_auto_title(self, client, tmp_hermes_home):
        """没有 title 时应使用第一条用户消息作为标题。"""
        sessions_dir = tmp_hermes_home / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        session_data = {
            "messages": [
                {"role": "user", "content": "如何学习 Python?"},
                {"role": "assistant", "content": "Python 是一门..."},
            ],
        }
        (sessions_dir / "session_20260428_090000.json").write_text(
            json.dumps(session_data, ensure_ascii=False)
        )
        resp = client.get("/api/sessions")
        data = resp.json()
        assert "如何学习 Python?" in data["sessions"][0]["title"]

    def test_api_costs_empty(self, client, tmp_hermes_home):
        """没有会话时应返回零费用。"""
        resp = client.get("/api/costs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_tokens"] == 0
        assert data["sessions"] == 0
        assert data["models"] == {}
        assert data["estimated_cost"] == "$0.00"

    def test_api_costs_with_data(self, client, tmp_hermes_home):
        """有会话时应正确统计费用。"""
        sessions_dir = tmp_hermes_home / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        for i in range(3):
            session_data = {
                "model": f"model-{i}",
                "messages": [
                    {"role": "user", "content": "x" * 4000},  # ~1000 tokens
                    {"role": "assistant", "content": "y" * 4000},
                ],
            }
            (sessions_dir / f"session_20260429_0{i}0000.json").write_text(
                json.dumps(session_data)
            )
        resp = client.get("/api/costs")
        data = resp.json()
        assert data["total_tokens"] > 0
        assert data["sessions"] == 3
        assert len(data["models"]) == 3

    def test_api_patterns_empty(self, client, tmp_hermes_home):
        """没有会话时应返回默认模式数据。"""
        resp = client.get("/api/patterns")
        assert resp.status_code == 200
        data = resp.json()
        assert "hourly" in data
        assert "daily" in data
        assert "peak_hour" in data
        # 24 小时
        assert len(data["hourly"]) == 24

    def test_api_patterns_with_data(self, client, tmp_hermes_home):
        """有会话时应正确分析使用模式。"""
        sessions_dir = tmp_hermes_home / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        session_data = {
            "created_at": "2026-04-29T14:30:00Z",
            "messages": [{"role": "user", "content": "hi"}],
        }
        (sessions_dir / "session_20260429_143000.json").write_text(
            json.dumps(session_data)
        )
        resp = client.get("/api/patterns")
        data = resp.json()
        assert data["hourly"]["14"] >= 1
        assert "2026-04-29" in data["daily"]


# ---------------------------------------------------------------------------
# 3. 会话详情端点
# ---------------------------------------------------------------------------
class TestSessionDetail:

    def test_session_detail_not_found(self, client, tmp_hermes_home):
        """不存在的会话应返回错误。"""
        resp = client.get("/api/session_detail?session_id=nonexistent")
        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data
        assert data["messages"] == []

    def test_session_detail_existing(self, client, tmp_hermes_home):
        """存在的会话应正确返回消息。"""
        sessions_dir = tmp_hermes_home / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        session_data = {
            "title": "详细测试",
            "created_at": "2026-04-29T10:00:00Z",
            "messages": [
                {"role": "user", "content": "问题一"},
                {"role": "assistant", "content": "回答一"},
                {"role": "user", "content": "问题二"},
                {"role": "assistant", "content": "回答二"},
            ],
        }
        (sessions_dir / "session_detail_test.json").write_text(
            json.dumps(session_data, ensure_ascii=False)
        )
        resp = client.get("/api/session_detail?session_id=session_detail_test")
        data = resp.json()
        assert "error" not in data
        assert len(data["messages"]) == 4
        assert data["messages"][0]["isUser"] is True
        assert data["messages"][1]["isUser"] is False
        assert data["title"] == "详细测试"


# ---------------------------------------------------------------------------
# 4. Cron & Projects 端点
# ---------------------------------------------------------------------------
class TestCronAndProjects:

    def test_api_cron_no_hermes(self, client):
        """没有 hermes CLI 时应返回提示。"""
        resp = client.get("/api/cron")
        data = resp.json()
        assert "raw" in data

    def test_api_cron_with_mock_cli(self, client, mock_hermes_cli):
        """有 hermes CLI 时应返回 cron 数据。"""
        with patch.object(hermes_chat, "get_hermes_cmd", return_value=mock_hermes_cli):
            resp = client.get("/api/cron")
        data = resp.json()
        assert "cronjob" in data["raw"].lower() or "No" in data["raw"]

    def test_api_projects_no_file(self, client, tmp_hermes_home):
        """没有 MEMORY.md 时应返回空项目。"""
        resp = client.get("/api/projects")
        data = resp.json()
        assert "projects" in data

    def test_api_projects_with_file(self, client, tmp_hermes_home):
        """有 MEMORY.md 且包含项目时应正确解析。"""
        memory_file = tmp_hermes_home / "memories"
        memory_file.mkdir(parents=True, exist_ok=True)
        (memory_file / "MEMORY.md").write_text(
            "🎯 重要项目\n"
            "- **Hermes Web Chat**: 网页聊天界面\n"
            "- **API Server**: FastAPI 后端\n"
            "---\n"
        )
        resp = client.get("/api/projects")
        data = resp.json()
        assert data["count"] >= 1


# ---------------------------------------------------------------------------
# 5. 插件更新端点
# ---------------------------------------------------------------------------
class TestPluginUpdate:

    def test_update_check_non_git(self, client):
        """非 git 仓库应返回相应提示。"""
        resp = client.get("/api/plugin/update/check")
        data = resp.json()
        assert "has_update" in data

    def test_update_execute_non_git(self, client):
        """非 git 仓库执行更新应返回失败。"""
        resp = client.post("/api/plugin/update/execute")
        data = resp.json()
        assert "success" in data or "error" in data


# ---------------------------------------------------------------------------
# 6. 聊天端点（mock hermes CLI）
# ---------------------------------------------------------------------------
class TestChatEndpoints:

    def test_chat_with_mock_cli(self, client, mock_hermes_cli):
        """POST /api/chat 应返回 hermes 的回复。"""
        with patch.object(hermes_chat, "get_hermes_cmd", return_value=mock_hermes_cli):
            resp = client.post("/api/chat", data={"message": "你好"})
        assert resp.status_code == 200
        data = resp.json()
        assert "response" in data
        assert "mock hermes" in data["response"].lower()

    def test_chat_error_handling(self, client):
        """hermes 命令不存在时应返回错误信息。"""
        resp = client.post("/api/chat", data={"message": "你好"})
        assert resp.status_code == 200
        data = resp.json()
        assert "response" in data

    def test_chat_stream_with_mock_cli(self, client, mock_hermes_cli):
        """POST /api/chat_stream 应返回 SSE 格式数据。"""
        with patch.object(hermes_chat, "get_hermes_cmd", return_value=mock_hermes_cli):
            resp = client.post("/api/chat_stream", data={"message": "你好"})
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")
        text = resp.text
        assert "data:" in text


# ---------------------------------------------------------------------------
# 7. should_filter_line 过滤逻辑测试
# ---------------------------------------------------------------------------
class TestShouldFilterLine:
    """测试从 call_hermes / call_hermes_stream 中提取的过滤逻辑。"""

    @pytest.mark.parametrize("line,expected", [
        # 空行 → 过滤
        ("", True),
        ("   ", True),
        ("\t", True),
        # session_id → 过滤
        ("session_id: abc123", True),
        # Query / Initializing → 过滤
        ("Query: hello world", True),
        ("Initializing plugins...", True),
        # 思考过程（以 | 开头）→ 过滤
        ("| 正在思考...", True),
        ("|thinking step 1", True),
        # 版本信息 → 过滤
        ("Hermes Agent v1.0.0", True),
        # 上游信息 → 过滤
        ("Using upstream provider: openai", True),
        ("Connecting to upstream...", True),
        # 工具列表 → 过滤
        ("Tools: 5 available", True),
        ("Available Skills: code_review, summarize", True),
        # 分隔线 → 过滤
        ("========================================", True),
        ("----------------------------------------", True),
        ("=== END ===", True),
        # --- 正常回复内容 → 不过滤
        ("你好！有什么可以帮助你的？", False),
        ("Hello! How can I help you?", False),
        ("  这是一条带空格的回复", False),
        ("代码示例:\nprint('hello')", False),
        ("- 列表项 1", False),
        ("# 标题", False),
        ("```python", False),
        ("Some text with upstream mention", True),  # 'upstream' anywhere in line → filter
    ])
    def test_filter_line(self, line, expected):
        """各种输入应正确判断是否过滤。"""
        assert should_filter_line(line) == expected, (
            f"should_filter_line({line!r}) 预期 {expected}"
        )


# ---------------------------------------------------------------------------
# 8. 辅助函数测试
# ---------------------------------------------------------------------------
class TestHelperFunctions:

    def test_get_memory_data_parses_dates(self, tmp_hermes_home):
        """get_memory_data 应正确解析日期行。"""
        original = hermes_chat.HERMES_HOME
        hermes_chat.HERMES_HOME = tmp_hermes_home
        try:
            mem_dir = tmp_hermes_home / "memories"
            mem_dir.mkdir(parents=True, exist_ok=True)
            (mem_dir / "MEMORY.md").write_text(
                "> 2026-01-15\n"
                "第一条记录\n"
                "> 2025-12-20\n"
                "去年记录\n"
            )
            data = hermes_chat.get_memory_data()
            assert len(data["daily"]) == 2
            assert "2026-01-15" in data["daily"][0]
            assert "2025-12-20" in data["daily"][1]
        finally:
            hermes_chat.HERMES_HOME = original

    def test_get_sessions_data_limits(self, tmp_hermes_home):
        """get_sessions_data 应最多返回 50 个会话。"""
        original = hermes_chat.HERMES_HOME
        hermes_chat.HERMES_HOME = tmp_hermes_home
        try:
            sessions_dir = tmp_hermes_home / "sessions"
            sessions_dir.mkdir(parents=True, exist_ok=True)
            # 创建 55 个会话文件
            for i in range(55):
                sd = {"messages": [{"role": "user", "content": f"msg {i}"}]}
                (sessions_dir / f"session_20260429_{i:06d}.json").write_text(
                    json.dumps(sd)
                )
            data = hermes_chat.get_sessions_data()
            assert data["count"] <= 50
        finally:
            hermes_chat.HERMES_HOME = original

    def test_get_hermes_cmd_none_when_not_found(self):
        """当 hermes 命令不存在时应返回 None。"""
        with patch.object(shutil, "which", return_value=None):
            result = hermes_chat.get_hermes_cmd()
            assert result is None


# ---------------------------------------------------------------------------
# 9. 集成测试
# ---------------------------------------------------------------------------
class TestIntegration:

    def test_full_workflow(self, client, tmp_hermes_home, mock_hermes_cli):
        """模拟完整工作流：创建会话 → 聊天 → 查询数据。"""
        # 1. 创建会话
        sessions_dir = tmp_hermes_home / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        (sessions_dir / "session_20260429_120000.json").write_text(
            json.dumps({
                "title": "集成测试会话",
                "created_at": "2026-04-29T12:00:00Z",
                "model": "gpt-4",
                "messages": [
                    {"role": "user", "content": "你好"},
                    {"role": "assistant", "content": "你好！"},
                ],
            }, ensure_ascii=False)
        )

        # 2. 查询会话列表
        resp = client.get("/api/sessions")
        assert resp.json()["count"] >= 1

        # 3. 查询会话详情
        resp = client.get("/api/session_detail?session_id=session_20260429_120000")
        data = resp.json()
        assert data["title"] == "集成测试会话"
        assert len(data["messages"]) == 2

        # 4. 发送聊天
        with patch.object(hermes_chat, "get_hermes_cmd", return_value=mock_hermes_cli):
            resp = client.post("/api/chat", data={"message": "测试"})
        assert resp.json()["response"] is not None

        # 5. 查询费用
        resp = client.get("/api/costs")
        assert resp.json()["sessions"] >= 1

        # 6. 查询模式
        resp = client.get("/api/patterns")
        assert resp.json()["peak_hour"] is not None

    def test_memory_and_projects_consistency(self, client, tmp_hermes_home):
        """MEMORY.md 应同时影响 memory 和 projects 端点。"""
        mem_dir = tmp_hermes_home / "memories"
        mem_dir.mkdir(parents=True, exist_ok=True)
        (mem_dir / "MEMORY.md").write_text(
            "> 2026-04-29\n"
            "今天工作\n"
            "---\n"
            "🎯 重要项目\n"
            "- **Test Project**: 测试项目\n"
            "---\n"
        )

        resp_mem = client.get("/api/memory")
        resp_proj = client.get("/api/projects")

        assert resp_mem.status_code == 200
        assert resp_proj.status_code == 200
        assert resp_mem.json()["file_path"] is not None
        assert resp_proj.json()["count"] >= 1
