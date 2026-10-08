"""Issue tracking is GitHub Issues, not Beads/Dolt."""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def test_beads_directory_is_gitignored():
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".beads/" in text


def test_agent_guides_use_github_issues():
    for name in ("AGENTS.md", "CLAUDE.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        assert "BEGIN BEADS INTEGRATION" not in text
        assert "bd dolt" not in text
        assert "GitHub Issues" in text
