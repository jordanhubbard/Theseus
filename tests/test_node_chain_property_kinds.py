"""
Tests for two new ZSDL kinds added for fluent CLI/builder npm packages:
  - node_chain_eq:    arbitrary {method|get|call} chain off an initial value
  - node_property_eq: sugar for "construct/call, then read one property"

These cover packages that don't fit the single-call/two-step shapes of
node_module_call_eq, node_factory_call_eq, or node_constructor_call_eq —
e.g. commander (4-step builder chain), inquirer.Separator, ora, meow.

Tests use real npm packages that must be installed in the project's
node_modules (commander, mri, boxen).
"""
import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))
import verify_behavior as vb


def _have_node():
    return shutil.which("node") is not None


def _have_module(name: str, esm: bool = False) -> bool:
    if not _have_node():
        return False
    try:
        lib = vb.LibraryLoader().load({
            "backend": "cli",
            "command": "node",
            "module_name": name,
            "esm": esm,
        })
        return isinstance(lib, vb.CLIBackend)
    except vb.LibraryNotFoundError:
        return False


def _registry(module_name: str, esm: bool = False) -> vb.PatternRegistry:
    lib = vb.LibraryLoader().load({
        "backend": "cli",
        "command": "node",
        "module_name": module_name,
        "esm": esm,
    })
    return vb.PatternRegistry(lib, {})


# ---------------------------------------------------------------------------
# node_chain_eq — multi-step fluent chain
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _have_module("commander"), reason="commander not installed")
class TestNodeChainEqCommander:
    """commander: new Command().option(flag).parse(argv,{from:'user'}).opts() -> {...}"""

    def _run(self, spec):
        reg = _registry("commander")
        return reg.run({"kind": "node_chain_eq", "spec": spec})

    def test_long_flag_with_value(self):
        ok, msg = self._run({
            "entry": "constructor",
            "class": "Command",
            "entry_args": [],
            "chain": [
                {"method": "option", "args": ["--foo <val>"]},
                {"method": "parse", "args": [["--foo", "bar"], {"from": "user"}]},
                {"method": "opts", "args": []},
            ],
            "expected": {"foo": "bar"},
        })
        assert ok, msg

    def test_short_boolean_flag(self):
        ok, msg = self._run({
            "entry": "constructor",
            "class": "Command",
            "entry_args": [],
            "chain": [
                {"method": "option", "args": ["-v, --verbose"]},
                {"method": "parse", "args": [["-v"], {"from": "user"}]},
                {"method": "opts", "args": []},
            ],
            "expected": {"verbose": True},
        })
        assert ok, msg

    def test_negation_flag(self):
        ok, msg = self._run({
            "entry": "constructor",
            "class": "Command",
            "entry_args": [],
            "chain": [
                {"method": "option", "args": ["--no-color"]},
                {"method": "parse", "args": [["--no-color"], {"from": "user"}]},
                {"method": "opts", "args": []},
            ],
            "expected": {"color": False},
        })
        assert ok, msg

    def test_default_value_when_unset(self):
        ok, msg = self._run({
            "entry": "constructor",
            "class": "Command",
            "entry_args": [],
            "chain": [
                {"method": "option", "args": ["-p, --port <n>", "port", "8080"]},
                {"method": "parse", "args": [[], {"from": "user"}]},
                {"method": "opts", "args": []},
            ],
            "expected": {"port": "8080"},
        })
        assert ok, msg

    def test_chain_reports_actual_on_mismatch(self):
        ok, msg = self._run({
            "entry": "constructor",
            "class": "Command",
            "entry_args": [],
            "chain": [
                {"method": "option", "args": ["--foo <val>"]},
                {"method": "parse", "args": [["--foo", "bar"], {"from": "user"}]},
                {"method": "opts", "args": []},
            ],
            "expected": {"foo": "WRONG"},
        })
        assert not ok
        assert "expected" in msg
        assert "bar" in msg


# ---------------------------------------------------------------------------
# node_chain_eq — module-as-callable + chain (no constructor)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _have_module("mri"), reason="mri not installed")
class TestNodeChainEqModuleEntry:
    """mri exports a function; mri(argv) returns {_, ...flags}. No chain needed,
    but we exercise entry='module' with an empty chain to confirm parity with
    node_module_call_eq for the trivial case."""

    def test_module_entry_no_chain(self):
        reg = _registry("mri")
        ok, msg = reg.run({"kind": "node_chain_eq", "spec": {
            "entry": "module",
            "entry_args": [["--foo", "bar"]],
            "chain": [],
            "expected": {"_": [], "foo": "bar"},
        }})
        assert ok, msg


# ---------------------------------------------------------------------------
# node_property_eq — sugar form for "call/construct, then read property"
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _have_module("boxen", esm=True), reason="boxen not installed")
class TestNodePropertyEqBoxenLength:
    """boxen is a pure function; we don't really need property_eq for it, but
    string.length is a stable property to exercise the sugar form against an
    ESM module entry."""

    def test_boxen_output_length_via_property(self):
        reg = _registry("boxen", esm=True)
        ok, msg = reg.run({"kind": "node_property_eq", "spec": {
            "entry": "named",
            "function": "default",
            "entry_args": ["x", {"borderStyle": "single", "padding": 0, "margin": 0}],
            "property": "length",
            "expected": len("┌─┐\n│x│\n└─┘"),
        }})
        assert ok, msg


# ---------------------------------------------------------------------------
# node_property_eq — constructor + property read (the inquirer.Separator shape)
# Uses a minimal pure-JS class via a synthetic test that doesn't require
# inquirer to be installed: we use commander's Command instance and read a
# stable property (.commands is an array, default empty).
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _have_module("commander"), reason="commander not installed")
class TestNodePropertyEqConstructor:
    def test_fresh_command_has_empty_commands_array(self):
        reg = _registry("commander")
        ok, msg = reg.run({"kind": "node_property_eq", "spec": {
            "entry": "constructor",
            "class": "Command",
            "entry_args": [],
            "property": "commands",
            "expected": [],
        }})
        assert ok, msg


# ---------------------------------------------------------------------------
# Dotted member paths — for nested ESM defaults like inquirer.default.Separator
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _have_module("inquirer", esm=True), reason="inquirer not installed")
class TestDottedPathInEsmDefault:
    """inquirer's ESM module exposes Separator only via m.default.Separator,
    not at the top level. Confirms class/factory/function names accept dotted
    paths for traversal into nested objects."""

    def test_separator_default_type(self):
        reg = _registry("inquirer", esm=True)
        ok, msg = reg.run({"kind": "node_property_eq", "spec": {
            "entry": "constructor",
            "class": "default.Separator",
            "entry_args": [],
            "property": "type",
            "expected": "separator",
        }})
        assert ok, msg

    def test_separator_custom_line(self):
        reg = _registry("inquirer", esm=True)
        ok, msg = reg.run({"kind": "node_property_eq", "spec": {
            "entry": "constructor",
            "class": "default.Separator",
            "entry_args": ["---"],
            "property": "separator",
            "expected": "---",
        }})
        assert ok, msg


# ---------------------------------------------------------------------------
# node_sandbox_chain_eq — runs the chain in a tmp-dir cwd with seeded files
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _have_module("glob"), reason="glob not installed")
class TestNodeSandboxChainEqGlob:
    """The headline use case: file-globbing in an isolated sandbox seeded with
    known files. glob.globSync() returns unsorted matches; we always .sort()
    in the chain to make the comparison order-independent."""

    def test_simple_top_level_glob(self):
        reg = _registry("glob")
        ok, msg = reg.run({"kind": "node_sandbox_chain_eq", "spec": {
            "entry": "named",
            "function": "globSync",
            "entry_args": ["*.txt"],
            "chain": [{"method": "sort", "args": []}],
            "setup": [
                {"path": "a.txt", "content": ""},
                {"path": "b.txt", "content": ""},
                {"path": "ignore.md", "content": ""},
            ],
            "expected": ["a.txt", "b.txt"],
        }})
        assert ok, msg

    def test_recursive_glob(self):
        reg = _registry("glob")
        ok, msg = reg.run({"kind": "node_sandbox_chain_eq", "spec": {
            "entry": "named",
            "function": "globSync",
            "entry_args": ["**/*.txt"],
            "chain": [{"method": "sort", "args": []}],
            "setup": [
                {"path": "a.txt", "content": ""},
                {"path": "sub/b.txt", "content": ""},
                {"path": "sub/deep/c.txt", "content": ""},
            ],
            "expected": ["a.txt", "sub/b.txt", "sub/deep/c.txt"],
        }})
        assert ok, msg

    def test_no_match_returns_empty(self):
        reg = _registry("glob")
        ok, msg = reg.run({"kind": "node_sandbox_chain_eq", "spec": {
            "entry": "named",
            "function": "globSync",
            "entry_args": ["*.never_extension"],
            "chain": [],
            "setup": [{"path": "a.txt", "content": ""}],
            "expected": [],
        }})
        assert ok, msg

    def test_dir_setup_entry_creates_directory(self):
        reg = _registry("glob")
        # Empty directory setup; glob shouldn't pick it up with **/*.txt
        ok, msg = reg.run({"kind": "node_sandbox_chain_eq", "spec": {
            "entry": "named",
            "function": "globSync",
            "entry_args": ["**/*.txt"],
            "chain": [{"method": "sort", "args": []}],
            "setup": [
                {"path": "empty_subdir", "dir": True},
                {"path": "real.txt", "content": "hi"},
            ],
            "expected": ["real.txt"],
        }})
        assert ok, msg


@pytest.mark.skipif(not _have_module("fs-extra"), reason="fs-extra not installed")
class TestNodeSandboxChainEqFsExtra:
    """fs-extra exposes sync helpers — pathExistsSync, readJsonSync, etc. —
    that exercise the sandbox setup mechanism."""

    def test_path_exists_after_setup(self):
        reg = _registry("fs-extra")
        ok, msg = reg.run({"kind": "node_sandbox_chain_eq", "spec": {
            "entry": "named",
            "function": "pathExistsSync",
            "entry_args": ["target.txt"],
            "chain": [],
            "setup": [{"path": "target.txt", "content": "hello"}],
            "expected": True,
        }})
        assert ok, msg

    def test_path_exists_false_for_missing(self):
        reg = _registry("fs-extra")
        ok, msg = reg.run({"kind": "node_sandbox_chain_eq", "spec": {
            "entry": "named",
            "function": "pathExistsSync",
            "entry_args": ["missing.txt"],
            "chain": [],
            "setup": [],
            "expected": False,
        }})
        assert ok, msg

    def test_read_file_sync(self):
        reg = _registry("fs-extra")
        ok, msg = reg.run({"kind": "node_sandbox_chain_eq", "spec": {
            "entry": "named",
            "function": "readFileSync",
            "entry_args": ["data.txt", "utf-8"],
            "chain": [],
            "setup": [{"path": "data.txt", "content": "payload"}],
            "expected": "payload",
        }})
        assert ok, msg


# ---------------------------------------------------------------------------
# node_sandbox_chain_eq — input validation
# ---------------------------------------------------------------------------

class TestNodeSandboxChainEqValidation:
    def test_absolute_path_in_setup_rejected(self):
        class _FakeLib:
            command = "node"
            module_name = "anything"
            esm = False
        reg = vb.PatternRegistry(_FakeLib(), {})
        ok, msg = reg.run({"kind": "node_sandbox_chain_eq", "spec": {
            "entry": "module",
            "entry_args": [],
            "chain": [],
            "setup": [{"path": "/etc/passwd", "content": "evil"}],
            "expected": None,
        }})
        assert not ok
        assert "relative" in msg.lower() or "..'" in msg

    def test_dotdot_path_in_setup_rejected(self):
        class _FakeLib:
            command = "node"
            module_name = "anything"
            esm = False
        reg = vb.PatternRegistry(_FakeLib(), {})
        ok, msg = reg.run({"kind": "node_sandbox_chain_eq", "spec": {
            "entry": "module",
            "entry_args": [],
            "chain": [],
            "setup": [{"path": "../escape", "content": "x"}],
            "expected": None,
        }})
        assert not ok

    def test_missing_path_field_rejected(self):
        class _FakeLib:
            command = "node"
            module_name = "anything"
            esm = False
        reg = vb.PatternRegistry(_FakeLib(), {})
        ok, msg = reg.run({"kind": "node_sandbox_chain_eq", "spec": {
            "entry": "module",
            "entry_args": [],
            "chain": [],
            "setup": [{"content": "no-path-field"}],
            "expected": None,
        }})
        assert not ok
        assert "path" in msg


# ---------------------------------------------------------------------------
# Validator recognizes the new kinds
# ---------------------------------------------------------------------------

class TestValidatorAcceptsNewKinds:
    def test_known_kinds_includes_chain(self):
        sys.path.insert(0, str(REPO_ROOT / "tools"))
        import validate_zspec as vz
        assert "node_chain_eq" in vz.KNOWN_KINDS
        assert "node_property_eq" in vz.KNOWN_KINDS
        assert "node_sandbox_chain_eq" in vz.KNOWN_KINDS

    def test_pattern_registry_dispatches_chain(self):
        # Confirm the registry knows about the new kinds without needing node.
        # Use a no-op lib to avoid the LibraryLoader dependency.
        class _FakeLib:
            command = "node"
            module_name = "x"
            esm = False
        reg = vb.PatternRegistry(_FakeLib(), {})
        assert "node_chain_eq" in reg._handlers
        assert "node_property_eq" in reg._handlers
        assert "node_sandbox_chain_eq" in reg._handlers


# ---------------------------------------------------------------------------
# Bad input — chain step without method/get/call should produce a useful error
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# ctypes_chain_eq / ctypes_sandbox_chain_eq — handle/pointer threading for
# stateful C library APIs. Tested against libpcap (system shared library).
# ---------------------------------------------------------------------------

def _have_libpcap():
    try:
        import ctypes, ctypes.util
        return ctypes.util.find_library("pcap") is not None
    except Exception:
        return False


def _libpcap_registry():
    import ctypes, ctypes.util
    lib = ctypes.CDLL(ctypes.util.find_library("pcap"))
    return vb.PatternRegistry(lib, {})


@pytest.mark.skipif(not _have_libpcap(), reason="libpcap not installed")
class TestCtypesChainEqLibpcap:
    """Single-call chains against libpcap's pure helpers — the simplest use of
    ctypes_chain_eq (no captures, no sandbox)."""

    def test_lib_version_starts_with_libpcap(self):
        import base64
        reg = _libpcap_registry()
        ok, msg = reg.run({"kind": "ctypes_chain_eq", "spec": {
            "chain": [
                {"function": "pcap_lib_version", "restype": "c_char_p",
                 "args": [], "arg_types": []},
            ],
            "expected_prefix_b64": base64.b64encode(b"libpcap version").decode(),
        }})
        assert ok, msg

    def test_dlt_val_to_name_en10mb(self):
        import base64
        reg = _libpcap_registry()
        ok, msg = reg.run({"kind": "ctypes_chain_eq", "spec": {
            "chain": [
                {"function": "pcap_datalink_val_to_name", "restype": "c_char_p",
                 "args": [1], "arg_types": ["c_int"]},
            ],
            "expected_b64": base64.b64encode(b"EN10MB").decode(),
        }})
        assert ok, msg

    def test_dlt_name_to_val_string_arg_autoencodes(self):
        # Plain string args are auto-encoded to bytes when arg_type is c_char_p.
        reg = _libpcap_registry()
        ok, msg = reg.run({"kind": "ctypes_chain_eq", "spec": {
            "chain": [
                {"function": "pcap_datalink_name_to_val", "restype": "c_int",
                 "args": ["EN10MB"], "arg_types": ["c_char_p"]},
            ],
            "expected": 1,
        }})
        assert ok, msg


@pytest.mark.skipif(not _have_libpcap(), reason="libpcap not installed")
class TestCtypesSandboxChainEqLibpcap:
    """The headline use case: thread an opaque pcap_t* handle through
    open → query → close, using a synthesized .pcap blob in the sandbox."""

    @staticmethod
    def _pcap_header(magic, dlt, snaplen=65535):
        import struct, base64
        return base64.b64encode(
            struct.pack("<IHHiIII", magic, 2, 4, 0, 0, snaplen, dlt)
        ).decode()

    def test_open_offline_then_datalink_en10mb(self):
        reg = _libpcap_registry()
        ok, msg = reg.run({"kind": "ctypes_sandbox_chain_eq", "spec": {
            "setup": [{"path": "trace.pcap", "content_b64": self._pcap_header(0xa1b2c3d4, 1)}],
            "chain": [
                {"function": "pcap_open_offline", "restype": "c_void_p",
                 "args": [{"sandbox_path": "trace.pcap"}, {"errbuf": 256}],
                 "arg_types": ["c_char_p", "c_char_p"], "capture": "h"},
                {"function": "pcap_datalink", "restype": "c_int",
                 "args": [{"capture": "h"}], "arg_types": ["c_void_p"],
                 "compare": True},
                {"function": "pcap_close", "restype": "c_int",
                 "args": [{"capture": "h"}], "arg_types": ["c_void_p"]},
            ],
            "expected": 1,
        }})
        assert ok, msg

    def test_open_offline_snaplen(self):
        reg = _libpcap_registry()
        ok, msg = reg.run({"kind": "ctypes_sandbox_chain_eq", "spec": {
            "setup": [{"path": "trace.pcap", "content_b64": self._pcap_header(0xa1b2c3d4, 113, snaplen=1500)}],
            "chain": [
                {"function": "pcap_open_offline", "restype": "c_void_p",
                 "args": [{"sandbox_path": "trace.pcap"}, {"errbuf": 256}],
                 "arg_types": ["c_char_p", "c_char_p"], "capture": "h"},
                {"function": "pcap_snapshot", "restype": "c_int",
                 "args": [{"capture": "h"}], "arg_types": ["c_void_p"],
                 "compare": True},
                {"function": "pcap_close", "restype": "c_int",
                 "args": [{"capture": "h"}], "arg_types": ["c_void_p"]},
            ],
            "expected": 1500,
        }})
        assert ok, msg

    def test_bad_magic_returns_null(self):
        reg = _libpcap_registry()
        ok, msg = reg.run({"kind": "ctypes_sandbox_chain_eq", "spec": {
            "setup": [{"path": "bad.pcap", "content_b64": self._pcap_header(0xdeadbeef, 1)}],
            "chain": [
                {"function": "pcap_open_offline", "restype": "c_void_p",
                 "args": [{"sandbox_path": "bad.pcap"}, {"errbuf": 256}],
                 "arg_types": ["c_char_p", "c_char_p"], "compare": True},
            ],
            "expected": 0,  # NULL pointer
        }})
        assert ok, msg


class TestCtypesChainEqValidation:
    """Schema/runtime validation — exercised without needing a real library."""

    def test_capture_reference_undefined_returns_error(self):
        # Use libpcap if available, otherwise skip — we just need any ctypes lib.
        if not _have_libpcap():
            pytest.skip("need a ctypes library to load")
        reg = _libpcap_registry()
        ok, msg = reg.run({"kind": "ctypes_chain_eq", "spec": {
            "chain": [
                {"function": "pcap_datalink_val_to_name", "restype": "c_char_p",
                 "args": [{"capture": "never_set"}], "arg_types": ["c_int"]},
            ],
            "expected_b64": "",
        }})
        assert not ok
        assert "never_set" in msg or "undefined capture" in msg

    def test_unknown_restype_token_rejected(self):
        if not _have_libpcap():
            pytest.skip("need a ctypes library to load")
        reg = _libpcap_registry()
        ok, msg = reg.run({"kind": "ctypes_chain_eq", "spec": {
            "chain": [
                {"function": "pcap_lib_version", "restype": "c_bogus", "args": [], "arg_types": []},
            ],
            "expected": 0,
        }})
        assert not ok
        assert "c_bogus" in msg

    def test_sandbox_path_outside_rejected(self):
        if not _have_libpcap():
            pytest.skip("need a ctypes library to load")
        reg = _libpcap_registry()
        ok, msg = reg.run({"kind": "ctypes_sandbox_chain_eq", "spec": {
            "setup": [{"path": "../escape", "content": "evil"}],
            "chain": [],
            "expected": 0,
        }})
        assert not ok


class TestUndefinedReturnMapping:
    """JS chains that legitimately return undefined (e.g. find-up miss,
    mkdirp on already-existing path) must produce JSON null so the comparison
    against YAML ~ works, instead of choking process.stdout.write."""

    @pytest.mark.skipif(not _have_module("commander"), reason="commander not installed")
    def test_undefined_property_compares_as_null(self):
        # Reading a non-existent property returns JS undefined.
        reg = _registry("commander")
        ok, msg = reg.run({"kind": "node_property_eq", "spec": {
            "entry": "constructor",
            "class": "Command",
            "entry_args": [],
            "property": "definitelyNotARealField",
            "expected": None,  # YAML ~ → Python None → JSON null
        }})
        assert ok, msg


class TestNodeChainEqMalformed:
    def test_unknown_step_shape_returns_false(self):
        class _FakeLib:
            command = "node"
            module_name = "anything"
            esm = False
        reg = vb.PatternRegistry(_FakeLib(), {})
        ok, msg = reg.run({"kind": "node_chain_eq", "spec": {
            "entry": "module",
            "entry_args": [],
            "chain": [{"weird_key": "x"}],
            "expected": None,
        }})
        assert not ok
        assert "method/get/call" in msg

    def test_unknown_entry_returns_false(self):
        class _FakeLib:
            command = "node"
            module_name = "anything"
            esm = False
        reg = vb.PatternRegistry(_FakeLib(), {})
        ok, msg = reg.run({"kind": "node_chain_eq", "spec": {
            "entry": "bogus",
            "entry_args": [],
            "chain": [],
            "expected": None,
        }})
        assert not ok
        assert "bogus" in msg
