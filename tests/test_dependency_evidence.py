"""
Tests for dependency evidence that feeds external OSS dependency scanners.
"""
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def test_dockerfile_apt_install_block_has_no_comment_lines():
    dockerfile = REPO_ROOT / "docker" / "Dockerfile.verify"
    lines = dockerfile.read_text(encoding="utf-8").splitlines()

    in_install = False
    install_lines = []
    for line in lines:
        if "apt-get install" in line:
            in_install = True
        if in_install:
            install_lines.append(line)
            if line.strip() and not line.rstrip().endswith("\\"):
                break

    assert install_lines, "expected an apt-get install block"
    comments = [line for line in install_lines if line.lstrip().startswith("#")]
    assert comments == []


def test_package_lock_has_direct_dependency_license_metadata():
    lockfile = REPO_ROOT / "package-lock.json"
    lock = json.loads(lockfile.read_text(encoding="utf-8"))
    direct_deps = lock["packages"][""]["dependencies"]

    missing = []
    for name in sorted(direct_deps):
        package = lock["packages"].get("node_modules/" + name, {})
        if "license" not in package:
            missing.append(name)

    assert missing == ["email-validator", "svg-tags", "unidecode"]


def test_dependency_evidence_documents_scanner_exceptions():
    doc = (REPO_ROOT / "docs" / "dependency-evidence.md").read_text(encoding="utf-8")

    for expected in (
        "svg-tags@1.0.0",
        "email-validator",
        "unidecode",
        "node-forge@1.4.0",
        "npm audit --omit=dev",
        "bounded ranges",
        "transitive lock",
        "Cargo.lock",
        "apt-get install",
        "Refresh the base-image pin",
    ):
        assert expected in doc
