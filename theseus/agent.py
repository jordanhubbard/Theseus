"""
theseus/agent.py

Thin wrapper around the configured AI agent.

Supported providers (set ai.provider in config.yaml):

  'auto'       Use claude CLI if in PATH, then openai endpoint, then any
               other known CLI agent (codex, droid) if in PATH.
  'claude'     claude CLI  (https://claude.ai/code)
               Invoked as: claude --print -  (prompt via stdin)
  'codex'      OpenAI Codex CLI  (https://github.com/openai/codex)
               Invoked as: codex --quiet -  (prompt via stdin)
  'droid'      Droid CLI  (configure ai.cli_agent_command = "droid")
               Same stdin protocol as claude/codex.
  'openai'     Any OpenAI-compatible HTTP endpoint (Ollama, LM Studio,
               OpenRouter, real OpenAI API, etc.)
               Set ai.openai_base_url and ai.openai_model.
  'cli_agent'  Generic fallback for any CLI agent that accepts a prompt
               via stdin and prints the response to stdout.
               Set ai.cli_agent_command (required) and optionally
               ai.cli_agent_args (list of extra flags before the prompt).

For any provider that exposes an OpenAI-compatible REST endpoint, prefer
'openai' and set ai.openai_base_url accordingly — it is more reliable than
subprocess-based invocation.
"""
from __future__ import annotations

import json
import shutil
import socket
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

# CLI agents with known invocation patterns.
# Each entry is (command, args_before_prompt, prompt_via_stdin).
_KNOWN_CLI_AGENTS: list[tuple[str, list[str], bool]] = [
    ("claude", ["--print", "-"], True),   # prompt passed via stdin as "-"
    ("codex",  ["--quiet", "-"], True),   # codex: --quiet suppresses spinner
    ("droid",  ["-"],            True),   # droid: prompt via stdin
]


def available(config: dict) -> bool:
    """Return True if any AI provider is configured and reachable."""
    provider = config.get("provider", "auto")
    if provider in ("claude", "auto") and _claude_in_path():
        return True
    if provider == "codex" and shutil.which("codex"):
        return True
    if provider == "droid" and shutil.which("droid"):
        return True
    if provider == "cli_agent" and config.get("cli_agent_command"):
        return bool(shutil.which(config["cli_agent_command"]))
    if provider in ("openai", "auto") and config.get("openai_base_url"):
        return True
    if provider == "auto":
        # auto: check all known CLI agents.
        # Use _claude_in_path() for 'claude' so tests can stub it without
        # also stubbing shutil.which (which is shared with codex/droid).
        for cmd, _, _ in _KNOWN_CLI_AGENTS:
            if cmd == "claude":
                if _claude_in_path():
                    return True
            elif shutil.which(cmd):
                return True
    return False


def run_prompt(prompt: str, config: dict, *, system: str = "", timeout: int = 0) -> str:
    """
    Send a prompt to the configured AI and return the text response.

    Args:
        prompt: the user-turn prompt text.
        config: AI config dict (from theseus.config.load()["ai"]).
        system: optional system prompt.
        timeout: seconds before giving up (0 = use provider default).

    Raises RuntimeError if no provider is available.
    """
    provider = config.get("provider", "auto")

    if provider == "openai":
        return _openai(prompt, config, system=system, timeout=timeout or 120)

    if provider == "claude":
        return _claude(prompt, system=system, timeout=timeout or 300)

    if provider == "codex":
        return _cli_invoke("codex", ["--quiet", "-"], True,
                           prompt, system=system, timeout=timeout or 300)

    if provider == "droid":
        return _cli_invoke("droid", ["-"], True,
                           prompt, system=system, timeout=timeout or 300)

    if provider == "cli_agent":
        cmd = config.get("cli_agent_command")
        if not cmd:
            raise RuntimeError("ai.cli_agent_command must be set when provider is 'cli_agent'")
        extra_args = config.get("cli_agent_args", ["-"])
        return _cli_invoke(cmd, extra_args, True,
                           prompt, system=system, timeout=timeout or 300)

    # auto: try known CLI agents in priority order, then openai endpoint
    if provider == "auto":
        # Special-case claude so tests can mock _claude() directly.
        if _claude_in_path():
            return _claude(prompt, system=system, timeout=timeout or 300)
        for cmd, args, via_stdin in _KNOWN_CLI_AGENTS:
            if cmd == "claude":
                continue  # already handled above
            if shutil.which(cmd):
                return _cli_invoke(cmd, args, via_stdin,
                                   prompt, system=system, timeout=timeout or 300)
        if config.get("openai_base_url"):
            return _openai(prompt, config, system=system, timeout=timeout or 120)

    if config.get("openai_base_url"):
        return _openai(prompt, config, system=system, timeout=timeout or 120)

    raise RuntimeError(
        "No AI provider available. Install claude, codex, or droid CLI, "
        "or set ai.openai_base_url in config.yaml. "
        "See docs/USER_GUIDE.md §2.4 for details."
    )


def _cli_invoke(
    command: str,
    args: list[str],
    via_stdin: bool,
    prompt: str,
    *,
    system: str = "",
    timeout: int = 300,
) -> str:
    """Invoke a CLI agent that accepts a prompt and prints the response."""
    argv = [command] + args
    # System prompt: pass as --system-prompt flag if the agent accepts it,
    # otherwise prepend to the user prompt (safest universal fallback).
    if system and command == "claude":
        argv += ["--system-prompt", system]
    elif system:
        prompt = f"{system}\n\n{prompt}"

    try:
        r = subprocess.run(
            argv,
            input=prompt if via_stdin else None,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"{command} CLI timed out after {timeout}s")
    except FileNotFoundError:
        raise RuntimeError(f"{command} CLI not found in PATH")
    if r.returncode != 0:
        raise RuntimeError(f"{command} CLI failed (exit {r.returncode}): {r.stderr.strip()}")
    return r.stdout.strip()


# Keep the private name for any callers that used the old internal function.
def _claude_in_path() -> bool:
    return bool(shutil.which("claude"))


def _claude(prompt: str, *, system: str = "", timeout: int = 300) -> str:
    return _cli_invoke("claude", ["--print", "-"], True, prompt,
                       system=system, timeout=timeout)


def _openai(prompt: str, config: dict, *, system: str = "", timeout: int = 120) -> str:
    base = config.get("openai_base_url", "http://localhost:11434/v1").rstrip("/")
    key = config.get("openai_api_key", "") or "none"
    model = config.get("openai_model", "gpt-4o")

    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = json.dumps({"model": model, "messages": messages, "temperature": 0.2, "max_tokens": 16000}).encode()
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
    except (urllib.error.URLError, socket.timeout, TimeoutError) as exc:
        raise RuntimeError(f"OpenAI API request failed: {exc}") from exc
    except (KeyError, IndexError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"OpenAI API unexpected response: {exc}") from exc
