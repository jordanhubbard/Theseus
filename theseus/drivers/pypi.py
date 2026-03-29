"""
theseus/drivers/pypi.py

Render a canonical package record as PyPI installation artifacts:
  requirements.txt  — pinned install requirement
  pyproject.toml    — minimal project descriptor for the dependency
"""
from __future__ import annotations

import json


def render(record: dict) -> dict[str, str]:
    """Render a canonical record for a PyPI package.

    Returns a dict mapping filename → content:
      "requirements.txt"
      "pyproject.toml"
    """
    identity = record.get("identity", {})
    descriptive = record.get("descriptive", {})
    dependencies = record.get("dependencies", {})
    sources = record.get("sources", [])
    ext = record.get("extensions", {}).get("pypi", {})

    # Use ecosystem_id (original PyPI name, case-preserved) when available
    pkg_name = identity.get("ecosystem_id") or identity.get("canonical_name", "unknown")
    version = identity.get("version", "")
    summary = descriptive.get("summary", "")
    homepage = descriptive.get("homepage", "")
    licenses = descriptive.get("license", [])
    license_str = licenses[0] if licenses else "UNKNOWN"
    requires_python = ext.get("requires_python", "")

    runtime_deps = dependencies.get("runtime", [])

    # ------------------------------------------------------------------
    # requirements.txt — pin the package and its runtime deps
    # ------------------------------------------------------------------
    req_lines = []
    if version:
        req_lines.append(f"{pkg_name}=={version}")
    else:
        req_lines.append(pkg_name)
    for dep in runtime_deps:
        req_lines.append(dep)
    requirements_txt = "\n".join(req_lines) + "\n"

    # ------------------------------------------------------------------
    # pyproject.toml — minimal [project] table usable with pip/build
    # ------------------------------------------------------------------
    toml_lines = [
        "[build-system]",
        'requires = ["setuptools>=61", "wheel"]',
        'build-backend = "setuptools.backends.legacy:build"',
        "",
        "[project]",
        f'name = "{pkg_name}"',
    ]
    if version:
        toml_lines.append(f'version = "{version}"')
    if summary:
        escaped = summary.replace('"', '\\"')
        toml_lines.append(f'description = "{escaped}"')
    if requires_python:
        toml_lines.append(f'requires-python = "{requires_python}"')
    toml_lines.append(f'license = {{text = "{license_str}"}}')
    if runtime_deps:
        toml_lines.append("dependencies = [")
        for dep in runtime_deps:
            toml_lines.append(f'    "{dep}",')
        toml_lines.append("]")
    if homepage:
        toml_lines.append("")
        toml_lines.append("[project.urls]")
        escaped_hp = homepage.replace('"', '\\"')
        toml_lines.append(f'Homepage = "{escaped_hp}"')

    # Source URL comment
    source_url = ""
    for src in sources:
        if src.get("url"):
            source_url = src["url"]
            break
    if source_url:
        toml_lines.append("")
        toml_lines.append(f"# Source: {source_url}")

    pyproject_toml = "\n".join(toml_lines) + "\n"

    return {
        "requirements.txt": requirements_txt,
        "pyproject.toml": pyproject_toml,
    }
