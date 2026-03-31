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
import json
import struct as _struct
import sys
from dataclasses import dataclass
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
                return importlib.import_module(module_name)
            except ImportError as exc:
                raise LibraryNotFoundError(
                    f"Cannot import Python module {module_name!r}: {exc}"
                ) from exc
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
        """Bind argtypes and restypes for the zlib API functions used by invariants."""
        # compress(dest, &destLen, source, sourceLen) -> int
        lib.compress.argtypes = [
            ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_ulong),
            ctypes.c_char_p,
            ctypes.c_ulong,
        ]
        lib.compress.restype = ctypes.c_int

        # compress2(dest, &destLen, source, sourceLen, level) -> int
        lib.compress2.argtypes = [
            ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_ulong),
            ctypes.c_char_p,
            ctypes.c_ulong,
            ctypes.c_int,
        ]
        lib.compress2.restype = ctypes.c_int

        # uncompress(dest, &destLen, source, sourceLen) -> int
        lib.uncompress.argtypes = [
            ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_ulong),
            ctypes.c_char_p,
            ctypes.c_ulong,
        ]
        lib.uncompress.restype = ctypes.c_int

        # compressBound(sourceLen) -> ulong
        lib.compressBound.argtypes = [ctypes.c_ulong]
        lib.compressBound.restype = ctypes.c_ulong

        # crc32(crc, buf, len) -> ulong
        lib.crc32.argtypes = [ctypes.c_ulong, ctypes.c_char_p, ctypes.c_uint]
        lib.crc32.restype = ctypes.c_ulong

        # adler32(adler, buf, len) -> ulong
        lib.adler32.argtypes = [ctypes.c_ulong, ctypes.c_char_p, ctypes.c_uint]
        lib.adler32.restype = ctypes.c_ulong

        # zlibVersion() -> const char*
        lib.zlibVersion.argtypes = []
        lib.zlibVersion.restype = ctypes.c_char_p

        # zError(err) -> const char*
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
    # Python-module kinds
    "hash_known_vector",
    "hash_incremental",
    "hash_object_attr",
    "python_set_contains",
    "hash_digest_consistency",
    "hash_copy_independence",
    "hash_api_equivalence",
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
            # Python-module kinds
            "hash_known_vector":      self._hash_known_vector,
            "hash_incremental":       self._hash_incremental,
            "hash_object_attr":       self._hash_object_attr,
            "python_set_contains":    self._python_set_contains,
            "hash_digest_consistency":self._hash_digest_consistency,
            "hash_copy_independence": self._hash_copy_independence,
            "hash_api_equivalence":   self._hash_api_equivalence,
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
        result = getattr(self._lib, fn_name)()
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
    # Verifies that compressBound(n) >= actual compressed size for a real input.
    def _call_ge(self, spec: dict) -> tuple[bool, str]:
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


# ---------------------------------------------------------------------------
# Invariant runner
# ---------------------------------------------------------------------------

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
                    # Try to get a version string from the library (ctypes backend only)
                    ver_fn = getattr(lib, "zlibVersion", None)
                    ver_bytes = ver_fn() if callable(ver_fn) else b""
                    lib_version = (ver_bytes or b"").decode("ascii", errors="replace")
                    should_skip = bool(
                        eval(skip_expr, {"__builtins__": {}},  # noqa: S307
                             {"lib_version": lib_version})
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

    runner = InvariantRunner()
    results = runner.run_all(spec, lib, filter_category=args.filter_category)

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

    if args.json_out:
        out = [
            {
                "id": r.inv_id,
                "passed": r.passed,
                "message": r.message,
                "skip_reason": r.skip_reason,
            }
            for r in results
        ]
        args.json_out.write_text(json.dumps(out, indent=2), encoding="utf-8")

    return 1 if failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
