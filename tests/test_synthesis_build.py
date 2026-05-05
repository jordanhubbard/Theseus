"""
Tests for theseus/synthesis/build.py — SynthesisBuildDriver and backend_lang_for_spec.
"""
import os
import shutil
import subprocess
import sys

import pytest

from theseus.synthesis.build import (
    SynthesisBuildDriver,
    SynthesisBuildResult,
    backend_lang_for_spec,
)


@pytest.fixture
def driver() -> SynthesisBuildDriver:
    return SynthesisBuildDriver()


# ---------------------------------------------------------------------------
# backend_lang_for_spec
# ---------------------------------------------------------------------------

class TestBackendLangForSpec:
    def test_python_module(self) -> None:
        assert backend_lang_for_spec({"backend": "python_module"}) == "python"

    def test_ctypes(self) -> None:
        assert backend_lang_for_spec({"backend": "ctypes"}) == "c"

    def test_cli_node(self) -> None:
        assert backend_lang_for_spec({"backend": "cli", "command": "node"}) == "javascript"

    def test_cli_non_node(self) -> None:
        assert backend_lang_for_spec({"backend": "cli", "command": "curl"}) == "python"

    def test_cli_python(self) -> None:
        assert backend_lang_for_spec({"backend": "cli", "command": "python3"}) == "python"

    def test_node_backend(self) -> None:
        assert backend_lang_for_spec({"backend": "node"}) == "javascript"

    def test_unknown_falls_back_to_python(self) -> None:
        assert backend_lang_for_spec({"backend": "something_else"}) == "python"

    def test_empty_dict(self) -> None:
        # No backend field → defaults to ctypes (matches verify_behavior.py default) → "c"
        assert backend_lang_for_spec({}) == "c"


# ---------------------------------------------------------------------------
# Python build
# ---------------------------------------------------------------------------

class TestBuildPython:
    def test_valid_module_succeeds(
        self, driver: SynthesisBuildDriver, tmp_path: pytest.TempPathFactory
    ) -> None:
        source = {"testmod.py": "def hello():\n    return 'world'\n"}
        result = driver.build(source, "python", "testmod", tmp_path)
        assert result.success is True
        assert result.backend_lang == "python"
        assert result.artifact_path == str(tmp_path)

    def test_syntax_error_fails(
        self, driver: SynthesisBuildDriver, tmp_path: pytest.TempPathFactory
    ) -> None:
        source = {"badmod.py": "def broken(\n"}
        result = driver.build(source, "python", "badmod", tmp_path)
        assert result.success is False
        assert result.build_log != ""

    def test_import_error_fails(
        self, driver: SynthesisBuildDriver, tmp_path: pytest.TempPathFactory
    ) -> None:
        source = {"errmod.py": "import this_does_not_exist_xyz\n"}
        result = driver.build(source, "python", "errmod", tmp_path)
        assert result.success is False

    def test_underscore_module_fallback(
        self, driver: SynthesisBuildDriver, tmp_path: pytest.TempPathFactory
    ) -> None:
        # canonical_name = "_mymod" but file is mymod.py (without underscore)
        source = {"mymod.py": "X = 1\n"}
        result = driver.build(source, "python", "_mymod", tmp_path)
        assert result.success is True

    def test_files_written_to_work_dir(
        self, driver: SynthesisBuildDriver, tmp_path: pytest.TempPathFactory
    ) -> None:
        source = {"mymod.py": "X = 42\n"}
        driver.build(source, "python", "mymod", tmp_path)
        assert (tmp_path / "mymod.py").exists()

    def test_work_dir_in_result(
        self, driver: SynthesisBuildDriver, tmp_path: pytest.TempPathFactory
    ) -> None:
        source = {"mymod.py": "X = 1\n"}
        result = driver.build(source, "python", "mymod", tmp_path)
        assert result.work_dir == str(tmp_path)

    def test_absolute_source_path_rejected(
        self, driver: SynthesisBuildDriver, tmp_path: pytest.TempPathFactory
    ) -> None:
        source = {str(tmp_path.parent / "escape.py"): "X = 1\n"}
        result = driver.build(source, "python", "mymod", tmp_path)
        assert result.success is False
        assert "absolute paths are not allowed" in result.build_log

    def test_parent_traversal_source_path_rejected(
        self, driver: SynthesisBuildDriver, tmp_path: pytest.TempPathFactory
    ) -> None:
        source = {"../escape.py": "X = 1\n"}
        result = driver.build(source, "python", "mymod", tmp_path)
        assert result.success is False
        assert "path escapes work directory" in result.build_log
        assert not (tmp_path.parent / "escape.py").exists()

    @pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlink unavailable")
    def test_symlink_source_path_rejected(
        self, driver: SynthesisBuildDriver, tmp_path: pytest.TempPathFactory
    ) -> None:
        outside = tmp_path.parent / "outside"
        outside.mkdir()
        (tmp_path / "linked").symlink_to(outside, target_is_directory=True)

        result = driver.build({"linked/escape.py": "X = 1\n"}, "python", "mymod", tmp_path)

        assert result.success is False
        assert "path escapes work directory" in result.build_log
        assert not (outside / "escape.py").exists()


# ---------------------------------------------------------------------------
# C build
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    shutil.which("cc") is None and shutil.which("gcc") is None and shutil.which("clang") is None,
    reason="No C compiler available",
)
class TestBuildC:
    def test_valid_c_succeeds(
        self, driver: SynthesisBuildDriver, tmp_path: pytest.TempPathFactory
    ) -> None:
        source = {
            "mylib.h": "int mylib_add(int a, int b);\n",
            "mylib.c": "#include \"mylib.h\"\nint mylib_add(int a, int b) { return a + b; }\n",
        }
        result = driver.build(source, "c", "mylib", tmp_path)
        assert result.success is True
        assert result.backend_lang == "c"
        # artifact_path should point to the compiled shared library
        from pathlib import Path
        assert Path(result.artifact_path).exists()

    def test_compile_error_fails(
        self, driver: SynthesisBuildDriver, tmp_path: pytest.TempPathFactory
    ) -> None:
        source = {"broken.c": "this is not C code\n"}
        result = driver.build(source, "c", "broken", tmp_path)
        assert result.success is False
        assert result.build_log != ""

    def test_no_c_files_fails(
        self, driver: SynthesisBuildDriver, tmp_path: pytest.TempPathFactory
    ) -> None:
        source = {"readme.txt": "no source here\n"}
        result = driver.build(source, "c", "nolib", tmp_path)
        assert result.success is False
        assert "No .c source" in result.build_log

    def test_dylib_on_macos_so_elsewhere(
        self, driver: SynthesisBuildDriver, tmp_path: pytest.TempPathFactory
    ) -> None:
        source = {"trivial.c": "int trivial_one(void) { return 1; }\n"}
        result = driver.build(source, "c", "trivial", tmp_path)
        if result.success:
            if sys.platform == "darwin":
                assert result.artifact_path.endswith(".dylib")
            else:
                assert result.artifact_path.endswith(".so")


# ---------------------------------------------------------------------------
# JavaScript build
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    shutil.which("node") is None and shutil.which("nodejs") is None,
    reason="node not available",
)
class TestBuildJavaScript:
    def test_valid_cjs_module_succeeds(
        self, driver: SynthesisBuildDriver, tmp_path: pytest.TempPathFactory
    ) -> None:
        source = {"index.js": "module.exports = { hello: () => 'world' };\n"}
        result = driver.build(source, "javascript", "testpkg", tmp_path)
        assert result.success is True
        assert result.backend_lang == "javascript"
        assert result.artifact_path == str(tmp_path)

    def test_cjs_module_is_loadable_by_package_name(
        self, driver: SynthesisBuildDriver, tmp_path: pytest.TempPathFactory
    ) -> None:
        source = {"index.js": "module.exports = { hello: () => 'world' };\n"}
        result = driver.build(
            source, "javascript", "testpkg", tmp_path, module_name="lodash.set"
        )
        assert result.success is True

        node = shutil.which("node") or shutil.which("nodejs")
        check = subprocess.run(
            [
                node,
                "-e",
                "const m = require('lodash.set'); if (m.hello() !== 'world') process.exit(2)",
            ],
            cwd=str(tmp_path),
            capture_output=True,
            text=True,
        )
        assert check.returncode == 0, check.stderr

    def test_esm_module_is_loadable_by_package_name(
        self, driver: SynthesisBuildDriver, tmp_path: pytest.TempPathFactory
    ) -> None:
        source = {
            "index.js": (
                "export default function hello() { return 'world'; }\n"
                "export const value = 7;\n"
            )
        }
        result = driver.build(
            source, "javascript", "chalk", tmp_path, module_name="chalk", esm=True
        )
        assert result.success is True

        node = shutil.which("node") or shutil.which("nodejs")
        check = subprocess.run(
            [
                node,
                "--input-type=module",
                "-e",
                "const m = await import('chalk'); if (m.default() !== 'world' || m.value !== 7) process.exit(2)",
            ],
            cwd=str(tmp_path),
            capture_output=True,
            text=True,
        )
        assert check.returncode == 0, check.stderr

    def test_syntax_error_fails(
        self, driver: SynthesisBuildDriver, tmp_path: pytest.TempPathFactory
    ) -> None:
        source = {"index.js": "module.exports = {\n"}
        result = driver.build(source, "javascript", "badpkg", tmp_path)
        assert result.success is False
        assert result.build_log != ""

    def test_no_js_files_fails(
        self, driver: SynthesisBuildDriver, tmp_path: pytest.TempPathFactory
    ) -> None:
        source = {"readme.txt": "no JS here\n"}
        result = driver.build(source, "javascript", "emptypkg", tmp_path)
        assert result.success is False


# ---------------------------------------------------------------------------
# Unknown backend
# ---------------------------------------------------------------------------

class TestBuildUnknownBackend:
    def test_unknown_backend_returns_failure(
        self, driver: SynthesisBuildDriver, tmp_path: pytest.TempPathFactory
    ) -> None:
        result = driver.build({}, "fortran", "prog", tmp_path)
        assert result.success is False
        assert "Unknown backend" in result.build_log
