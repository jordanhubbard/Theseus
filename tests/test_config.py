"""
Tests for theseus/config.py
"""
import json
import tempfile
from pathlib import Path

import pytest

from theseus.config import load, _deep_merge, _parse_simple, _scalar, _strip_comment


# ---------------------------------------------------------------------------
# load() tests
# ---------------------------------------------------------------------------

def test_load_no_file_returns_defaults(tmp_path):
    """load() with a non-existent path returns defaults."""
    cfg = load(tmp_path / "nonexistent.yaml")
    assert cfg["ai"]["provider"] == "auto"
    assert cfg["ai"]["openai_model"] == "gpt-4o"
    assert cfg["artifact_store"]["url"] == ""
    assert cfg["targets"] == []


def test_load_partial_config_merges_with_defaults(tmp_path):
    """load() merges partial config over defaults."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "ai:\n  provider: claude\n  openai_model: my-model\n",
        encoding="utf-8",
    )
    cfg = load(config_file)
    assert cfg["ai"]["provider"] == "claude"
    assert cfg["ai"]["openai_model"] == "my-model"
    # Defaults still present
    assert cfg["ai"]["openai_base_url"] == "http://localhost:11434/v1"
    assert cfg["artifact_store"]["url"] == ""


def test_load_full_config(tmp_path):
    """load() correctly parses all sections."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "ai:\n"
        "  provider: openai\n"
        "  openai_base_url: http://example.com/v1\n"
        "  openai_api_key: secret\n"
        "  openai_model: gpt-3.5-turbo\n"
        "artifact_store:\n"
        "  url: s3://my-bucket/theseus\n"
        "targets:\n"
        "  - name: myhost\n"
        "    os: linux\n"
        "    arch: amd64\n",
        encoding="utf-8",
    )
    cfg = load(config_file)
    assert cfg["ai"]["provider"] == "openai"
    assert cfg["ai"]["openai_base_url"] == "http://example.com/v1"
    assert cfg["artifact_store"]["url"] == "s3://my-bucket/theseus"
    assert len(cfg["targets"]) == 1
    assert cfg["targets"][0]["name"] == "myhost"


# ---------------------------------------------------------------------------
# _parse_simple() tests
# ---------------------------------------------------------------------------

def test_parse_simple_nested_mapping():
    text = "ai:\n  provider: claude\n  openai_model: gpt-4o\n"
    result = _parse_simple(text)
    assert result["ai"]["provider"] == "claude"
    assert result["ai"]["openai_model"] == "gpt-4o"


def test_parse_simple_list_of_mappings():
    text = (
        "targets:\n"
        "  - name: myhost\n"
        "    os: linux\n"
        "    arch: amd64\n"
        "  - name: other\n"
        "    os: darwin\n"
    )
    result = _parse_simple(text)
    assert len(result["targets"]) == 2
    assert result["targets"][0]["name"] == "myhost"
    assert result["targets"][0]["os"] == "linux"
    assert result["targets"][1]["name"] == "other"


def test_parse_simple_booleans():
    text = "local: true\nremote: false\n"
    result = _parse_simple(text)
    assert result["local"] is True
    assert result["remote"] is False


def test_parse_simple_null():
    text = "key: null\nother: ~\n"
    result = _parse_simple(text)
    assert result["key"] is None
    assert result["other"] is None


def test_parse_simple_strings_with_spaces():
    text = 'url: "http://localhost:11434/v1"\n'
    result = _parse_simple(text)
    assert result["url"] == "http://localhost:11434/v1"


def test_parse_simple_ignores_comments():
    text = "# This is a comment\nkey: value\n# Another comment\n"
    result = _parse_simple(text)
    assert result["key"] == "value"
    assert len(result) == 1


def test_parse_simple_inline_comment():
    text = "key: value # inline comment\n"
    result = _parse_simple(text)
    assert result["key"] == "value"


def test_parse_simple_integer():
    text = "port: 8080\n"
    result = _parse_simple(text)
    assert result["port"] == 8080


# ---------------------------------------------------------------------------
# _deep_merge() tests
# ---------------------------------------------------------------------------

def test_deep_merge_flat():
    base = {"a": 1, "b": 2}
    override = {"b": 99, "c": 3}
    result = _deep_merge(base, override)
    assert result == {"a": 1, "b": 99, "c": 3}


def test_deep_merge_nested():
    base = {"ai": {"provider": "auto", "model": "gpt-4o"}}
    override = {"ai": {"provider": "claude"}}
    result = _deep_merge(base, override)
    assert result["ai"]["provider"] == "claude"
    assert result["ai"]["model"] == "gpt-4o"


def test_deep_merge_does_not_mutate_base():
    base = {"a": {"x": 1}}
    override = {"a": {"y": 2}}
    _deep_merge(base, override)
    assert "y" not in base["a"]


def test_deep_merge_override_non_dict_replaces():
    base = {"a": {"x": 1}}
    override = {"a": "string"}
    result = _deep_merge(base, override)
    assert result["a"] == "string"


def test_deep_merge_empty_override():
    base = {"a": 1, "b": 2}
    result = _deep_merge(base, {})
    assert result == {"a": 1, "b": 2}
