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


def run_prompt(prompt: str, config: dict, *, system: str = "") -> str:
    """
    Send a prompt to the configured AI and return the text response.
    Raises RuntimeError if no provider is available.
    """
    provider = config.get("provider", "auto")
    if provider == "openai":
        return _openai(prompt, config, system=system)
    if provider == "claude" or (provider == "auto" and _claude_in_path()):
        return _claude(prompt, system=system)
    if config.get("openai_base_url"):
        return _openai(prompt, config, system=system)
    raise RuntimeError(
        "No AI provider available. Install the claude CLI or set "
        "ai.openai_base_url in config.yaml."
    )


def _claude_in_path() -> bool:
    return shutil.which("claude") is not None


def _claude(prompt: str, *, system: str = "") -> str:
    argv = ["claude", "--print", prompt]
    if system:
        argv += ["--system-prompt", system]
    r = subprocess.run(argv, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(f"claude CLI failed: {r.stderr.strip()}")
    return r.stdout.strip()


def _openai(prompt: str, config: dict, *, system: str = "") -> str:
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
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"].strip()
    except urllib.error.URLError as exc:
        raise RuntimeError(f"OpenAI API request failed: {exc}") from exc
    except (KeyError, IndexError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"OpenAI API unexpected response: {exc}") from exc
