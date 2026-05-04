"""Tests for the clean-room package registry gate."""
import json

import pytest

import registry
import tools.cleanroom_verify as cleanroom_verify


def _write_registry(tmp_path, status="pending"):
    spec = tmp_path / "pkg.zspec.json"
    spec.write_text("{}", encoding="utf-8")
    impl = tmp_path / "cleanroom" / "pkg"
    impl.mkdir(parents=True)
    path = tmp_path / "registry.json"
    path.write_text(
        json.dumps({
            "version": 1,
            "packages": {
                "theseus_pkg": {
                    "cleanroom_path": str(impl),
                    "spec": str(spec),
                    "status": status,
                }
            },
        }),
        encoding="utf-8",
    )
    return path


def test_register_rejects_verified_status(tmp_path, monkeypatch):
    reg_path = tmp_path / "registry.json"
    reg_path.write_text(json.dumps({"packages": {}}), encoding="utf-8")
    monkeypatch.setattr(registry, "REGISTRY_PATH", reg_path)

    with pytest.raises(ValueError):
        registry.register("theseus_pkg", "cleanroom/python/theseus_pkg", "spec.json", "verified")


def test_verify_promotes_only_after_cleanroom_verify_passes(tmp_path, monkeypatch):
    reg_path = _write_registry(tmp_path)
    monkeypatch.setattr(registry, "REGISTRY_PATH", reg_path)
    monkeypatch.setattr(
        cleanroom_verify,
        "verify",
        lambda spec, verbose=False: {"pass": 1, "fail": 0, "errors": []},
    )

    registry.mark_verified("theseus_pkg")

    info = json.loads(reg_path.read_text(encoding="utf-8"))["packages"]["theseus_pkg"]
    assert info["status"] == "verified"
    assert info["verified_pass_count"] == 1
    assert info["verified_total"] == 1


def test_verify_does_not_promote_on_cleanroom_failure(tmp_path, monkeypatch):
    reg_path = _write_registry(tmp_path)
    monkeypatch.setattr(registry, "REGISTRY_PATH", reg_path)
    monkeypatch.setattr(
        cleanroom_verify,
        "verify",
        lambda spec, verbose=False: {
            "pass": 0,
            "fail": 1,
            "errors": [{"invariant": "x", "error": "broken"}],
        },
    )

    with pytest.raises(RuntimeError):
        registry.mark_verified("theseus_pkg")

    info = json.loads(reg_path.read_text(encoding="utf-8"))["packages"]["theseus_pkg"]
    assert info["status"] == "pending"
