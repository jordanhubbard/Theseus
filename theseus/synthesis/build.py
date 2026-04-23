"""
theseus/synthesis/build.py

Per-language build drivers for synthesized source code.

Given source files produced by an LLM, each driver:
  - Writes them to a working directory
  - Compiles them (if needed)
  - Validates the result is loadable
  - Returns a SynthesisBuildResult describing success/failure and artifact location
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SynthesisBuildResult:
    """Outcome of building synthesized source code."""

    success: bool
    # For Python/JS: the staging directory to prepend to PYTHONPATH/NODE_PATH.
    # For C: the full path to the compiled .so / .dylib.
    artifact_path: str
    backend_lang: str
    build_log: str
    returncode: int
    work_dir: str


class SynthesisBuildDriver:
    """Compile/stage synthesized source files for a given backend language."""

    def build(
        self,
        source_files: dict[str, str],
        backend_lang: str,
        canonical_name: str,
        work_dir: Path,
    ) -> SynthesisBuildResult:
        """
        Write *source_files* into *work_dir* and compile/validate them.

        Args:
            source_files: mapping of filename → file content from the LLM.
            backend_lang: one of "python", "c", "javascript".
            canonical_name: used to derive the expected module/library name.
            work_dir: directory to write files into (caller creates it).

        Returns:
            SynthesisBuildResult with success status and artifact path.
        """
        if backend_lang == "python":
            return self._build_python(source_files, canonical_name, work_dir)
        if backend_lang == "c":
            return self._build_c(source_files, canonical_name, work_dir)
        if backend_lang == "javascript":
            return self._build_javascript(source_files, canonical_name, work_dir)
        if backend_lang == "rust":
            return self._build_rust(source_files, canonical_name, work_dir)
        return SynthesisBuildResult(
            success=False,
            artifact_path="",
            backend_lang=backend_lang,
            build_log=f"Unknown backend_lang: {backend_lang!r}",
            returncode=1,
            work_dir=str(work_dir),
        )

    # ------------------------------------------------------------------
    # Python
    # ------------------------------------------------------------------

    def _build_python(
        self,
        source_files: dict[str, str],
        canonical_name: str,
        work_dir: Path,
    ) -> SynthesisBuildResult:
        _write_files(source_files, work_dir)

        env = dict(os.environ)
        env["PYTHONPATH"] = str(work_dir) + os.pathsep + env.get("PYTHONPATH", "")

        # Validate the module can be imported without errors.
        # Use the canonical name as module name; strip leading underscores for the
        # import probe (e.g. "_bisect" → try "_bisect" first, then "bisect").
        module_name = canonical_name
        result = subprocess.run(
            [sys.executable, "-c", f"import {module_name}"],
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )
        log = (result.stdout + result.stderr).strip()

        if result.returncode == 0:
            return SynthesisBuildResult(
                success=True,
                artifact_path=str(work_dir),
                backend_lang="python",
                build_log=log,
                returncode=0,
                work_dir=str(work_dir),
            )

        # If the canonical name fails, try without a leading underscore.
        if canonical_name.startswith("_"):
            alt = canonical_name.lstrip("_")
            r2 = subprocess.run(
                [sys.executable, "-c", f"import {alt}"],
                capture_output=True,
                text=True,
                env=env,
                timeout=30,
            )
            if r2.returncode == 0:
                return SynthesisBuildResult(
                    success=True,
                    artifact_path=str(work_dir),
                    backend_lang="python",
                    build_log=(r2.stdout + r2.stderr).strip(),
                    returncode=0,
                    work_dir=str(work_dir),
                )
            log = (log + "\n" + (r2.stdout + r2.stderr)).strip()

        return SynthesisBuildResult(
            success=False,
            artifact_path=str(work_dir),
            backend_lang="python",
            build_log=log,
            returncode=result.returncode,
            work_dir=str(work_dir),
        )

    # ------------------------------------------------------------------
    # C shared library
    # ------------------------------------------------------------------

    def _build_c(
        self,
        source_files: dict[str, str],
        canonical_name: str,
        work_dir: Path,
    ) -> SynthesisBuildResult:
        _write_files(source_files, work_dir)

        # Determine output filename and compiler flags per platform.
        if sys.platform == "darwin":
            lib_filename = f"lib{canonical_name}.dylib"
            shared_flag = "-dynamiclib"
        else:
            lib_filename = f"lib{canonical_name}.so"
            shared_flag = "-shared"

        lib_path = work_dir / lib_filename

        # Collect all .c source files.
        c_sources = sorted(str(p) for p in work_dir.glob("*.c"))
        if not c_sources:
            return SynthesisBuildResult(
                success=False,
                artifact_path="",
                backend_lang="c",
                build_log="No .c source files found in work directory.",
                returncode=1,
                work_dir=str(work_dir),
            )

        cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
        if cc is None:
            return SynthesisBuildResult(
                success=False,
                artifact_path="",
                backend_lang="c",
                build_log="No C compiler (cc/gcc/clang) found in PATH.",
                returncode=1,
                work_dir=str(work_dir),
            )

        cmd = [cc, shared_flag, "-fPIC", "-O2", "-o", str(lib_path)] + c_sources
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(work_dir),
            timeout=120,
        )
        log = (result.stdout + result.stderr).strip()

        if result.returncode != 0 or not lib_path.exists():
            return SynthesisBuildResult(
                success=False,
                artifact_path="",
                backend_lang="c",
                build_log=log,
                returncode=result.returncode,
                work_dir=str(work_dir),
            )

        return SynthesisBuildResult(
            success=True,
            artifact_path=str(lib_path),
            backend_lang="c",
            build_log=log,
            returncode=0,
            work_dir=str(work_dir),
        )

    # ------------------------------------------------------------------
    # JavaScript (Node.js)
    # ------------------------------------------------------------------

    def _build_javascript(
        self,
        source_files: dict[str, str],
        canonical_name: str,
        work_dir: Path,
    ) -> SynthesisBuildResult:
        _write_files(source_files, work_dir)

        node = shutil.which("node") or shutil.which("nodejs")
        if node is None:
            return SynthesisBuildResult(
                success=False,
                artifact_path="",
                backend_lang="javascript",
                build_log="node not found in PATH.",
                returncode=1,
                work_dir=str(work_dir),
            )

        # Prefer index.js; fall back to any .js file.
        entry = work_dir / "index.js"
        if not entry.exists():
            js_files = list(work_dir.glob("*.js"))
            if js_files:
                entry = js_files[0]
            else:
                return SynthesisBuildResult(
                    success=False,
                    artifact_path="",
                    backend_lang="javascript",
                    build_log="No .js files found in work directory.",
                    returncode=1,
                    work_dir=str(work_dir),
                )

        # For ESM, use dynamic import; for CJS use require.
        # We probe with require() — if it fails with ERR_REQUIRE_ESM we note it
        # but still succeed (the verify harness uses import() for ESM specs).
        script = f"require({str(entry)!r})"
        result = subprocess.run(
            [node, "-e", script],
            capture_output=True,
            text=True,
            cwd=str(work_dir),
            timeout=30,
        )
        log = (result.stdout + result.stderr).strip()

        # ERR_REQUIRE_ESM means the module is ESM-only — that's fine, treat as success.
        if result.returncode != 0 and "ERR_REQUIRE_ESM" not in log:
            return SynthesisBuildResult(
                success=False,
                artifact_path="",
                backend_lang="javascript",
                build_log=log,
                returncode=result.returncode,
                work_dir=str(work_dir),
            )

        return SynthesisBuildResult(
            success=True,
            artifact_path=str(work_dir),
            backend_lang="javascript",
            build_log=log,
            returncode=0,
            work_dir=str(work_dir),
        )


    # ------------------------------------------------------------------
    # Rust (PyO3 extension module)
    # ------------------------------------------------------------------

    def _build_rust(
        self,
        source_files: dict[str, str],
        canonical_name: str,
        work_dir: Path,
    ) -> SynthesisBuildResult:
        _write_files(source_files, work_dir)

        maturin = shutil.which("maturin")
        if maturin is None:
            return SynthesisBuildResult(
                success=False,
                artifact_path="",
                backend_lang="rust",
                build_log="maturin not found in PATH — install with: pip install maturin",
                returncode=1,
                work_dir=str(work_dir),
            )

        # Generate Cargo.toml if LLM did not produce one.
        # Use pyo3 0.22 with abi3-py39 so the wheel works on Python 3.9+ including
        # 3.14+. PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1 is set at build time to allow
        # building against Python versions newer than pyo3's declared maximum.
        cargo_toml = work_dir / "Cargo.toml"
        if not cargo_toml.exists():
            cargo_toml.write_text(
                f'[package]\nname = "{canonical_name}"\nversion = "0.1.0"\nedition = "2021"\n\n'
                f'[lib]\nname = "{canonical_name}"\ncrate-type = ["cdylib"]\n\n'
                f'[dependencies]\npyo3 = {{ version = "0.22", features = ["extension-module", "abi3-py39"] }}\n',
                encoding="utf-8",
            )

        # Generate pyproject.toml required by maturin 1.x.
        pyproject = work_dir / "pyproject.toml"
        if not pyproject.exists():
            pyproject.write_text(
                '[build-system]\nrequires = ["maturin>=1.0,<2.0"]\nbuild-backend = "maturin"\n\n'
                f'[project]\nname = "{canonical_name}"\nversion = "0.1.0"\n\n'
                '[tool.maturin]\nfeatures = ["pyo3/extension-module"]\n',
                encoding="utf-8",
            )

        # Build a wheel then extract the .so into work_dir/lib so it can be
        # prepended to PYTHONPATH for harness invocation.
        dist_dir = work_dir / "dist"
        dist_dir.mkdir(exist_ok=True)
        lib_dir = work_dir / "lib"
        lib_dir.mkdir(exist_ok=True)

        build_env = dict(os.environ)
        # Allow building against Python versions newer than pyo3's declared maximum.
        build_env["PYO3_USE_ABI3_FORWARD_COMPATIBILITY"] = "1"

        result = subprocess.run(
            [
                maturin, "build", "--release",
                "--out", str(dist_dir),
                "--manifest-path", str(cargo_toml),
                "--interpreter", sys.executable,
            ],
            capture_output=True,
            text=True,
            cwd=str(work_dir),
            env=build_env,
            timeout=300,
        )
        log = (result.stdout + result.stderr).strip()

        if result.returncode != 0:
            return SynthesisBuildResult(
                success=False,
                artifact_path="",
                backend_lang="rust",
                build_log=log,
                returncode=result.returncode,
                work_dir=str(work_dir),
            )

        # Find the wheel and extract the compiled extension module.
        wheels = sorted(dist_dir.glob("*.whl"))
        if not wheels:
            return SynthesisBuildResult(
                success=False,
                artifact_path="",
                backend_lang="rust",
                build_log=log + "\nNo .whl file produced.",
                returncode=1,
                work_dir=str(work_dir),
            )

        import zipfile
        wheel = wheels[0]
        with zipfile.ZipFile(wheel) as zf:
            so_names = [
                n for n in zf.namelist()
                if n.endswith(".so") or n.endswith(".abi3.so") or n.endswith(".pyd")
            ]
            for so_name in so_names:
                # Flatten into lib_dir (strip any package sub-path).
                target = lib_dir / os.path.basename(so_name)
                target.write_bytes(zf.read(so_name))

        if not any(lib_dir.iterdir()):
            return SynthesisBuildResult(
                success=False,
                artifact_path="",
                backend_lang="rust",
                build_log=log + "\nWheel contained no .so/.pyd files.",
                returncode=1,
                work_dir=str(work_dir),
            )

        return SynthesisBuildResult(
            success=True,
            artifact_path=str(lib_dir),
            backend_lang="rust",
            build_log=log,
            returncode=0,
            work_dir=str(work_dir),
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_files(source_files: dict[str, str], work_dir: Path) -> None:
    """Write all source files to work_dir, creating subdirectories as needed."""
    for filename, content in source_files.items():
        dest = work_dir / filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")


def backend_lang_for_spec(lib_spec: dict) -> str:
    """
    Map a compiled spec's ``library`` dict to a synthesis target language.

    Follows the same defaulting logic as verify_behavior.py's LibraryLoader:
    when the ``backend`` key is absent, ctypes is assumed (specs like zlib, lz4,
    zstd only have ``soname_patterns`` and no explicit ``backend`` field).

    Mapping:
      python_module  → "python"
      ctypes (or absent with soname_patterns) → "c"
      cli + node cmd → "javascript"
      cli (other)    → "python"  (synthesise as a Python CLI script)
    """
    backend = lib_spec.get("backend", "ctypes")   # match verify_behavior.py default
    if backend == "python_module":
        return "python"
    if backend == "rust_module":
        return "rust"
    if backend == "python_cleanroom":
        return "python_cleanroom"
    if backend == "node_cleanroom":
        return "node_cleanroom"
    if backend == "ctypes":
        return "c"
    if backend == "cli":
        command = lib_spec.get("command", "")
        if command == "node":
            return "javascript"
        return "python"
    # node() backend (future)
    if backend == "node":
        return "javascript"
    # Unknown — fall back to python
    return "python"
