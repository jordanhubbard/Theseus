#!/usr/bin/env python3
"""
verify_behavior.py — Z-layer behavioral specification verification harness.

Loads a .zspec.json file and verifies every invariant against the real installed
library via ctypes. No compilation required.

Usage:
    python3 tools/verify_behavior.py zspecs/zlib.zspec.json
    python3 tools/verify_behavior.py zspecs/zlib.zspec.json --filter checksum
    python3 tools/verify_behavior.py zspecs/zlib.zspec.json --verbose
    python3 tools/verify_behavior.py zspecs/zlib.zspec.json --list

Exit codes:
    0  All invariants passed
    1  One or more invariants failed
    2  Harness error (spec unreadable, library not found, etc.)
"""
import argparse
import base64
import ctypes
import ctypes.util
import importlib
import importlib.metadata
import json
import re as _re
import shutil
import struct as _struct
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class SpecError(Exception):
    pass


class LibraryNotFoundError(Exception):
    pass


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

@dataclass
class Result:
    inv_id: str
    passed: bool
    message: str
    skip_reason: str | None = None


@dataclass
class CLIBackend:
    """Represents a CLI tool loaded as a 'library' for the cli backend.

    module_name is set when the CLI tool is a Node.js runtime and the spec
    targets a specific npm module (e.g. command='node', module_name='semver').

    esm=True means the module is ESM-only (no require()). Node handler methods
    will use dynamic import() wrapped in an async IIFE instead of require().
    """
    command: str
    module_name: str | None = None
    esm: bool = False


# ---------------------------------------------------------------------------
# Argument resolver
# ---------------------------------------------------------------------------

def _resolve_arg(val, atype: str):
    """
    Convert a JSON spec arg value to the appropriate Python type for ctypes.

    Supported arg_type tokens:
      "int"       — pass as Python int; ctypes converts via argtypes
      "bytes_b64" — base64-decode to bytes
      "null"      — pass None (NULL pointer for c_char_p)
    """
    if atype == "int":
        return int(val)
    if atype == "bytes_b64":
        return base64.b64decode(val) if val else b""
    if atype == "null":
        return None
    return val


# ---------------------------------------------------------------------------
# Library loader
# ---------------------------------------------------------------------------

class LibraryLoader:
    """Loads the target library — either a shared library via ctypes or a Python module."""

    def load(self, lib_spec: dict):
        backend = lib_spec.get("backend", "ctypes")
        if backend == "python_module":
            module_name = lib_spec["module_name"]
            try:
                mod = importlib.import_module(module_name)
            except ImportError as exc:
                raise LibraryNotFoundError(
                    f"Cannot import Python module {module_name!r}: {exc}"
                ) from exc
            # Pre-import well-known submodules so they are accessible as attributes
            # of the top-level module via getattr (side-effect of import).
            _SUBMODULE_PRELOADS: dict[str, list[str]] = {
                "pygments": [
                    "pygments.lexers",
                    "pygments.formatters",
                    "pygments.token",
                    "pygments.styles",
                ],
                "packaging": [
                    "packaging.version",
                    "packaging.specifiers",
                    "packaging.utils",
                    "packaging.requirements",
                ],
                "setuptools": [
                    "setuptools._vendor",
                    "setuptools._vendor.packaging",
                    "setuptools._vendor.packaging.version",
                    "setuptools._vendor.packaging.specifiers",
                    "setuptools._vendor.packaging.requirements",
                ],
                "defusedxml": [
                    "defusedxml.ElementTree",
                ],
                "docutils": [
                    "docutils.core",
                    "docutils.nodes",
                ],
            }
            for sub in _SUBMODULE_PRELOADS.get(module_name, []):
                try:
                    importlib.import_module(sub)
                except ImportError:
                    pass
            return mod
        if backend == "cli":
            cmd = lib_spec["command"]
            found = shutil.which(cmd)
            if not found:
                raise LibraryNotFoundError(
                    f"CLI command {cmd!r} not found in PATH"
                )
            module_name = lib_spec.get("module_name")
            esm = bool(lib_spec.get("esm", False))
            if module_name:
                # Verify the module is loadable before running any invariants.
                # ESM-only modules must use dynamic import(); CJS uses require().
                if esm:
                    check_script = (
                        f"(async()=>{{await import({json.dumps(module_name)});"
                        f"process.exit(0)}})().catch(()=>process.exit(1))"
                    )
                else:
                    check_script = f"require({json.dumps(module_name)})"
                check = subprocess.run(
                    [found, "-e", check_script],
                    capture_output=True,
                )
                if check.returncode != 0:
                    err = check.stderr.decode("utf-8", errors="replace").strip()
                    raise LibraryNotFoundError(
                        f"Node module {module_name!r} not found "
                        f"(is it installed?): {err}"
                    )
            return CLIBackend(command=found, module_name=module_name, esm=esm)
        return self._load_ctypes(lib_spec)

    def _load_ctypes(self, lib_spec: dict) -> ctypes.CDLL:
        patterns = lib_spec.get("soname_patterns", [])
        for name in patterns:
            found = ctypes.util.find_library(name)
            if found:
                try:
                    lib = ctypes.CDLL(found)
                    self._setup(lib)
                    return lib
                except OSError:
                    pass
        # Fallback: try direct platform-conventional names
        for name in patterns:
            for attempt in (
                f"lib{name}.dylib",
                f"lib{name}.so",
                f"lib{name}.so.1",
                f"lib{name}.so.7",
            ):
                try:
                    lib = ctypes.CDLL(attempt)
                    self._setup(lib)
                    return lib
                except OSError:
                    pass
        raise LibraryNotFoundError(
            f"Could not find library with soname patterns: {patterns}"
        )

    def _setup(self, lib: ctypes.CDLL) -> None:
        """Bind argtypes and restypes for well-known C API functions used by invariants.

        Each block is guarded so that loading a library that does not export a given
        function (e.g. zstd instead of zlib) does not raise AttributeError.
        """
        # zlib API — only bound when the library exports these symbols
        if hasattr(lib, "compress"):
            lib.compress.argtypes = [
                ctypes.c_char_p,
                ctypes.POINTER(ctypes.c_ulong),
                ctypes.c_char_p,
                ctypes.c_ulong,
            ]
            lib.compress.restype = ctypes.c_int

        if hasattr(lib, "compress2"):
            lib.compress2.argtypes = [
                ctypes.c_char_p,
                ctypes.POINTER(ctypes.c_ulong),
                ctypes.c_char_p,
                ctypes.c_ulong,
                ctypes.c_int,
            ]
            lib.compress2.restype = ctypes.c_int

        if hasattr(lib, "uncompress"):
            lib.uncompress.argtypes = [
                ctypes.c_char_p,
                ctypes.POINTER(ctypes.c_ulong),
                ctypes.c_char_p,
                ctypes.c_ulong,
            ]
            lib.uncompress.restype = ctypes.c_int

        if hasattr(lib, "compressBound"):
            lib.compressBound.argtypes = [ctypes.c_ulong]
            lib.compressBound.restype = ctypes.c_ulong

        if hasattr(lib, "crc32"):
            lib.crc32.argtypes = [ctypes.c_ulong, ctypes.c_char_p, ctypes.c_uint]
            lib.crc32.restype = ctypes.c_ulong

        if hasattr(lib, "adler32"):
            lib.adler32.argtypes = [ctypes.c_ulong, ctypes.c_char_p, ctypes.c_uint]
            lib.adler32.restype = ctypes.c_ulong

        if hasattr(lib, "zlibVersion"):
            lib.zlibVersion.argtypes = []
            lib.zlibVersion.restype = ctypes.c_char_p

        if hasattr(lib, "zError"):
            lib.zError.argtypes = [ctypes.c_int]
            lib.zError.restype = ctypes.c_char_p


# ---------------------------------------------------------------------------
# Spec loader
# ---------------------------------------------------------------------------

REQUIRED_SECTIONS = [
    "schema_version", "identity", "provenance", "library",
    "constants", "types", "functions", "invariants",
    "wire_formats", "error_model",
]

KNOWN_KINDS = {
    # ctypes / C-library kinds
    "constant_eq",
    "call_eq",
    "call_returns",
    "version_prefix",
    "roundtrip",
    "wire_bytes",
    "error_on_bad_input",
    "incremental_eq_oneshot",
    "call_ge",
    # Python-module kinds (hashlib)
    "hash_known_vector",
    "hash_incremental",
    "hash_object_attr",
    "python_set_contains",
    "hash_digest_consistency",
    "hash_copy_independence",
    "hash_api_equivalence",
    # General Python-module kinds (base64, json, struct, sqlite3, …)
    "python_call_eq",
    "python_call_raises",
    "python_encode_decode_roundtrip",
    "python_struct_roundtrip",
    "python_sqlite_roundtrip",
    # CLI / subprocess kinds
    "cli_exits_with",
    "cli_stdout_eq",
    "cli_stdout_contains",
    "cli_stdout_matches",
    "cli_stderr_contains",
    # Node.js module kinds
    "node_module_call_eq",
    "node_constructor_call_eq",
    "node_factory_call_eq",
    # lz4-specific ctypes roundtrip
    "lz4_roundtrip",
    # pcre2-specific ctypes compile+match
    "pcre2_match",
}


class SpecLoader:
    def load(self, path: Path) -> dict:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as e:
            raise SpecError(f"Cannot read spec file: {e}") from e
        try:
            spec = json.loads(text)
        except json.JSONDecodeError as e:
            raise SpecError(f"Invalid JSON in spec file: {e}") from e
        if not isinstance(spec, dict):
            raise SpecError("Spec must be a JSON object at the top level")
        missing = [k for k in REQUIRED_SECTIONS if k not in spec]
        if missing:
            raise SpecError(f"Missing required sections: {', '.join(missing)}")
        if not isinstance(spec.get("invariants"), list):
            raise SpecError("'invariants' must be a JSON array")
        return spec


# ---------------------------------------------------------------------------
# Pattern registry — one handler per invariant kind
# ---------------------------------------------------------------------------

class PatternRegistry:
    def __init__(self, lib, constants_map: dict):
        self._lib = lib
        self._c = constants_map
        self._handlers = {
            # ctypes kinds
            "constant_eq":            self._constant_eq,
            "call_eq":                self._call_eq,
            "call_returns":           self._call_returns,
            "version_prefix":         self._version_prefix,
            "roundtrip":              self._roundtrip,
            "wire_bytes":             self._wire_bytes,
            "error_on_bad_input":     self._error_on_bad_input,
            "incremental_eq_oneshot": self._incremental_eq_oneshot,
            "call_ge":                self._call_ge,
            # Python-module kinds (hashlib)
            "hash_known_vector":              self._hash_known_vector,
            "hash_incremental":               self._hash_incremental,
            "hash_object_attr":               self._hash_object_attr,
            "python_set_contains":            self._python_set_contains,
            "hash_digest_consistency":        self._hash_digest_consistency,
            "hash_copy_independence":         self._hash_copy_independence,
            "hash_api_equivalence":           self._hash_api_equivalence,
            # General Python-module kinds
            "python_call_eq":                 self._python_call_eq,
            "python_call_raises":             self._python_call_raises,
            "python_encode_decode_roundtrip": self._python_encode_decode_roundtrip,
            "python_struct_roundtrip":        self._python_struct_roundtrip,
            "python_sqlite_roundtrip":        self._python_sqlite_roundtrip,
            # CLI / subprocess kinds
            "cli_exits_with":                 self._cli_exits_with,
            "cli_stdout_eq":                  self._cli_stdout_eq,
            "cli_stdout_contains":            self._cli_stdout_contains,
            "cli_stdout_matches":             self._cli_stdout_matches,
            "cli_stderr_contains":            self._cli_stderr_contains,
            # Node.js module kinds
            "node_module_call_eq":            self._node_module_call_eq,
            "node_constructor_call_eq":       self._node_constructor_call_eq,
            "node_factory_call_eq":           self._node_factory_call_eq,
            # lz4-specific ctypes roundtrip
            "lz4_roundtrip":                  self._lz4_roundtrip,
            # pcre2-specific ctypes compile+match
            "pcre2_match":                    self._pcre2_match,
        }

    def run(self, inv: dict) -> tuple[bool, str]:
        kind = inv.get("kind", "")
        handler = self._handlers.get(kind)
        if handler is None:
            return False, f"Unknown invariant kind: {kind!r}"
        return handler(inv["spec"])

    # --- constant_eq ---
    # Verifies that a named constant in the spec has the expected integer value.
    # Constants are compile-time #defines; they are not exported as symbols.
    # This catches spec drift: if someone edits the spec incorrectly, this fails.
    def _constant_eq(self, spec: dict) -> tuple[bool, str]:
        name = spec["name"]
        expected = spec["expected_value"]
        actual = self._c.get(name)
        if actual is None:
            return False, f"Constant {name!r} not in spec constants map"
        if actual != expected:
            return False, f"{name}: spec has {actual}, but invariant expects {expected}"
        return True, f"{name} == {expected}"

    # --- call_eq ---
    # Calls a function with spec-defined args and checks the return value equals expected.
    # Used for checksum functions (crc32, adler32) with known test vectors.
    def _call_eq(self, spec: dict) -> tuple[bool, str]:
        fn_name = spec["function"]
        raw_args = spec["args"]
        atypes = spec.get("arg_types", ["int"] * len(raw_args))
        args = [_resolve_arg(v, t) for v, t in zip(raw_args, atypes)]
        expected = spec["expected"]
        try:
            result = int(getattr(self._lib, fn_name)(*args))
        except Exception as exc:
            return False, f"Call to {fn_name}() raised: {exc}"
        if result != expected:
            return False, f"{fn_name}() returned {result} (0x{result & 0xFFFFFFFF:08x}), expected {expected} (0x{expected & 0xFFFFFFFF:08x})"
        return True, f"{fn_name}() == {expected}"

    # --- call_returns ---
    # Calls a function and checks the return code name matches the spec.
    # Used for compress2() success and error cases.
    def _call_returns(self, spec: dict) -> tuple[bool, str]:
        fn_name = spec["function"]
        expected_name = spec["expected_return"]
        expected = self._c.get(expected_name)
        if expected is None:
            return False, f"Unknown expected return code: {expected_name!r}"

        if fn_name == "compress2":
            src = base64.b64decode(spec["src_b64"]) if spec.get("src_b64") else b""
            level = spec.get("level", -1)
            cap = spec.get("dst_capacity", max(len(src) + 100, 64))
            dst = ctypes.create_string_buffer(cap)
            dst_len = ctypes.c_ulong(cap)
            ret = int(self._lib.compress2(dst, ctypes.byref(dst_len), src, len(src), level))
        else:
            return False, f"call_returns: unsupported function {fn_name!r}"

        if ret != expected:
            return False, f"{fn_name}() returned {ret}, expected {expected_name}({expected})"
        return True, f"{fn_name}() returned {expected_name} as expected"

    # --- version_prefix ---
    # Calls the library's version function and checks the returned string starts
    # with the expected prefix (base64-encoded in the spec).
    def _version_prefix(self, spec: dict) -> tuple[bool, str]:
        fn_name = spec["function"]
        prefix = base64.b64decode(spec["expected_prefix_b64"])
        fn = getattr(self._lib, fn_name)
        # For ctypes libraries the default restype is c_int; version functions
        # return a C string, so we set c_char_p here if not already set.
        if hasattr(fn, "restype") and fn.restype is not ctypes.c_char_p:
            fn.restype = ctypes.c_char_p
        result = fn()
        if result is None:
            return False, f"{fn_name}() returned NULL"
        if not result.startswith(prefix):
            return False, f"{fn_name}() = {result!r}, expected prefix {prefix!r}"
        return True, f"{fn_name}() = {result!r}"

    # --- roundtrip ---
    # compress() then uncompress() each input; verifies byte-perfect recovery.
    def _roundtrip(self, spec: dict) -> tuple[bool, str]:
        Z_OK = self._c.get("Z_OK", 0)
        inputs = spec["inputs"]
        for test in inputs:
            label = test.get("label", "?")
            raw = base64.b64decode(test["data_b64"]) if test.get("data_b64") else b""
            original = raw * test.get("repeat", 1)

            # Compress
            cap = max(len(original) + len(original) // 10 + 32 + 64, 64)
            dst = ctypes.create_string_buffer(cap)
            dst_len = ctypes.c_ulong(cap)
            ret = int(self._lib.compress(dst, ctypes.byref(dst_len), original, len(original)))
            if ret != Z_OK:
                return False, f"[{label}] compress() returned {ret}, expected Z_OK({Z_OK})"
            compressed = dst.raw[: dst_len.value]

            # Decompress
            rec_cap = max(len(original) * 2 + 64, 64)
            rec = ctypes.create_string_buffer(rec_cap)
            rec_len = ctypes.c_ulong(rec_cap)
            ret2 = int(self._lib.uncompress(rec, ctypes.byref(rec_len), compressed, len(compressed)))
            if ret2 != Z_OK:
                return False, f"[{label}] uncompress() returned {ret2}, expected Z_OK({Z_OK})"
            recovered = rec.raw[: rec_len.value]
            if recovered != original:
                return False, (
                    f"[{label}] round-trip mismatch: recovered {len(recovered)} bytes, "
                    f"expected {len(original)}"
                )
        return True, f"all {len(inputs)} inputs round-tripped correctly"

    # --- wire_bytes ---
    # Produces compressed output and checks byte-level assertions against it.
    # python_check expressions run in a restricted namespace containing:
    #   data             — the byte slice (bytes object)
    #   struct           — Python's struct module
    #   adler32_of_input — integer Adler-32 of the original uncompressed input
    def _wire_bytes(self, spec: dict) -> tuple[bool, str]:
        Z_OK = self._c.get("Z_OK", 0)
        produce_fn = spec["produce_via"]
        pa = spec.get("produce_args", {})
        src_raw = base64.b64decode(pa.get("data_b64", "")) if pa.get("data_b64") else b""
        src = src_raw * pa.get("repeat", 1)
        level = pa.get("level", -1)

        cap = max(len(src) + len(src) // 10 + 32 + 64, 64)
        dst = ctypes.create_string_buffer(cap)
        dst_len = ctypes.c_ulong(cap)

        if produce_fn == "compress2":
            ret = int(self._lib.compress2(dst, ctypes.byref(dst_len), src, len(src), level))
        elif produce_fn == "compress":
            ret = int(self._lib.compress(dst, ctypes.byref(dst_len), src, len(src)))
        else:
            return False, f"Unsupported produce_via: {produce_fn!r}"

        if ret != Z_OK:
            return False, f"{produce_fn}() returned {ret}, expected Z_OK"

        compressed = dst.raw[: dst_len.value]
        adler32_of_input = int(self._lib.adler32(1, src, len(src)))

        for assertion in spec["assertions"]:
            desc = assertion["description"]
            offset = assertion["offset"]
            length = assertion["length"]

            if isinstance(offset, int) and offset < 0:
                end = offset + length
                data_slice = compressed[offset:] if end == 0 else compressed[offset:end]
            else:
                data_slice = compressed[offset: offset + length]

            check = assertion["python_check"]
            ns = {
                "data": data_slice,
                "struct": _struct,
                "adler32_of_input": adler32_of_input,
            }
            try:
                ok = eval(check, {"__builtins__": {}}, ns)  # noqa: S307
            except Exception as exc:
                return False, f"[{desc}] check expression failed to evaluate: {exc}"
            if not ok:
                return False, f"[{desc}] FAILED: {check!r}  data={data_slice.hex()}"

        return True, f"all {len(spec['assertions'])} wire assertions passed"

    # --- error_on_bad_input ---
    # Passes deliberately invalid data to a function and checks it returns the expected error code.
    def _error_on_bad_input(self, spec: dict) -> tuple[bool, str]:
        fn_name = spec["function"]
        bad = base64.b64decode(spec["bad_input_b64"])
        expected_name = spec["expected_return"]
        expected = self._c.get(expected_name)
        if expected is None:
            return False, f"Unknown expected return code: {expected_name!r}"

        if fn_name == "uncompress":
            dst = ctypes.create_string_buffer(1024)
            dst_len = ctypes.c_ulong(1024)
            ret = int(self._lib.uncompress(dst, ctypes.byref(dst_len), bad, len(bad)))
        else:
            return False, f"error_on_bad_input: unsupported function {fn_name!r}"

        if ret != expected:
            return False, f"{fn_name}() returned {ret}, expected {expected_name}({expected})"
        return True, f"{fn_name}() correctly returns {expected_name} on invalid input"

    # --- incremental_eq_oneshot ---
    # Verifies that feeding data in chunks produces the same result as a single call.
    # Used to verify the incremental composition property of crc32 and adler32.
    def _incremental_eq_oneshot(self, spec: dict) -> tuple[bool, str]:
        fn_name = spec["function"]
        init = spec["init_value"]
        chunks = [base64.b64decode(c) for c in spec["chunks"]]
        full = base64.b64decode(spec["full_data_b64"])
        fn = getattr(self._lib, fn_name)

        running = init
        for chunk in chunks:
            running = int(fn(running, chunk, len(chunk)))

        oneshot = int(fn(init, full, len(full)))

        if running != oneshot:
            return False, f"{fn_name}: incremental={running} != oneshot={oneshot}"
        return True, f"{fn_name}: incremental == oneshot == {oneshot}"

    # --- call_ge ---
    # Two modes:
    #   Simple: spec has "function", "args", "arg_types", "expected_min" — calls the function
    #           and checks the return value >= expected_min.  Used by zstd.
    #   zlib:   spec has "src_b64" / "src_repeat" — compresses with compress2 and verifies
    #           that compressBound >= the actual compressed size.
    def _call_ge(self, spec: dict) -> tuple[bool, str]:
        if "expected_min" in spec:
            # Simple mode: call function(args) and check >= expected_min
            fn_name = spec["function"]
            raw_args = spec.get("args", [])
            atypes = spec.get("arg_types", ["int"] * len(raw_args))
            args = [_resolve_arg(v, t) for v, t in zip(raw_args, atypes)]
            expected_min = spec["expected_min"]
            try:
                result = int(getattr(self._lib, fn_name)(*args))
            except Exception as exc:
                return False, f"Call to {fn_name}() raised: {exc}"
            if result < expected_min:
                return False, f"{fn_name}({raw_args}) returned {result}, expected >= {expected_min}"
            return True, f"{fn_name}({raw_args}) == {result} >= {expected_min}"

        # zlib mode: compress with compress2, verify compressBound >= actual compressed size
        Z_OK = self._c.get("Z_OK", 0)
        src_raw = base64.b64decode(spec.get("src_b64", "")) if spec.get("src_b64") else b""
        src = src_raw * spec.get("src_repeat", 1)
        level = spec.get("compare_level", -1)

        cap = max(len(src) + len(src) // 10 + 32 + 64, 64)
        dst = ctypes.create_string_buffer(cap)
        dst_len = ctypes.c_ulong(cap)
        ret = int(self._lib.compress2(dst, ctypes.byref(dst_len), src, len(src), level))
        if ret != Z_OK:
            return False, f"compress2() failed ({ret}) while testing compressBound"
        actual = dst_len.value

        bound = int(self._lib.compressBound(len(src)))
        if bound < actual:
            return False, f"compressBound({len(src)})={bound} < actual={actual}: invariant violated"
        return True, f"compressBound({len(src)})={bound} >= actual={actual}"

    # -------------------------------------------------------------------------
    # Python-module pattern handlers (hashlib and similar OO APIs)
    # -------------------------------------------------------------------------

    # --- hash_known_vector ---
    # Creates a fresh hash object, feeds the test input, and checks hexdigest
    # against the known reference value from a published test vector.
    def _hash_known_vector(self, spec: dict) -> tuple[bool, str]:
        alg = spec["algorithm"]
        data = base64.b64decode(spec["data_b64"]) if spec.get("data_b64") else b""
        expected = spec["expected_hex"]
        try:
            h = self._lib.new(alg, data, usedforsecurity=False)
            actual = h.hexdigest()
        except Exception as exc:
            return False, f"{alg}({data!r}) raised: {exc}"
        if actual != expected:
            return False, f"{alg}({data!r}): got {actual}, expected {expected}"
        return True, f"{alg}({data!r}) == {expected}"

    # --- hash_incremental ---
    # Feeds data in multiple chunks and checks the result equals the one-shot digest.
    # Verifies the core streaming property: update(a); update(b) == update(a+b).
    def _hash_incremental(self, spec: dict) -> tuple[bool, str]:
        alg = spec["algorithm"]
        chunks = [base64.b64decode(c) for c in spec["chunks"]]
        full = base64.b64decode(spec["full_data_b64"]) if spec.get("full_data_b64") else b""
        try:
            h_inc = self._lib.new(alg, usedforsecurity=False)
            for chunk in chunks:
                h_inc.update(chunk)
            incremental = h_inc.hexdigest()

            h_one = self._lib.new(alg, full, usedforsecurity=False)
            oneshot = h_one.hexdigest()
        except Exception as exc:
            return False, f"{alg} incremental test raised: {exc}"
        if incremental != oneshot:
            return False, f"{alg}: incremental={incremental} != oneshot={oneshot}"
        return True, f"{alg}: incremental == oneshot == {oneshot}"

    # --- hash_object_attr ---
    # Creates a fresh hash object and checks that a named attribute equals the expected value.
    # Used to verify digest_size, block_size, and name attributes match the RFC specification.
    def _hash_object_attr(self, spec: dict) -> tuple[bool, str]:
        alg = spec["algorithm"]
        attr = spec["attr"]
        expected = spec["expected"]
        try:
            h = self._lib.new(alg, usedforsecurity=False)
            actual = getattr(h, attr)
        except Exception as exc:
            return False, f"{alg}.{attr} raised: {exc}"
        if actual != expected:
            return False, f"{alg}.{attr} == {actual!r}, expected {expected!r}"
        return True, f"{alg}.{attr} == {expected!r}"

    # --- python_set_contains ---
    # Reads a module-level set attribute and checks that all required members are present.
    # Used to verify hashlib.algorithms_guaranteed contains the required algorithm names.
    def _python_set_contains(self, spec: dict) -> tuple[bool, str]:
        attr = spec["attribute"]
        must_contain = spec["must_contain"]
        try:
            actual_set = getattr(self._lib, attr)
        except AttributeError:
            return False, f"Module has no attribute {attr!r}"
        missing = [item for item in must_contain if item not in actual_set]
        if missing:
            return False, f"{attr} missing: {missing}"
        return True, f"{attr} contains all required members"

    # --- hash_digest_consistency ---
    # Checks that h.digest() == bytes.fromhex(h.hexdigest()) — the two output
    # representations of the same hash value must be bit-for-bit identical.
    def _hash_digest_consistency(self, spec: dict) -> tuple[bool, str]:
        alg = spec["algorithm"]
        data = base64.b64decode(spec["data_b64"]) if spec.get("data_b64") else b""
        try:
            h = self._lib.new(alg, data, usedforsecurity=False)
            raw = h.digest()
            hex_str = h.hexdigest()
        except Exception as exc:
            return False, f"{alg} digest_consistency raised: {exc}"
        from_hex = bytes.fromhex(hex_str)
        if raw != from_hex:
            return False, f"{alg}: digest()={raw.hex()} != bytes.fromhex(hexdigest())={from_hex.hex()}"
        if len(raw) != h.digest_size:
            return False, f"{alg}: len(digest())={len(raw)} != digest_size={h.digest_size}"
        return True, f"{alg}: digest() == bytes.fromhex(hexdigest()) ({len(raw)} bytes)"

    # --- hash_copy_independence ---
    # Creates a hash, takes a copy, updates the copy with extra data, and verifies
    # that the original's digest is unchanged. Proves copy() deep-copies the state.
    def _hash_copy_independence(self, spec: dict) -> tuple[bool, str]:
        alg = spec["algorithm"]
        init_data = base64.b64decode(spec["initial_data_b64"]) if spec.get("initial_data_b64") else b""
        extra_data = base64.b64decode(spec["extra_data_b64"]) if spec.get("extra_data_b64") else b""
        try:
            original = self._lib.new(alg, init_data, usedforsecurity=False)
            before = original.hexdigest()
            copy = original.copy()
            copy.update(extra_data)
            after = original.hexdigest()
        except Exception as exc:
            return False, f"{alg} copy_independence raised: {exc}"
        if before != after:
            return False, f"{alg}: original digest changed after updating copy: {before} -> {after}"
        return True, f"{alg}: original digest unchanged after updating copy"

    # --- hash_api_equivalence ---
    # Verifies that hashlib.new(alg, data) produces the same digest as the
    # algorithm-specific shorthand constructor (e.g. hashlib.sha256(data)).
    def _hash_api_equivalence(self, spec: dict) -> tuple[bool, str]:
        alg = spec["algorithm"]
        data = base64.b64decode(spec["data_b64"]) if spec.get("data_b64") else b""
        try:
            via_new = self._lib.new(alg, data, usedforsecurity=False).hexdigest()
            constructor = getattr(self._lib, alg)
            via_constructor = constructor(data, usedforsecurity=False).hexdigest()
        except Exception as exc:
            return False, f"{alg} api_equivalence raised: {exc}"
        if via_new != via_constructor:
            return False, f"{alg}: new()={via_new} != {alg}()={via_constructor}"
        return True, f"{alg}: hashlib.new({alg!r}, ...) == hashlib.{alg}(...) == {via_new}"

    # -------------------------------------------------------------------------
    # General Python-module pattern handlers (base64, json, struct, …)
    # -------------------------------------------------------------------------

    # Typed-value resolver used by python_call_eq / python_call_raises.
    # Supported type tokens:
    #   "bytes_b64"   — base64-decode the value string to bytes
    #   "bytes_ascii" — encode the value string as ASCII to bytes
    #   "bytes_hex"   — hex-decode the value string to bytes
    #   "str"         — use as-is (string)
    #   "int"         — coerce to int
    #   "float"       — coerce to float
    #   "bool"        — coerce to bool
    #   "null"        — return None
    #   "tuple"       — convert list value to tuple
    #   "json"        — pass through (already JSON-decoded)
    # Raw JSON scalars (str, int, float, bool, None) are passed through unchanged.
    def _resolve_typed(self, v):
        if isinstance(v, dict) and "type" in v:
            t = v["type"]
            val = v.get("value")
            if t == "bytes_b64":
                return base64.b64decode(val) if val else b""
            if t == "bytes_ascii":
                return val.encode("ascii") if val else b""
            if t == "bytes_hex":
                return bytes.fromhex(val) if val else b""
            if t == "str":
                return str(val) if val is not None else ""
            if t == "int":
                return int(val)
            if t == "float":
                return float(val)
            if t == "bool":
                return bool(val)
            if t == "null":
                return None
            if t == "tuple":
                return tuple(val) if val is not None else ()
            if t == "json":
                return val
        return v  # raw JSON scalar: str, int, float, bool, None pass through

    # --- python_call_eq ---
    # Calls module.function(*args, **kwargs) and checks the result equals expected.
    # function may be a dotted path (e.g. "date.fromisoformat") which is resolved
    # by walking attribute access from the module root.
    # Handles tuple/list comparison symmetrically (struct.unpack returns tuples).
    def _python_call_eq(self, spec: dict) -> tuple[bool, str]:
        fn_name = spec["function"]
        obj = self._lib
        for part in fn_name.split("."):
            obj = getattr(obj, part, None)
            if obj is None:
                return False, f"Module has no attribute {fn_name!r}"
        fn = obj
        args = [self._resolve_typed(a) for a in spec.get("args", [])]
        kwargs = {k: self._resolve_typed(v) for k, v in spec.get("kwargs", {}).items()}
        expected = self._resolve_typed(spec["expected"])
        try:
            result = fn(*args, **kwargs)
        except Exception as exc:
            return False, f"{fn_name}() raised: {exc}"
        # Optional method chaining: call result.method(*method_args)
        method = spec.get("method")
        if method:
            method_args = [self._resolve_typed(a) for a in spec.get("method_args", [])]
            m = getattr(result, method, None)
            if m is None:
                return False, f"Result {result!r} has no attribute {method!r}"
            if callable(m):
                try:
                    result = m(*method_args)
                except Exception as exc:
                    return False, f"{fn_name}().{method}() raised: {exc}"
            else:
                result = m
            # Optional second chain: result.method_chain()
            method_chain = spec.get("method_chain")
            if method_chain:
                mc = getattr(result, method_chain, None)
                if mc is None:
                    return False, f"Result {result!r} has no attribute {method_chain!r}"
                if callable(mc):
                    try:
                        result = mc()
                    except Exception as exc:
                        return False, f".{method_chain}() raised: {exc}"
                else:
                    result = mc
        # Normalize: compare tuple results against list expectations by converting to list
        r = list(result) if isinstance(result, tuple) and isinstance(expected, list) else result
        e = list(expected) if isinstance(expected, tuple) and isinstance(result, list) else expected
        if r != e:
            return False, f"{fn_name}() returned {result!r}, expected {expected!r}"
        return True, f"{fn_name}() == {result!r}"

    # --- python_call_raises ---
    # Calls module.function(*args, **kwargs) and checks that it raises the named exception.
    # expected_exception may be a short name ("ValueError"), a qualified module name
    # ("json.JSONDecodeError", "binascii.Error"), or the internal qualified name
    # ("json.decoder.JSONDecodeError"). Matching uses isinstance() so re-exported
    # exception classes (like json.JSONDecodeError -> json.decoder.JSONDecodeError) work.
    def _python_call_raises(self, spec: dict) -> tuple[bool, str]:
        fn_name = spec["function"]
        obj = self._lib
        for part in fn_name.split("."):
            obj = getattr(obj, part, None)
            if obj is None:
                return False, f"Module has no attribute {fn_name!r}"
        fn = obj
        args = [self._resolve_typed(a) for a in spec.get("args", [])]
        kwargs = {k: self._resolve_typed(v) for k, v in spec.get("kwargs", {}).items()}
        expected_exc = spec["expected_exception"]
        try:
            result = fn(*args, **kwargs)
        except Exception as exc:
            qualname = f"{type(exc).__module__}.{type(exc).__qualname__}"
            short = type(exc).__name__
            # Fast path: match by name strings
            if expected_exc in (qualname, short) or qualname.endswith(f".{expected_exc}"):
                return True, f"{fn_name}() raised {short} as expected"
            # Slow path: try to resolve the dotted name and use isinstance()
            # Handles re-exports like json.JSONDecodeError -> json.decoder.JSONDecodeError
            parts = expected_exc.rsplit(".", 1)
            if len(parts) == 2:
                try:
                    mod = importlib.import_module(parts[0])
                    cls = getattr(mod, parts[1])
                    if isinstance(exc, cls):
                        return True, f"{fn_name}() raised {short} as expected"
                except (ImportError, AttributeError):
                    pass
            return False, f"{fn_name}() raised {qualname}, expected {expected_exc}"
        return False, f"{fn_name}() returned {result!r} without raising"

    # --- python_encode_decode_roundtrip ---
    # Encodes each input with encode_fn, then decodes the result with decode_fn,
    # and verifies the decoded output equals the original bytes.
    # Used for base64 variants: b64encode/b64decode, urlsafe_b64encode/urlsafe_b64decode.
    def _python_encode_decode_roundtrip(self, spec: dict) -> tuple[bool, str]:
        enc = getattr(self._lib, spec["encode_fn"])
        dec = getattr(self._lib, spec["decode_fn"])
        inputs = spec["inputs_b64"]
        for item in inputs:
            original = base64.b64decode(item) if item else b""
            try:
                encoded = enc(original)
                decoded = dec(encoded)
            except Exception as exc:
                return False, f"roundtrip raised for {original!r}: {exc}"
            if decoded != original:
                return False, (
                    f"roundtrip mismatch for {original!r}: "
                    f"encoded={encoded!r}, decoded={decoded!r}"
                )
        return True, f"all {len(inputs)} inputs round-tripped via {spec['encode_fn']}/{spec['decode_fn']}"

    # --- lz4_roundtrip ---
    # Calls LZ4_compressBound to size the output buffer, then LZ4_compress_default
    # to compress, then LZ4_decompress_safe to decompress, and verifies byte-perfect
    # recovery for each input in spec["inputs_b64"] (base64-encoded byte strings).
    def _lz4_roundtrip(self, spec: dict) -> tuple[bool, str]:
        lib = self._lib
        # Set up function signatures
        compress_bound = lib.LZ4_compressBound
        compress_bound.restype = ctypes.c_int
        compress_bound.argtypes = [ctypes.c_int]

        compress_fn = lib.LZ4_compress_default
        compress_fn.restype = ctypes.c_int
        compress_fn.argtypes = [
            ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_int
        ]

        decompress_fn = lib.LZ4_decompress_safe
        decompress_fn.restype = ctypes.c_int
        decompress_fn.argtypes = [
            ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_int
        ]

        inputs = spec.get("inputs_b64", [])
        for item in inputs:
            original = base64.b64decode(item) if item else b""
            src_size = len(original)

            # Compress
            bound = int(compress_bound(max(src_size, 1)))
            dst = ctypes.create_string_buffer(bound)
            comp_size = int(compress_fn(original, dst, src_size, bound))
            if comp_size <= 0:
                return False, (
                    f"LZ4_compress_default() returned {comp_size} for "
                    f"{src_size}-byte input; expected > 0"
                )

            # Decompress
            rec_cap = max(src_size * 2 + 64, 64)
            rec = ctypes.create_string_buffer(rec_cap)
            dec_size = int(decompress_fn(dst.raw[:comp_size], rec, comp_size, rec_cap))
            if dec_size < 0:
                return False, (
                    f"LZ4_decompress_safe() returned {dec_size}; expected >= 0"
                )
            recovered = rec.raw[:dec_size]
            if recovered != original:
                return False, (
                    f"roundtrip mismatch: recovered {dec_size} bytes, "
                    f"expected {src_size}"
                )
        return True, f"all {len(inputs)} inputs round-tripped via LZ4_compress_default/LZ4_decompress_safe"

    # --- pcre2_match ---
    # Compiles a PCRE2 pattern with pcre2_compile_8, creates match data with
    # pcre2_match_data_create_from_pattern_8, runs pcre2_match_8, and checks
    # that the return code equals expected_rc.
    #
    # On a successful match, pcre2_match_8 returns the number of pairs in the
    # ovector (capture count + 1, >= 1).  On no match it returns
    # PCRE2_ERROR_NOMATCH (-1).
    #
    # spec fields:
    #   pattern_b64  — base64-encoded UTF-8 pattern string
    #   subject_b64  — base64-encoded subject string to match against
    #   expected_rc  — expected pcre2_match_8 return code
    def _pcre2_match(self, spec: dict) -> tuple[bool, str]:
        lib = self._lib
        pattern = base64.b64decode(spec["pattern_b64"])
        subject = base64.b64decode(spec["subject_b64"])
        expected_rc = spec["expected_rc"]

        # Set up pcre2_compile_8 signature
        compile_fn = lib.pcre2_compile_8
        compile_fn.restype = ctypes.c_void_p
        compile_fn.argtypes = [
            ctypes.c_char_p,           # pattern
            ctypes.c_size_t,           # length (PCRE2_ZERO_TERMINATED = ~0)
            ctypes.c_uint32,           # options
            ctypes.POINTER(ctypes.c_int),        # errorcode output
            ctypes.POINTER(ctypes.c_size_t),     # erroroffset output
            ctypes.c_void_p,           # compile context (NULL)
        ]

        errorcode = ctypes.c_int(0)
        erroroffset = ctypes.c_size_t(0)
        PCRE2_ZERO_TERMINATED = ctypes.c_size_t(~0)

        code = compile_fn(
            pattern, PCRE2_ZERO_TERMINATED, 0,
            ctypes.byref(errorcode), ctypes.byref(erroroffset), None,
        )
        if code is None or code == 0:
            # Compile failed; get error message for diagnostics
            try:
                errbuf = ctypes.create_string_buffer(256)
                lib.pcre2_get_error_message_8.restype = ctypes.c_int
                lib.pcre2_get_error_message_8(errorcode.value, errbuf, 256)
                errmsg = errbuf.value.decode("ascii", errors="replace")
            except Exception:
                errmsg = f"errorcode={errorcode.value}"
            return False, (
                f"pcre2_compile_8({pattern!r}) failed at offset {erroroffset.value}: {errmsg}"
            )

        try:
            # Create match data block
            md_fn = lib.pcre2_match_data_create_from_pattern_8
            md_fn.restype = ctypes.c_void_p
            md_fn.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
            md = md_fn(code, None)
            if md is None or md == 0:
                return False, "pcre2_match_data_create_from_pattern_8() returned NULL"

            try:
                # Run match
                match_fn = lib.pcre2_match_8
                match_fn.restype = ctypes.c_int
                match_fn.argtypes = [
                    ctypes.c_void_p,   # code
                    ctypes.c_char_p,   # subject
                    ctypes.c_size_t,   # length
                    ctypes.c_size_t,   # startoffset
                    ctypes.c_uint32,   # options
                    ctypes.c_void_p,   # match_data
                    ctypes.c_void_p,   # match context (NULL)
                ]
                rc = int(match_fn(code, subject, len(subject), 0, 0, md, None))
            finally:
                lib.pcre2_match_data_free_8.argtypes = [ctypes.c_void_p]
                lib.pcre2_match_data_free_8(md)
        finally:
            lib.pcre2_code_free_8.argtypes = [ctypes.c_void_p]
            lib.pcre2_code_free_8(code)

        if rc != expected_rc:
            return False, (
                f"pcre2_match_8({pattern!r}, {subject!r}) returned {rc}, "
                f"expected {expected_rc}"
            )
        return True, (
            f"pcre2_match_8({pattern!r}, {subject!r}) == {expected_rc}"
        )

    # --- python_struct_roundtrip ---
    # For each entry in test_cases (a list of value-lists), packs with
    # struct.pack(fmt, *values) then unpacks and verifies lossless recovery.
    # Falls back to the "values" field (treated as a single test case) for
    # multi-field formats where all values are packed together.
    def _python_struct_roundtrip(self, spec: dict) -> tuple[bool, str]:
        fmt = spec["format"]
        test_cases = spec.get("test_cases") or [spec["values"]]
        for values in test_cases:
            try:
                packed = self._lib.pack(fmt, *values)
                unpacked = self._lib.unpack(fmt, packed)
            except Exception as exc:
                return False, f"struct roundtrip raised for {fmt!r} {values}: {exc}"
            if list(unpacked) != values:
                return False, (
                    f"struct roundtrip failed for {fmt!r}: "
                    f"{list(unpacked)} != {values}"
                )
        return True, f"struct.unpack({fmt!r}, pack({fmt!r}, ...)) ok for {len(test_cases)} case(s)"

    # --- python_sqlite_roundtrip ---
    # Opens an in-memory SQLite database, executes setup_sql statements, runs
    # query_sql, fetches all rows, converts each row to a plain list, and
    # compares against expected_rows.  Works with any python_module spec that
    # has access to sqlite3 (the stdlib module).
    def _python_sqlite_roundtrip(self, spec: dict) -> tuple[bool, str]:
        import sqlite3 as _sqlite3
        setup_sql    = spec.get("setup_sql", [])
        query_sql    = spec["query_sql"]
        expected_rows = spec["expected_rows"]
        try:
            con = _sqlite3.connect(":memory:")
            for stmt in setup_sql:
                con.execute(stmt)
            rows = [list(r) for r in con.execute(query_sql).fetchall()]
            con.close()
        except Exception as exc:
            return False, f"sqlite3 raised: {exc}"
        if rows != expected_rows:
            return False, f"query returned {rows!r}, expected {expected_rows!r}"
        return True, f"sqlite3 roundtrip ok: {len(rows)} row(s)"

    # -------------------------------------------------------------------------
    # CLI / subprocess pattern handlers
    # -------------------------------------------------------------------------

    # Internal helper: run the CLI command and return the CompletedProcess.
    # stdin_b64=None means no stdin is connected; stdin_b64="" means empty stdin.
    def _cli_run(self, spec: dict) -> subprocess.CompletedProcess:
        args = spec.get("args", [])
        cmd = [self._lib.command] + [str(a) for a in args]
        stdin_b64 = spec.get("stdin_b64")
        stdin_data = (
            base64.b64decode(stdin_b64) if stdin_b64 else b""
        ) if stdin_b64 is not None else None
        timeout = spec.get("timeout", 10)
        return subprocess.run(
            cmd, input=stdin_data, capture_output=True, timeout=timeout
        )

    # --- cli_exits_with ---
    # Runs the command and checks its exit code equals expected_exit.
    # Use expected_exit: 0 for success, any other value for expected failure.
    def _cli_exits_with(self, spec: dict) -> tuple[bool, str]:
        expected = spec["expected_exit"]
        try:
            proc = self._cli_run(spec)
        except subprocess.TimeoutExpired:
            return False, f"command timed out after {spec.get('timeout', 10)}s"
        except Exception as exc:
            return False, f"subprocess raised: {exc}"
        if proc.returncode != expected:
            stderr = proc.stderr.decode("utf-8", errors="replace").strip()
            return False, (
                f"exit code {proc.returncode}, expected {expected}"
                + (f" (stderr: {stderr!r})" if stderr else "")
            )
        return True, f"exit code {proc.returncode} as expected"

    # --- cli_stdout_eq ---
    # Runs the command and checks stdout (trailing whitespace stripped) equals
    # the expected string exactly. Use cli_stdout_contains when the output format
    # may vary across tool versions.
    def _cli_stdout_eq(self, spec: dict) -> tuple[bool, str]:
        expected = spec["expected"]
        try:
            proc = self._cli_run(spec)
        except subprocess.TimeoutExpired:
            return False, "command timed out"
        except Exception as exc:
            return False, f"subprocess raised: {exc}"
        actual = proc.stdout.decode("utf-8", errors="replace").rstrip()
        if actual != expected:
            return False, f"stdout {actual!r}, expected {expected!r}"
        return True, f"stdout == {expected!r}"

    # --- cli_stdout_contains ---
    # Runs the command and checks that the expected substring appears in stdout.
    # Used for hash output where the algorithm-name prefix varies across
    # OpenSSL/LibreSSL versions but the hex digest is always present.
    def _cli_stdout_contains(self, spec: dict) -> tuple[bool, str]:
        expected = spec["expected_substring"]
        try:
            proc = self._cli_run(spec)
        except subprocess.TimeoutExpired:
            return False, "command timed out"
        except Exception as exc:
            return False, f"subprocess raised: {exc}"
        stdout = proc.stdout.decode("utf-8", errors="replace")
        if expected not in stdout:
            return False, f"expected {expected!r} not found in stdout {stdout!r}"
        return True, f"stdout contains {expected!r}"

    # --- cli_stdout_matches ---
    # Runs the command and checks that stdout matches the given regular expression.
    # Used when we need to verify the structure of the output, not just a substring.
    def _cli_stdout_matches(self, spec: dict) -> tuple[bool, str]:
        pattern = spec["pattern"]
        flags = _re.MULTILINE if spec.get("multiline") else 0
        try:
            proc = self._cli_run(spec)
        except subprocess.TimeoutExpired:
            return False, "command timed out"
        except Exception as exc:
            return False, f"subprocess raised: {exc}"
        stdout = proc.stdout.decode("utf-8", errors="replace")
        if not _re.search(pattern, stdout, flags):
            return False, f"stdout {stdout!r} does not match pattern {pattern!r}"
        return True, f"stdout matches {pattern!r}"

    # --- cli_stderr_contains ---
    # Runs the command and checks that the expected substring appears in stderr.
    # Used to verify error messages for invalid commands or arguments.
    def _cli_stderr_contains(self, spec: dict) -> tuple[bool, str]:
        expected = spec["expected_substring"]
        try:
            proc = self._cli_run(spec)
        except subprocess.TimeoutExpired:
            return False, "command timed out"
        except Exception as exc:
            return False, f"subprocess raised: {exc}"
        stderr = proc.stderr.decode("utf-8", errors="replace")
        if expected not in stderr:
            return False, f"expected {expected!r} not found in stderr {stderr!r}"
        return True, f"stderr contains {expected!r}"

    # --- node_module_call_eq ---
    # Builds an inline node -e script that requires the npm module, calls the
    # named function with JSON-serialised args, and compares the JSON.stringify
    # of the return value against json.dumps(expected).  JSON is valid JavaScript
    # so args round-trip without any transformation.
    def _node_module_call_eq(self, spec: dict) -> tuple[bool, str]:
        module   = spec.get("module") or getattr(self._lib, "module_name", None)
        fn_name  = spec.get("function")   # None → call the module itself as a function
        args     = spec.get("args", [])
        expected = spec["expected"]
        args_js  = json.dumps(args)
        # When fn_name is None the module is a plain callable (e.g. minimist).
        if fn_name:
            call_expr = f"m[{json.dumps(fn_name)}](...{args_js})"
        else:
            call_expr = f"m(...{args_js})"
        if getattr(self._lib, "esm", False):
            script = (
                f"(async()=>{{const m=await import({json.dumps(module)});"
                f"process.stdout.write(JSON.stringify({call_expr}))}})();"
            )
        else:
            script = (
                f"const m=require({json.dumps(module)});"
                f"process.stdout.write(JSON.stringify({call_expr}))"
            )
        cmd = [self._lib.command, "-e", script]
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=spec.get("timeout", 10))
        except subprocess.TimeoutExpired:
            return False, "node timed out"
        except Exception as exc:
            return False, f"subprocess raised: {exc}"
        if proc.returncode != 0:
            stderr = proc.stderr.decode("utf-8", errors="replace").strip()
            return False, f"node exited {proc.returncode}: {stderr!r}"
        actual        = proc.stdout.decode("utf-8", errors="replace").strip()
        # Use compact separators to match JSON.stringify's no-space output.
        expected_json = json.dumps(expected, separators=(",", ":"))
        label         = fn_name or "<module>"
        if actual != expected_json:
            return False, f"{label}({args!r}) returned {actual!r}, expected {expected_json!r}"
        return True, f"{label}({args!r}) == {expected!r}"

    # --- node_constructor_call_eq ---
    # Instantiates a class from the npm module, calls a method on the instance,
    # and optionally calls the result as a function (for compile-then-call APIs
    # like Ajv).
    #
    # spec fields:
    #   class       — property on the module to use as constructor (default "default")
    #   ctor_args   — args to constructor (default [])
    #   method      — method to call on the instance
    #   args        — args to pass to the method
    #   then_call   — if true, call the method result as a function with then_args
    #   then_args   — args to pass to the chained call (default [])
    #   expected    — expected final value
    def _node_constructor_call_eq(self, spec: dict) -> tuple[bool, str]:
        module     = spec.get("module") or getattr(self._lib, "module_name", None)
        cls_name   = spec.get("class", "default")
        ctor_args  = spec.get("ctor_args", [])
        method     = spec["method"]
        args       = spec.get("args", [])
        then_call  = spec.get("then_call", False)
        then_args  = spec.get("then_args", [])
        expected   = spec["expected"]

        ctor_js      = json.dumps(ctor_args)
        method_js    = json.dumps(method)
        args_js      = json.dumps(args)
        then_args_js = json.dumps(then_args)

        if then_call:
            result_expr = f"inst[{method_js}](...{args_js})(...{then_args_js})"
        else:
            result_expr = f"inst[{method_js}](...{args_js})"

        if getattr(self._lib, "esm", False):
            script = (
                f"(async()=>{{const m=await import({json.dumps(module)});"
                f"const Cls=m[{json.dumps(cls_name)}];"
                f"const inst=new Cls(...{ctor_js});"
                f"process.stdout.write(JSON.stringify({result_expr}))}})();"
            )
        else:
            script = (
                f"const m=require({json.dumps(module)});"
                f"const Cls=m[{json.dumps(cls_name)}];"
                f"const inst=new Cls(...{ctor_js});"
                f"process.stdout.write(JSON.stringify({result_expr}))"
            )
        cmd = [self._lib.command, "-e", script]
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=spec.get("timeout", 10))
        except subprocess.TimeoutExpired:
            return False, "node timed out"
        except Exception as exc:
            return False, f"subprocess raised: {exc}"
        if proc.returncode != 0:
            stderr = proc.stderr.decode("utf-8", errors="replace").strip()
            return False, f"node exited {proc.returncode}: {stderr!r}"
        actual        = proc.stdout.decode("utf-8", errors="replace").strip()
        expected_json = json.dumps(expected, separators=(",", ":"))
        label         = f"new {cls_name}().{method}"
        if actual != expected_json:
            return False, f"{label}({args!r}) returned {actual!r}, expected {expected_json!r}"
        return True, f"{label}({args!r}) == {expected!r}"

    # --- node_factory_call_eq ---
    # Calls the module (or a named factory function on the module) as a plain
    # function (no 'new'), then calls a method on the returned instance, and
    # compares the JSON-stringified result against the expected value.
    #
    # This covers factory-function APIs where the module itself is the factory
    # (e.g. express()) or where a named factory is called without 'new'
    # (e.g. express.Router()).
    #
    # spec fields:
    #   factory     — property on the module to call as factory; null → call m() directly
    #   factory_args — args to the factory call (default [])
    #   method       — method to call on the returned instance
    #   method_args  — args to pass to the method (default [])
    #   expected     — expected final value
    def _node_factory_call_eq(self, spec: dict) -> tuple[bool, str]:
        module       = spec.get("module") or getattr(self._lib, "module_name", None)
        factory      = spec.get("factory")          # None → call m() directly
        factory_args = spec.get("factory_args", [])
        method       = spec["method"]
        method_args  = spec.get("method_args", [])
        expected     = spec["expected"]

        factory_args_js = json.dumps(factory_args)
        method_js       = json.dumps(method)
        method_args_js  = json.dumps(method_args)

        if factory:
            inst_expr = f"m[{json.dumps(factory)}](...{factory_args_js})"
        else:
            inst_expr = f"m(...{factory_args_js})"

        result_expr = f"({inst_expr})[{method_js}](...{method_args_js})"

        if getattr(self._lib, "esm", False):
            script = (
                f"(async()=>{{const m=await import({json.dumps(module)});"
                f"process.stdout.write(JSON.stringify({result_expr}))}})();"
            )
        else:
            script = (
                f"const m=require({json.dumps(module)});"
                f"process.stdout.write(JSON.stringify({result_expr}))"
            )
        cmd = [self._lib.command, "-e", script]
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=spec.get("timeout", 10))
        except subprocess.TimeoutExpired:
            return False, "node timed out"
        except Exception as exc:
            return False, f"subprocess raised: {exc}"
        if proc.returncode != 0:
            stderr = proc.stderr.decode("utf-8", errors="replace").strip()
            return False, f"node exited {proc.returncode}: {stderr!r}"
        actual        = proc.stdout.decode("utf-8", errors="replace").strip()
        expected_json = json.dumps(expected, separators=(",", ":"))
        label         = f"{factory or '<module>'}().{method}"
        if actual != expected_json:
            return False, f"{label}({method_args!r}) returned {actual!r}, expected {expected_json!r}"
        return True, f"{label}({method_args!r}) == {expected!r}"


# ---------------------------------------------------------------------------
# Invariant runner
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Version detection helpers
# ---------------------------------------------------------------------------

def _get_lib_version(lib_spec: dict, lib) -> str:
    """Return the installed version of the library as a string, or '' if unknown.

    Strategy per backend:
    - ctypes: call lib.<version_function>() if specified in the spec
    - python_module: try importlib.metadata.version(module_name), then sys.version for stdlib
    - cli (node): run `node -e "process.stdout.write(require('<mod>/package.json').version)"`
    """
    backend = lib_spec.get("backend", "ctypes")
    module_name = lib_spec.get("module_name", "")

    if backend == "python_module":
        try:
            return importlib.metadata.version(module_name)
        except importlib.metadata.PackageNotFoundError:
            pass
        # stdlib modules don't appear in metadata; use the Python version as a proxy
        vi = sys.version_info
        return f"{vi.major}.{vi.minor}.{vi.micro}"

    if backend == "cli" and module_name:
        # Ask node to read the package.json version
        cmd = lib_spec.get("command", "node")
        script = (
            f"try{{process.stdout.write(require({json.dumps(module_name + '/package.json')}).version)}}"
            f"catch(e){{process.exit(1)}}"
        )
        try:
            r = subprocess.run([cmd, "-e", script], capture_output=True, timeout=5)
            if r.returncode == 0:
                return r.stdout.decode("utf-8", errors="replace").strip()
        except Exception:
            pass
        return ""

    if backend == "ctypes":
        ver_fn_name = lib_spec.get("version_function")
        if ver_fn_name:
            try:
                ver_fn = getattr(lib, ver_fn_name)
                ver_fn.restype = ctypes.c_char_p
                result = ver_fn()
                return (result or b"").decode("ascii", errors="replace")
            except Exception:
                pass

    return ""


def _check_spec_version(spec_for_versions: str, lib_version: str) -> tuple[bool, str]:
    """Check whether lib_version satisfies spec_for_versions range.

    Returns (ok, warning_message). ok=True means satisfied or cannot determine.
    Uses packaging.specifiers if available; falls back to a simple prefix check.
    """
    if not spec_for_versions or spec_for_versions.startswith("N/A") or not lib_version:
        return True, ""

    try:
        from packaging.specifiers import SpecifierSet  # type: ignore
        from packaging.version import Version, InvalidVersion  # type: ignore
        try:
            # Normalize space-separated specifiers to comma-separated (packaging requires commas)
            normalized = _re.sub(r"\s+(?=[<>=!])", ",", spec_for_versions.strip())
            spec_set = SpecifierSet(normalized)
            ver = Version(lib_version)
            ok = ver in spec_set
            if not ok:
                return False, (
                    f"Library version {lib_version!r} does not satisfy "
                    f"spec_for_versions {spec_for_versions!r}"
                )
            return True, ""
        except InvalidVersion:
            return True, ""  # can't parse version — skip check
    except ImportError:
        pass

    # Fallback: handle simple ">=X.Y" by comparing major.minor
    m = _re.match(r"^>=(\d+)\.(\d+)", spec_for_versions)
    if m:
        req_major, req_minor = int(m.group(1)), int(m.group(2))
        vm = _re.match(r"^(\d+)\.(\d+)", lib_version)
        if vm:
            inst_major, inst_minor = int(vm.group(1)), int(vm.group(2))
            ok = (inst_major, inst_minor) >= (req_major, req_minor)
            if not ok:
                return False, (
                    f"Library version {lib_version!r} does not satisfy "
                    f"spec_for_versions {spec_for_versions!r}"
                )
    return True, ""


def _semver_satisfies(version_str: str, constraint: str) -> bool:
    """Return True if version_str satisfies the semver constraint.

    Constraint syntax: standard specifier set, e.g. ">=1.2", ">=1.2 <2.0".
    Uses packaging.specifiers if available; falls back to a simple prefix check.
    Returns False (do not skip) when version_str is empty or unparseable.
    """
    if not version_str or not constraint:
        return False
    try:
        from packaging.specifiers import SpecifierSet  # type: ignore
        from packaging.version import Version, InvalidVersion  # type: ignore
        try:
            normalized = _re.sub(r"\s+(?=[<>=!])", ",", constraint.strip())
            return Version(version_str) in SpecifierSet(normalized)
        except (InvalidVersion, ValueError):
            return False
    except ImportError:
        pass
    # Fallback: handle simple ">=X.Y" by comparing major.minor
    m = _re.match(r"^>=(\d+)\.(\d+)", constraint)
    if m:
        req = (int(m.group(1)), int(m.group(2)))
        vm = _re.match(r"^(\d+)\.(\d+)", version_str)
        if vm:
            return (int(vm.group(1)), int(vm.group(2))) >= req
    return False


def _build_skip_context(lib_version: str) -> dict:
    """Build the evaluation context for skip_if expressions.

    Available variables:
      lib_version          — library version string (e.g. "1.2.12")
      platform             — OS identifier: "darwin", "linux", "freebsd", "win32"
      semver_satisfies(v, c) — True if version string v satisfies constraint c
                               e.g. semver_satisfies(lib_version, ">=1.3")
    """
    import sys as _sys
    platform_str = _sys.platform  # "darwin", "linux", "freebsd", "win32", ...
    # Normalize "linux2" → "linux" for cleaner expressions
    if platform_str.startswith("linux"):
        platform_str = "linux"
    return {
        "lib_version": lib_version,
        "platform": platform_str,
        "semver_satisfies": _semver_satisfies,
    }


class InvariantRunner:
    def build_constants_map(self, constants: dict) -> dict:
        """Flatten grouped constants {group: [{name, value, ...}]} to {name: value}."""
        flat = {}
        for group in constants.values():
            if isinstance(group, list):
                for entry in group:
                    if isinstance(entry, dict) and "name" in entry and "value" in entry:
                        flat[entry["name"]] = entry["value"]
        return flat

    def run_all(
        self,
        spec: dict,
        lib,
        filter_category: str | None = None,
        lib_version: str = "",
    ) -> list[Result]:
        cmap = self.build_constants_map(spec["constants"])
        registry = PatternRegistry(lib, cmap)
        results: list[Result] = []

        for inv in spec["invariants"]:
            if filter_category and inv.get("category") != filter_category:
                continue

            # Evaluate skip_if expression if present
            skip_expr = inv.get("skip_if")
            if skip_expr:
                try:
                    should_skip = bool(
                        eval(skip_expr, {"__builtins__": {}},  # noqa: S307
                             _build_skip_context(lib_version))
                    )
                except Exception:
                    should_skip = False
                if should_skip:
                    results.append(Result(inv["id"], True, "skipped", skip_reason=skip_expr))
                    continue

            try:
                passed, msg = registry.run(inv)
            except Exception as exc:
                passed, msg = False, f"HARNESS ERROR: {exc}"

            results.append(Result(inv["id"], passed, msg))

        return results


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify a Z-layer behavioral spec against an installed library"
    )
    parser.add_argument("spec", type=Path, help="Path to .zspec.json file")
    parser.add_argument(
        "--filter", dest="filter_category",
        help="Only run invariants in this category",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Print all results, not just failures",
    )
    parser.add_argument(
        "--list", action="store_true",
        help="List invariant IDs and descriptions, then exit",
    )
    parser.add_argument(
        "--json-out", type=Path,
        help="Write results as JSON to this file",
    )
    parser.add_argument(
        "--baseline", type=Path,
        help=(
            "Compare results against a previous --json-out file. "
            "Prints regressions (pass→fail), fixes (fail→pass), and new/removed invariants. "
            "Exits non-zero if there are any regressions."
        ),
    )
    parser.add_argument(
        "--watch", action="store_true",
        help=(
            "Re-run the spec automatically whenever the .zspec.json file is saved. "
            "Clears the terminal before each run. Press Ctrl-C to stop."
        ),
    )
    args = parser.parse_args(argv)

    try:
        spec = SpecLoader().load(args.spec)
    except SpecError as exc:
        print(f"ERROR loading spec: {exc}", file=sys.stderr)
        return 2

    try:
        lib = LibraryLoader().load(spec["library"])
    except LibraryNotFoundError as exc:
        print(f"ERROR loading library: {exc}", file=sys.stderr)
        return 2

    if args.list:
        for inv in spec["invariants"]:
            print(
                f"{inv['id']:55s}  [{inv.get('category', '?'):15s}]  "
                f"{inv.get('description', '')}"
            )
        return 0

    def _run_once() -> int:
        lib_version = _get_lib_version(spec["library"], lib)
        ver_ok, ver_warn = _check_spec_version(
            spec.get("identity", {}).get("spec_for_versions", ""),
            lib_version,
        )
        if lib_version:
            print(f"Library version: {lib_version}")
        if not ver_ok:
            print(f"WARNING: {ver_warn}", file=sys.stderr)

        runner = InvariantRunner()
        results = runner.run_all(spec, lib, filter_category=args.filter_category, lib_version=lib_version)

        passed  = sum(1 for r in results if r.passed and not r.skip_reason)
        failed  = sum(1 for r in results if not r.passed)
        skipped = sum(1 for r in results if r.skip_reason)

        for r in results:
            if r.skip_reason:
                tag = "SKIP"
            elif r.passed:
                tag = "PASS"
            else:
                tag = "FAIL"
            if not r.passed or r.skip_reason or args.verbose:
                print(f"  {tag}  {r.inv_id}: {r.message}")

        print(f"\n{len(results)} invariants: {passed} passed, {failed} failed, {skipped} skipped")

        out = [
            {
                "id": r.inv_id,
                "passed": r.passed,
                "message": r.message,
                "skip_reason": r.skip_reason,
            }
            for r in results
        ]

        if args.json_out:
            args.json_out.write_text(json.dumps(out, indent=2), encoding="utf-8")

        if args.baseline:
            regressions = _diff_results(args.baseline, out)
            if regressions > 0:
                return 1
            return 0

        return 1 if failed > 0 else 0

    if not args.watch:
        return _run_once()

    # --watch mode: poll the spec file for changes and re-run on every save
    import time as _time
    import os as _os
    spec_file = args.spec.resolve()
    try:
        last_mtime = spec_file.stat().st_mtime
    except OSError:
        last_mtime = 0.0
    print(f"Watching {spec_file} — press Ctrl-C to stop.\n")
    # Run immediately on startup
    _os.system("clear" if sys.platform != "win32" else "cls")
    _run_once()
    try:
        while True:
            _time.sleep(0.5)
            try:
                mtime = spec_file.stat().st_mtime
            except OSError:
                continue
            if mtime != last_mtime:
                last_mtime = mtime
                _os.system("clear" if sys.platform != "win32" else "cls")
                # Reload spec from disk on each change
                try:
                    spec.update(SpecLoader().load(spec_file))
                except SpecError as exc:
                    print(f"ERROR reloading spec: {exc}", file=sys.stderr)
                    continue
                _run_once()
    except KeyboardInterrupt:
        print("\nWatch mode stopped.")
        return 0


def _diff_results(baseline_path: Path, current: list[dict]) -> int:
    """
    Load baseline results from baseline_path, diff against current results,
    print a summary, and return the number of regressions (pass→fail).
    """
    try:
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR reading baseline {baseline_path}: {exc}", file=sys.stderr)
        return 1

    b_by_id = {r["id"]: r for r in baseline}
    c_by_id = {r["id"]: r for r in current}

    regressions: list[str] = []
    fixes:       list[str] = []
    added:       list[str] = []
    removed:     list[str] = []

    for inv_id, cur in c_by_id.items():
        if inv_id not in b_by_id:
            added.append(inv_id)
        else:
            b_passed = b_by_id[inv_id]["passed"]
            c_passed = cur["passed"]
            if b_passed and not c_passed:
                regressions.append(f"  REGRESSION  {inv_id}: {cur['message']}")
            elif not b_passed and c_passed:
                fixes.append(f"  FIXED       {inv_id}: {cur['message']}")

    for inv_id in b_by_id:
        if inv_id not in c_by_id:
            removed.append(inv_id)

    if regressions:
        print(f"\nRegressions ({len(regressions)}):")
        for line in regressions:
            print(line)
    if fixes:
        print(f"\nFixes ({len(fixes)}):")
        for line in fixes:
            print(line)
    if added:
        print(f"\nNew invariants ({len(added)}): {', '.join(added)}")
    if removed:
        print(f"\nRemoved invariants ({len(removed)}): {', '.join(removed)}")

    if not regressions and not fixes and not added and not removed:
        print("\nDiff: no changes vs baseline.")
    else:
        print(
            f"\nDiff vs {baseline_path.name}: "
            f"{len(regressions)} regression(s), {len(fixes)} fix(es), "
            f"{len(added)} added, {len(removed)} removed"
        )

    return len(regressions)


if __name__ == "__main__":
    sys.exit(main())
