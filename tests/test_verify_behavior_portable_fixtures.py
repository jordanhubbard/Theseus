"""Portable public-API fixtures used by the real stdlib corpus."""
import base64
import ctypes
import dis
import importlib.util
import inspect
import sys
from types import SimpleNamespace

import pytest

from tools import verify_behavior as vb


def test_module_attribute_and_call_fixtures_use_the_declared_library():
    registry = vb.PatternRegistry(dis, {})
    assert registry._resolve_typed({'type': 'module_attr', 'value': 'opmap', 'key': 'LOAD_CONST'}) == dis.opmap['LOAD_CONST']
    registry = vb.PatternRegistry(importlib.util, {})
    spec = registry._resolve_typed({'type': 'module_call', 'value': 'find_spec', 'args': ['json']})
    assert spec.name == 'json'
    registry = vb.PatternRegistry(inspect, {})
    ok, message = registry._python_call_eq({'function': 'signature', 'args': [{'type': 'builtin', 'value': 'len'}],
        'method': '__str__', 'expected': '(obj, /)'})
    assert ok, message


@pytest.mark.parametrize('fixture', [
    {'type': 'module_call', 'value': '__import__("os")'},
    {'type': 'module_attr', 'value': 'opmap["LOAD_CONST"]'},
    {'type': 'builtin', 'value': 'eval'},
    {'type': 'builtin', 'value': '__import__'},
])
def test_fixture_references_are_structured_not_expressions(fixture):
    with pytest.raises(ValueError):
        vb.PatternRegistry(dis, {})._resolve_typed(fixture)


def test_valid_none_attribute_is_distinct_from_missing_attribute():
    registry = vb.PatternRegistry(SimpleNamespace(optional=None), {})
    # A legitimate None can be traversed via its documented type attribute.
    ok, message = registry._python_call_eq({'function': 'optional.__class__', 'args': [], 'expected': None})
    assert ok, message
    assert not registry._python_call_eq({'function': 'missing', 'expected': None})[0]


def test_dotted_membership_and_freebsd_platform_normalization(monkeypatch):
    registry = vb.PatternRegistry(SimpleNamespace(Event=SimpleNamespace(_fields=('time', 'priority'))), {})
    assert registry._python_set_contains({'attribute': 'Event._fields', 'must_contain': ['priority']})[0]
    assert not registry._python_set_contains({'attribute': 'Event.missing', 'must_contain': ['priority']})[0]
    monkeypatch.setattr(sys, 'platform', 'freebsd14')
    assert vb._build_skip_context('1.0')['platform'] == 'freebsd'


def test_c_version_function_receives_declared_integer_arguments():
    calls = []
    def version(selector):
        calls.append(selector)
        return b'OpenSSL fixture'
    registry = vb.PatternRegistry(SimpleNamespace(version=version), {})
    ok, message = registry._version_prefix({'function': 'version', 'args_int': [0],
        'expected_prefix_b64': base64.b64encode(b'OpenSSL ').decode()})
    assert ok, message
    assert calls == [0]
    assert version.argtypes == [ctypes.c_int]
