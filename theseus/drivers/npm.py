"""
theseus/drivers/npm.py

Render a canonical package record as npm installation artifacts:
  package.json  — declares the package as a dependency
  .npmrc        — optional registry config placeholder
"""
from __future__ import annotations

import json


def render(record: dict) -> dict[str, str]:
    """Render a canonical record for an npm package.

    Returns a dict mapping filename → content:
      "package.json"
      ".npmrc"
    """
    identity = record.get("identity", {})
    descriptive = record.get("descriptive", {})
    dependencies = record.get("dependencies", {})
    sources = record.get("sources", [])

    # Use ecosystem_id (original npm name, including @scope/) when available
    pkg_name = identity.get("ecosystem_id") or identity.get("canonical_name", "unknown")
    version = identity.get("version", "")
    summary = descriptive.get("summary", "")
    homepage = descriptive.get("homepage", "")
    licenses = descriptive.get("license", [])
    license_str = licenses[0] if licenses else "UNLICENSED"

    runtime_deps = dependencies.get("runtime", [])
    peer_deps = dependencies.get("host", [])

    # ------------------------------------------------------------------
    # package.json
    # ------------------------------------------------------------------
    # Workspace-style: this package.json installs the target package as a dep.
    safe_name = pkg_name.lstrip("@").replace("/", "-").replace("_", "-")
    pkg_json: dict = {
        "name": f"theseus-install-{safe_name}",
        "version": "1.0.0",
        "description": f"Theseus install manifest for {pkg_name}",
        "private": True,
        "dependencies": {
            pkg_name: version if version else "*",
        },
        "license": license_str,
    }
    if homepage:
        pkg_json["homepage"] = homepage

    # ------------------------------------------------------------------
    # .npmrc — basic config (registry + audit settings)
    # ------------------------------------------------------------------
    npmrc_lines = [
        "registry=https://registry.npmjs.org/",
        "audit=false",
        "fund=false",
    ]
    npmrc = "\n".join(npmrc_lines) + "\n"

    return {
        "package.json": json.dumps(pkg_json, indent=2) + "\n",
        ".npmrc": npmrc,
    }
