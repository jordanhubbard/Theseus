"""
Tests for the python_module backend with the dns (dnspython) behavioral spec.

Organized as:
  - TestDnsLoader: loading the dns spec and module
  - TestDnsVersion: version category invariants (__version__ format)
  - TestDnsName: name category invariants (dns.name submodule)
  - TestDnsRdatatype: rdatatype category invariants (DNS record type constants)
  - TestDnsRdataclass: rdataclass category invariants (DNS class constants)
  - TestDnsRcode: rcode category invariants (DNS response code constants)
  - TestDnsAll: all 19 dns invariants pass
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import verify_behavior as vb

DNS_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "dns.zspec.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def dns_spec():
    return vb.SpecLoader().load(DNS_SPEC_PATH)


@pytest.fixture(scope="module")
def dns_mod(dns_spec):
    return vb.LibraryLoader().load(dns_spec["library"])


@pytest.fixture(scope="module")
def constants_map(dns_spec):
    return vb.InvariantRunner().build_constants_map(dns_spec["constants"])


@pytest.fixture(scope="module")
def registry(dns_mod, constants_map):
    return vb.PatternRegistry(dns_mod, constants_map)


# ---------------------------------------------------------------------------
# TestDnsLoader — spec loading and module import
# ---------------------------------------------------------------------------

class TestDnsLoader:
    def test_loads_dns_spec(self, dns_spec):
        assert isinstance(dns_spec, dict)

    def test_all_required_sections_present(self, dns_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in dns_spec, f"Missing section: {section}"

    def test_backend_is_python_module(self, dns_spec):
        assert dns_spec["library"]["backend"] == "python_module"

    def test_module_name_is_dns(self, dns_spec):
        assert dns_spec["library"]["module_name"] == "dns"

    def test_loads_dns_module(self, dns_mod):
        import dns
        assert dns_mod is dns

    def test_all_invariant_kinds_known(self, dns_spec):
        for inv in dns_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_all_invariant_ids_unique(self, dns_spec):
        ids = [inv["id"] for inv in dns_spec["invariants"]]
        assert len(ids) == len(set(ids))

    def test_invariant_count_is_nineteen(self, dns_spec):
        assert len(dns_spec["invariants"]) == 19

    def test_submodules_loaded(self, dns_mod):
        """Submodules must be accessible as attributes after library load."""
        import dns.name
        import dns.rdatatype
        import dns.rdataclass
        import dns.rcode
        assert hasattr(dns_mod, "name")
        assert hasattr(dns_mod, "rdatatype")
        assert hasattr(dns_mod, "rdataclass")
        assert hasattr(dns_mod, "rcode")


# ---------------------------------------------------------------------------
# TestDnsVersion
# ---------------------------------------------------------------------------

class TestDnsVersion:
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

    def test_version_nonempty(self, dns_mod):
        assert isinstance(dns_mod.__version__, str)
        assert len(dns_mod.__version__) > 0


# ---------------------------------------------------------------------------
# TestDnsName
# ---------------------------------------------------------------------------

class TestDnsName:
    def test_absolute_name_is_absolute(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "name.from_text",
                "args": ["www.example.com."],
                "method": "is_absolute",
                "expected": True,
            },
        })
        assert ok, msg

    def test_relative_name_is_not_absolute(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "name.from_text",
                "args": ["www.example.com"],
                "kwargs": {"origin": None},
                "method": "is_absolute",
                "expected": False,
            },
        })
        assert ok, msg

    def test_root_is_absolute(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "name.root.is_absolute",
                "args": [],
                "expected": True,
            },
        })
        assert ok, msg

    def test_root_str(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "name.root.__str__",
                "args": [],
                "expected": ".",
            },
        })
        assert ok, msg

    def test_absolute_name_str(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "name.from_text",
                "args": ["www.example.com."],
                "method": "__str__",
                "expected": "www.example.com.",
            },
        })
        assert ok, msg

    def test_name_type(self, dns_mod):
        """from_text returns a dns.name.Name instance."""
        import dns.name
        n = dns.name.from_text("www.example.com.")
        assert type(n).__name__ == "Name"


# ---------------------------------------------------------------------------
# TestDnsRdatatype
# ---------------------------------------------------------------------------

class TestDnsRdatatype:
    def test_A_eq_1(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "rdatatype.A.__eq__",
                "args": [1],
                "expected": True,
            },
        })
        assert ok, msg

    def test_AAAA_eq_28(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "rdatatype.AAAA.__eq__",
                "args": [28],
                "expected": True,
            },
        })
        assert ok, msg

    def test_MX_eq_15(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "rdatatype.MX.__eq__",
                "args": [15],
                "expected": True,
            },
        })
        assert ok, msg

    def test_NS_eq_2(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "rdatatype.NS.__eq__",
                "args": [2],
                "expected": True,
            },
        })
        assert ok, msg

    def test_TXT_eq_16(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "rdatatype.TXT.__eq__",
                "args": [16],
                "expected": True,
            },
        })
        assert ok, msg

    def test_to_text_A(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "rdatatype.to_text",
                "args": [1],
                "expected": "A",
            },
        })
        assert ok, msg

    def test_from_text_AAAA(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "rdatatype.from_text",
                "args": ["AAAA"],
                "expected": 28,
            },
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# TestDnsRdataclass
# ---------------------------------------------------------------------------

class TestDnsRdataclass:
    def test_IN_eq_1(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "rdataclass.IN.__eq__",
                "args": [1],
                "expected": True,
            },
        })
        assert ok, msg

    def test_to_text_IN(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "rdataclass.to_text",
                "args": [1],
                "expected": "IN",
            },
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# TestDnsRcode
# ---------------------------------------------------------------------------

class TestDnsRcode:
    def test_NOERROR_eq_0(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "rcode.NOERROR.__eq__",
                "args": [0],
                "expected": True,
            },
        })
        assert ok, msg

    def test_NXDOMAIN_eq_3(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "rcode.NXDOMAIN.__eq__",
                "args": [3],
                "expected": True,
            },
        })
        assert ok, msg

    def test_to_text_NOERROR(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "rcode.to_text",
                "args": [0],
                "expected": "NOERROR",
            },
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# TestDnsAll — all 19 spec invariants must pass
# ---------------------------------------------------------------------------

class TestDnsAll:
    def test_all_pass(self, dns_spec, dns_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(dns_spec, dns_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, f"Failed invariants: {[r.inv_id for r in failed]}"

    def test_invariant_count(self, dns_spec, dns_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(dns_spec, dns_mod)
        assert len(results) == 19

    def test_filter_by_category_version(self, dns_spec, dns_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(dns_spec, dns_mod, filter_category="version")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_by_category_name(self, dns_spec, dns_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(dns_spec, dns_mod, filter_category="name")
        assert len(results) == 5
        assert all(r.passed for r in results)

    def test_filter_by_category_rdatatype(self, dns_spec, dns_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(dns_spec, dns_mod, filter_category="rdatatype")
        assert len(results) == 7
        assert all(r.passed for r in results)

    def test_filter_by_category_rdataclass(self, dns_spec, dns_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(dns_spec, dns_mod, filter_category="rdataclass")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_by_category_rcode(self, dns_spec, dns_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(dns_spec, dns_mod, filter_category="rcode")
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_no_invariants_skipped(self, dns_spec, dns_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(dns_spec, dns_mod)
        skipped = [r for r in results if r.skip_reason is not None]
        assert not skipped, f"Unexpectedly skipped: {[r.inv_id for r in skipped]}"
