"""
Tests for the python_module backend with the protobuf (google.protobuf) behavioral spec.

Organized as:
  - TestProtobufLoader: loading the protobuf spec and module
  - TestProtobufVersion: version category invariants
  - TestProtobufFieldDescriptor: field_descriptor category invariants (type/label constants)
  - TestProtobufClasses: classes category invariants (Message, FieldDescriptor, descriptor_pool)
  - TestProtobufAll: all 13 protobuf invariants pass
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import verify_behavior as vb

PROTOBUF_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "protobuf.zspec.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def protobuf_spec():
    return vb.SpecLoader().load(PROTOBUF_SPEC_PATH)


@pytest.fixture(scope="module")
def protobuf_mod(protobuf_spec):
    return vb.LibraryLoader().load(protobuf_spec["library"])


@pytest.fixture(scope="module")
def constants_map(protobuf_spec):
    return vb.InvariantRunner().build_constants_map(protobuf_spec["constants"])


@pytest.fixture(scope="module")
def registry(protobuf_mod, constants_map):
    return vb.PatternRegistry(protobuf_mod, constants_map)


# ---------------------------------------------------------------------------
# TestProtobufLoader — spec loading and module import
# ---------------------------------------------------------------------------

class TestProtobufLoader:
    def test_loads_protobuf_spec(self, protobuf_spec):
        assert isinstance(protobuf_spec, dict)

    def test_all_required_sections_present(self, protobuf_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in protobuf_spec, f"Missing section: {section}"

    def test_backend_is_python_module(self, protobuf_spec):
        assert protobuf_spec["library"]["backend"] == "python_module"

    def test_module_name_is_google_protobuf(self, protobuf_spec):
        assert protobuf_spec["library"]["module_name"] == "google.protobuf"

    def test_loads_protobuf_module(self, protobuf_mod):
        import google.protobuf
        assert protobuf_mod is google.protobuf

    def test_all_invariant_kinds_known(self, protobuf_spec):
        for inv in protobuf_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_all_invariant_ids_unique(self, protobuf_spec):
        ids = [inv["id"] for inv in protobuf_spec["invariants"]]
        assert len(ids) == len(set(ids))

    def test_invariant_count_is_thirteen(self, protobuf_spec):
        assert len(protobuf_spec["invariants"]) == 13

    def test_submodules_loaded(self, protobuf_mod):
        """Submodules must be accessible as attributes after library load."""
        import google.protobuf.descriptor
        import google.protobuf.message
        import google.protobuf.descriptor_pool
        assert hasattr(protobuf_mod, "descriptor")
        assert hasattr(protobuf_mod, "message")
        assert hasattr(protobuf_mod, "descriptor_pool")


# ---------------------------------------------------------------------------
# TestProtobufVersion
# ---------------------------------------------------------------------------

class TestProtobufVersion:
    def test_version_contains_dot(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "__version__.__contains__",
                "args": ["."],
                "expected": True,
            },
        })
        assert ok, msg

    def test_version_is_string(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "__version__.__class__.__name__.__eq__",
                "args": ["str"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_version_nonempty(self, protobuf_mod):
        assert isinstance(protobuf_mod.__version__, str)
        assert len(protobuf_mod.__version__) > 0


# ---------------------------------------------------------------------------
# TestProtobufFieldDescriptor
# ---------------------------------------------------------------------------

class TestProtobufFieldDescriptor:
    def test_TYPE_INT32_eq_5(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "descriptor.FieldDescriptor.TYPE_INT32.__eq__",
                "args": [5],
                "expected": True,
            },
        })
        assert ok, msg

    def test_TYPE_STRING_eq_9(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "descriptor.FieldDescriptor.TYPE_STRING.__eq__",
                "args": [9],
                "expected": True,
            },
        })
        assert ok, msg

    def test_TYPE_BOOL_eq_8(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "descriptor.FieldDescriptor.TYPE_BOOL.__eq__",
                "args": [8],
                "expected": True,
            },
        })
        assert ok, msg

    def test_TYPE_FLOAT_eq_2(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "descriptor.FieldDescriptor.TYPE_FLOAT.__eq__",
                "args": [2],
                "expected": True,
            },
        })
        assert ok, msg

    def test_TYPE_BYTES_eq_12(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "descriptor.FieldDescriptor.TYPE_BYTES.__eq__",
                "args": [12],
                "expected": True,
            },
        })
        assert ok, msg

    def test_LABEL_OPTIONAL_eq_1(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "descriptor.FieldDescriptor.LABEL_OPTIONAL.__eq__",
                "args": [1],
                "expected": True,
            },
        })
        assert ok, msg

    def test_LABEL_REQUIRED_eq_2(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "descriptor.FieldDescriptor.LABEL_REQUIRED.__eq__",
                "args": [2],
                "expected": True,
            },
        })
        assert ok, msg

    def test_LABEL_REPEATED_eq_3(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "descriptor.FieldDescriptor.LABEL_REPEATED.__eq__",
                "args": [3],
                "expected": True,
            },
        })
        assert ok, msg

    def test_type_constants_are_ints(self, protobuf_mod):
        """All TYPE_* constants must be plain ints."""
        fd = protobuf_mod.descriptor.FieldDescriptor
        for name in ("TYPE_INT32", "TYPE_STRING", "TYPE_BOOL", "TYPE_FLOAT", "TYPE_BYTES"):
            assert isinstance(getattr(fd, name), int), f"{name} is not an int"

    def test_label_constants_are_ints(self, protobuf_mod):
        """All LABEL_* constants must be plain ints."""
        fd = protobuf_mod.descriptor.FieldDescriptor
        for name in ("LABEL_OPTIONAL", "LABEL_REQUIRED", "LABEL_REPEATED"):
            assert isinstance(getattr(fd, name), int), f"{name} is not an int"

    def test_label_constants_are_distinct(self, protobuf_mod):
        """LABEL_OPTIONAL, LABEL_REQUIRED, LABEL_REPEATED must all be different."""
        fd = protobuf_mod.descriptor.FieldDescriptor
        values = [fd.LABEL_OPTIONAL, fd.LABEL_REQUIRED, fd.LABEL_REPEATED]
        assert len(set(values)) == 3


# ---------------------------------------------------------------------------
# TestProtobufClasses
# ---------------------------------------------------------------------------

class TestProtobufClasses:
    def test_Message_class_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "message.Message.__name__.__eq__",
                "args": ["Message"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_FieldDescriptor_class_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "descriptor.FieldDescriptor.__name__.__eq__",
                "args": ["FieldDescriptor"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_descriptor_pool_module_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "descriptor_pool.__name__.__eq__",
                "args": ["google.protobuf.descriptor_pool"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_Message_is_class(self, protobuf_mod):
        """message.Message must be a class."""
        assert isinstance(protobuf_mod.message.Message, type)

    def test_FieldDescriptor_is_class(self, protobuf_mod):
        """descriptor.FieldDescriptor must be a class."""
        assert isinstance(protobuf_mod.descriptor.FieldDescriptor, type)


# ---------------------------------------------------------------------------
# TestProtobufAll — all 13 protobuf invariants must pass
# ---------------------------------------------------------------------------

class TestProtobufAll:
    def test_all_pass(self, protobuf_spec, protobuf_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(protobuf_spec, protobuf_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, f"Failed invariants: {[r.inv_id for r in failed]}"

    def test_invariant_count(self, protobuf_spec, protobuf_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(protobuf_spec, protobuf_mod)
        assert len(results) == 13

    def test_filter_by_category_version(self, protobuf_spec, protobuf_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(protobuf_spec, protobuf_mod, filter_category="version")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_by_category_field_descriptor(self, protobuf_spec, protobuf_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(protobuf_spec, protobuf_mod, filter_category="field_descriptor")
        assert len(results) == 8
        assert all(r.passed for r in results)

    def test_filter_by_category_classes(self, protobuf_spec, protobuf_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(protobuf_spec, protobuf_mod, filter_category="classes")
        assert len(results) == 3
        assert all(r.passed for r in results)
