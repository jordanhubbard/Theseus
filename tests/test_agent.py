"""
Tests for theseus/agent.py
"""
import json
import unittest.mock as mock
from unittest.mock import MagicMock, patch, call
import urllib.error

import pytest

from theseus import agent


# ---------------------------------------------------------------------------
# available() tests
# ---------------------------------------------------------------------------

def test_available_false_when_no_config():
    # When no CLI provider is in PATH and no openai_base_url is set, returns False.
    with patch("theseus.agent._claude_in_path", return_value=False), \
         patch("theseus.agent.shutil.which", return_value=None):
        assert agent.available({}) is False


def test_available_true_when_claude_in_path():
    with patch("theseus.agent._claude_in_path", return_value=True):
        assert agent.available({"provider": "auto"}) is True


def test_available_true_when_openai_base_url_set():
    cfg = {"provider": "openai", "openai_base_url": "http://localhost:11434/v1"}
    # Even without claude in path, openai should make it available
    with patch("theseus.agent._claude_in_path", return_value=False):
        assert agent.available(cfg) is True


def test_available_false_when_openai_provider_no_url():
    cfg = {"provider": "openai", "openai_base_url": ""}
    with patch("theseus.agent._claude_in_path", return_value=False):
        assert agent.available(cfg) is False


def test_available_auto_with_openai_url_no_claude():
    cfg = {"provider": "auto", "openai_base_url": "http://localhost:11434/v1"}
    with patch("theseus.agent._claude_in_path", return_value=False):
        assert agent.available(cfg) is True


# ---------------------------------------------------------------------------
# run_prompt() — error path
# ---------------------------------------------------------------------------

def test_run_prompt_raises_when_no_provider():
    cfg = {"provider": "auto", "openai_base_url": ""}
    with patch("theseus.agent._claude_in_path", return_value=False), \
         patch("theseus.agent.shutil.which", return_value=None):
        with pytest.raises(RuntimeError, match="No AI provider"):
            agent.run_prompt("hello", cfg)


def test_run_prompt_raises_when_provider_none():
    with patch("theseus.agent._claude_in_path", return_value=False), \
         patch("theseus.agent.shutil.which", return_value=None):
        with pytest.raises(RuntimeError):
            agent.run_prompt("hello", {})


# ---------------------------------------------------------------------------
# run_prompt() — claude provider
# ---------------------------------------------------------------------------

def test_run_prompt_calls_claude_when_provider_claude():
    cfg = {"provider": "claude"}
    with patch("theseus.agent._claude", return_value="response text") as mock_claude:
        result = agent.run_prompt("my prompt", cfg)
    mock_claude.assert_called_once_with("my prompt", system="", timeout=300)
    assert result == "response text"


def test_run_prompt_calls_claude_when_auto_and_claude_in_path():
    cfg = {"provider": "auto"}
    with patch("theseus.agent._claude_in_path", return_value=True):
        with patch("theseus.agent._claude", return_value="claude says hi") as mock_claude:
            result = agent.run_prompt("prompt", cfg)
    assert result == "claude says hi"


# ---------------------------------------------------------------------------
# run_prompt() — openai provider
# ---------------------------------------------------------------------------

def test_run_prompt_calls_openai_when_provider_openai():
    cfg = {
        "provider": "openai",
        "openai_base_url": "http://localhost:11434/v1",
        "openai_api_key": "",
        "openai_model": "gpt-4o",
    }
    with patch("theseus.agent._openai", return_value="openai response") as mock_oi:
        result = agent.run_prompt("my prompt", cfg)
    mock_oi.assert_called_once_with("my prompt", cfg, system="", timeout=120)
    assert result == "openai response"


# ---------------------------------------------------------------------------
# _openai() — HTTP request construction
# ---------------------------------------------------------------------------

def _make_openai_response(content: str) -> MagicMock:
    """Build a fake urllib response object."""
    resp_data = json.dumps({
        "choices": [{"message": {"content": content}}]
    }).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = resp_data
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def test_openai_constructs_correct_payload():
    cfg = {
        "openai_base_url": "http://localhost:11434/v1",
        "openai_api_key": "mykey",
        "openai_model": "gpt-4o",
    }
    mock_resp = _make_openai_response("hello from model")

    captured_req = []

    def fake_urlopen(req, timeout=None):
        captured_req.append(req)
        return mock_resp

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        result = agent._openai("test prompt", cfg)

    assert result == "hello from model"
    assert len(captured_req) == 1
    req = captured_req[0]
    payload = json.loads(req.data.decode())
    assert payload["model"] == "gpt-4o"
    assert payload["messages"][-1]["content"] == "test prompt"
    assert payload["messages"][-1]["role"] == "user"
    assert req.get_header("Authorization") == "Bearer mykey"


def test_openai_includes_system_message_when_provided():
    cfg = {
        "openai_base_url": "http://localhost:11434/v1",
        "openai_api_key": "",
        "openai_model": "gpt-4o",
    }
    mock_resp = _make_openai_response("ok")
    captured_req = []

    def fake_urlopen(req, timeout=None):
        captured_req.append(req)
        return mock_resp

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        agent._openai("user prompt", cfg, system="you are a bot")

    payload = json.loads(captured_req[0].data.decode())
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][0]["content"] == "you are a bot"
    assert payload["messages"][1]["role"] == "user"


def test_openai_raises_runtime_error_on_url_error():
    cfg = {
        "openai_base_url": "http://localhost:11434/v1",
        "openai_api_key": "",
        "openai_model": "gpt-4o",
    }
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("connection refused")):
        with pytest.raises(RuntimeError, match="OpenAI API request failed"):
            agent._openai("prompt", cfg)


def test_openai_raises_runtime_error_on_bad_json():
    cfg = {
        "openai_base_url": "http://localhost:11434/v1",
        "openai_api_key": "",
        "openai_model": "gpt-4o",
    }
    mock_resp = MagicMock()
    mock_resp.read.return_value = b"not json at all"
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        with pytest.raises(RuntimeError, match="OpenAI API unexpected response"):
            agent._openai("prompt", cfg)
