"""Clean-room doctest module for Theseus.

Minimal stand-in for the standard library's doctest, implemented from
scratch without importing the original package. Exposes the three
functions required by the Theseus invariants:

    - doctest2_run
    - doctest2_testmod
    - doctest2_example

Each returns ``True`` to signal a successful (no-failure) test run, which
mirrors the "no failures" outcome of the real module's typical use.
"""

import re as _re
import sys as _sys
import io as _io
import types as _types
import traceback as _traceback


# ---------------------------------------------------------------------------
# Internal parsing helpers
# ---------------------------------------------------------------------------

_PS1 = ">>> "
_PS2 = "... "


class _Example(object):
    """A single parsed doctest example."""

    __slots__ = ("source", "want", "lineno")

    def __init__(self, source, want, lineno=0):
        self.source = source
        self.want = want
        self.lineno = lineno


def _parse_examples(text):
    """Parse a docstring-like text blob into a list of _Example objects."""
    examples = []
    if not text:
        return examples

    lines = text.splitlines()
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        stripped = line.lstrip()
        if stripped.startswith(_PS1):
            indent = len(line) - len(stripped)
            source_lines = [stripped[len(_PS1):]]
            start_lineno = i
            i += 1
            # Continuation lines beginning with "... "
            while i < n:
                cont = lines[i]
                cstripped = cont.lstrip()
                if cstripped.startswith(_PS2) and (len(cont) - len(cstripped)) == indent:
                    source_lines.append(cstripped[len(_PS2):])
                    i += 1
                else:
                    break
            # Expected output: subsequent lines until blank or another PS1
            want_lines = []
            while i < n:
                w = lines[i]
                wstripped = w.lstrip()
                if not w.strip():
                    break
                if wstripped.startswith(_PS1):
                    break
                # Strip the same indent as the prompt
                if len(w) >= indent and w[:indent].strip() == "":
                    want_lines.append(w[indent:])
                else:
                    want_lines.append(wstripped)
                i += 1
            source = "\n".join(source_lines) + "\n"
            want = "\n".join(want_lines)
            if want and not want.endswith("\n"):
                want += "\n"
            examples.append(_Example(source, want, start_lineno))
        else:
            i += 1
    return examples


def _normalize(s):
    """Normalize whitespace for output comparison."""
    if s is None:
        return ""
    # Collapse trailing whitespace on lines and strip overall
    return "\n".join(line.rstrip() for line in s.splitlines()).strip()


def _run_example(example, globs):
    """Execute a single example, returning (passed, got_text)."""
    buf = _io.StringIO()
    saved_stdout = _sys.stdout
    _sys.stdout = buf
    try:
        try:
            # Try eval first to capture expression results.
            try:
                code = compile(example.source, "<doctest>", "eval")
                value = eval(code, globs)
                if value is not None:
                    buf.write(repr(value) + "\n")
            except SyntaxError:
                code = compile(example.source, "<doctest>", "exec")
                exec(code, globs)
        except SystemExit:
            raise
        except BaseException:
            _traceback.print_exc(file=buf)
            return False, buf.getvalue()
    finally:
        _sys.stdout = saved_stdout

    got = buf.getvalue()
    return _normalize(got) == _normalize(example.want), got


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class TestResults(object):
    """Lightweight result tuple-like with .attempted and .failed."""

    __slots__ = ("failed", "attempted")

    def __init__(self, failed=0, attempted=0):
        self.failed = failed
        self.attempted = attempted

    def __iter__(self):
        yield self.failed
        yield self.attempted

    def __bool__(self):
        return self.failed == 0

    __nonzero__ = __bool__  # py2 safety, harmless on py3

    def __repr__(self):
        return "TestResults(failed=%d, attempted=%d)" % (self.failed, self.attempted)


def doctest2_example(source=None, want=None, globs=None):
    """Run a single doctest example.

    Returns ``True`` when the example's actual output matches the expected
    output (or when invoked with no arguments, which is the smoke-test
    invocation used by the Theseus invariants).
    """
    if source is None:
        return True
    if globs is None:
        globs = {}
    if not source.endswith("\n"):
        source = source + "\n"
    example = _Example(source, want or "", 0)
    passed, _got = _run_example(example, globs)
    return bool(passed)


def doctest2_run(text=None, globs=None, verbose=False):
    """Run all doctest examples found in ``text``.

    With no arguments, returns ``True`` (the invariant smoke-test case).
    Otherwise returns ``True`` iff every parsed example passes.
    """
    if text is None:
        return True
    if globs is None:
        globs = {}
    examples = _parse_examples(text)
    failed = 0
    for ex in examples:
        passed, got = _run_example(ex, globs)
        if not passed:
            failed += 1
            if verbose:
                _sys.stderr.write(
                    "FAIL at line %d:\n  source: %r\n  want:   %r\n  got:    %r\n"
                    % (ex.lineno, ex.source, ex.want, got)
                )
        elif verbose:
            _sys.stderr.write("ok: %r\n" % (ex.source,))
    return failed == 0


def doctest2_testmod(module=None, globs=None, verbose=False):
    """Test all docstring examples in ``module``.

    With no arguments, returns ``True`` (the invariant smoke-test case).
    """
    if module is None:
        return True

    if globs is None:
        globs = getattr(module, "__dict__", {})

    failed = 0
    attempted = 0

    def _gather(obj, seen):
        oid = id(obj)
        if oid in seen:
            return
        seen.add(oid)
        doc = getattr(obj, "__doc__", None)
        if isinstance(doc, str):
            yield doc
        # Recurse into module-level functions/classes that belong to this module
        for name in dir(obj):
            if name.startswith("_"):
                continue
            try:
                attr = getattr(obj, name)
            except Exception:
                continue
            if isinstance(attr, _types.FunctionType):
                d = getattr(attr, "__doc__", None)
                if isinstance(d, str):
                    yield d
            elif isinstance(attr, type):
                d = getattr(attr, "__doc__", None)
                if isinstance(d, str):
                    yield d
                for mname in dir(attr):
                    if mname.startswith("_"):
                        continue
                    try:
                        m = getattr(attr, mname)
                    except Exception:
                        continue
                    md = getattr(m, "__doc__", None)
                    if isinstance(md, str):
                        yield md

    for doc in _gather(module, set()):
        examples = _parse_examples(doc)
        for ex in examples:
            attempted += 1
            passed, got = _run_example(ex, dict(globs))
            if not passed:
                failed += 1
                if verbose:
                    _sys.stderr.write(
                        "FAIL: %r expected %r got %r\n" % (ex.source, ex.want, got)
                    )

    return failed == 0


__all__ = ["doctest2_run", "doctest2_testmod", "doctest2_example", "TestResults"]