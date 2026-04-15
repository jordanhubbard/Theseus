"""
theseus/agent.py

Thin wrapper around the configured AI agent.

If the 'claude' CLI is in PATH and provider is not 'openai', runs prompts
via subprocess.  Otherwise, calls an OpenAI-compatible HTTP API using
stdlib urllib only (no third-party dependencies).
"""
from __future__ import annotations

import json
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path


def available(config: dict) -> bool:
    """Return True if any AI provider is configured and reachable."""
    provider = config.get("provider", "auto")
    if provider in ("claude", "auto") and _claude_in_path():
        return True
    if provider in ("openai", "auto") and config.get("openai_base_url"):
        return True
    return False


def run_prompt(prompt: str, config: dict, *, system: str = "", timeout: int = 0) -> str:
    """
    Send a prompt to the configured AI and return the text response.

    Args:
        prompt: the user-turn prompt text.
        config: AI config dict (from theseus.config.load()["ai"]).
        system: optional system prompt.
        timeout: seconds before giving up (0 = use provider default:
                 300s for claude CLI, 120s for OpenAI HTTP).

    Raises RuntimeError if no provider is available.
    """
    provider = config.get("provider", "auto")
    if provider == "openai":
        return _openai(prompt, config, system=system, timeout=timeout or 120)
    if provider == "claude" or (provider == "auto" and _claude_in_path()):
        return _claude(prompt, system=system, timeout=timeout or 300)
    if config.get("openai_base_url"):
        return _openai(prompt, config, system=system, timeout=timeout or 120)
    raise RuntimeError(
        "No AI provider available. Install the claude CLI or set "
        "ai.openai_base_url in config.yaml."
    )


def _claude_in_path() -> bool:
    return shutil.which("claude") is not None


def _claude(prompt: str, *, system: str = "", timeout: int = 300) -> str:
    # Pass the prompt via stdin ("-") to avoid OS argument-length limits on
    # large synthesis prompts.  The system prompt is still passed as an arg
    # since it is typically short.
    argv = ["claude", "--print", "-"]
    if system:
        argv += ["--system-prompt", system]
    try:
        r = subprocess.run(
            argv, input=prompt, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"claude CLI timed out after {timeout}s")
    if r.returncode != 0:
        raise RuntimeError(f"claude CLI failed: {r.stderr.strip()}")
    return r.stdout.strip()


def _openai(prompt: str, config: dict, *, system: str = "", timeout: int = 120) -> str:
    base = config.get("openai_base_url", "http://localhost:11434/v1").rstrip("/")
    key = config.get("openai_api_key", "") or "none"
    model = config.get("openai_model", "gpt-4o")

    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = json.dumps({"model": model, "messages": messages, "temperature": 0.2}).encode()
    req = urllib.request.Request(
        f"{base}/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"].strip()
    except urllib.error.URLError as exc:
        raise RuntimeError(f"OpenAI API request failed: {exc}") from exc
    except (KeyError, IndexError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"OpenAI API unexpected response: {exc}") from exc
