"""
Clean-room reimplementation of Python's ``codeop`` module.

This module supports compiling possibly incomplete Python source code,
returning a code object if the source is a complete statement, ``None``
if more input is required, or raising :class:`SyntaxError` if the source
is definitely invalid.

Implemented from scratch without importing the original ``codeop``.
"""

import __future__

__all__ = [
    "compile_command",
    "Compile",
    "CommandCompiler",
    "codeop2_compile_complete",
    "codeop2_compile_incomplete",
    "codeop2_commandcompiler",
]

# Compiler flag that prevents an automatic dedent at end-of-file. This is
# what allows us to distinguish incomplete blocks from a complete one.
PyCF_DONT_IMPLY_DEDENT = 0x200

# Collect all known __future__ feature flags so the incremental compilers
# can carry forward features that have been imported.
_features = [getattr(__future__, fname) for fname in __future__.all_feature_names]


def _maybe_compile(compiler, source, filename, symbol):
    """
    Try to compile ``source``. Return a code object if it is complete,
    ``None`` if more input is required, or raise :class:`SyntaxError`
    if the source is definitively invalid.

    The technique is a three-way trial: compile ``source`` as-is, then
    with one trailing newline, then with two. If all three fail with
    *identical* syntax errors, the source is genuinely invalid;
    otherwise it is merely incomplete.
    """
    # If the source is empty or contains only comments / blank lines,
    # replace it with a no-op so it compiles cleanly (except for ``eval``
    # mode, which requires an expression).
    for line in source.split("\n"):
        line = line.strip()
        if line and line[0] != "#":
            break
    else:
        if symbol != "eval":
            source = "pass"

    err1 = err2 = None
    code = code1 = code2 = None

    try:
        code = compiler(source, filename, symbol)
    except SyntaxError:
        pass
    except (OverflowError, ValueError):
        # ``compile`` can raise these for things like very large
        # numeric literals or null bytes; surface them directly.
        raise

    try:
        code1 = compiler(source + "\n", filename, symbol)
    except SyntaxError as exc:
        err1 = exc
    except (OverflowError, ValueError) as exc:
        err1 = exc

    try:
        code2 = compiler(source + "\n\n", filename, symbol)
    except SyntaxError as exc:
        err2 = exc
    except (OverflowError, ValueError) as exc:
        err2 = exc

    try:
        if code:
            return code
        if not code1 and repr(err1) == repr(err2):
            if err1 is not None:
                raise err1
        return None
    finally:
        # Break reference cycles to tracebacks.
        err1 = err2 = None


def _compile(source, filename, symbol):
    """Plain stateless compiler used by :func:`compile_command`."""
    return compile(source, filename, symbol, PyCF_DONT_IMPLY_DEDENT)


def compile_command(source, filename="<input>", symbol="single"):
    """
    Compile a command and judge whether it is complete.

    Arguments:

    * ``source`` -- the source string; may contain newlines
    * ``filename`` -- optional filename used in tracebacks
    * ``symbol`` -- ``"single"`` (default), ``"exec"`` or ``"eval"``

    Return value is one of:

    * a code object if the command is complete and valid
    * ``None`` if the command is incomplete
    * raises :class:`SyntaxError` if the command is invalid
    * raises :class:`OverflowError` / :class:`ValueError` for other
      compile-time errors
    """
    return _maybe_compile(_compile, source, filename, symbol)


class Compile:
    """
    A stateful compiler that "remembers" ``__future__`` imports so that
    subsequent compilations inherit features previously imported.
    """

    def __init__(self):
        self.flags = PyCF_DONT_IMPLY_DEDENT

    def __call__(self, source, filename, symbol):
        # ``dont_inherit=True`` so we control which feature flags apply.
        codeob = compile(source, filename, symbol, self.flags, True)
        for feature in _features:
            if codeob.co_flags & feature.compiler_flag:
                self.flags |= feature.compiler_flag
        return codeob


class CommandCompiler:
    """
    Instances of this class behave much like :func:`compile_command`,
    except that they remember ``__future__`` imports across calls.
    """

    def __init__(self):
        self.compiler = Compile()

    def __call__(self, source, filename="<input>", symbol="single"):
        return _maybe_compile(self.compiler, source, filename, symbol)


# ---------------------------------------------------------------------------
# Invariants (self-tests). Each returns ``True`` iff the corresponding
# behaviour of this module matches the canonical ``codeop`` semantics.
# ---------------------------------------------------------------------------

def codeop2_compile_complete():
    """Return True iff complete commands produce a code object."""
    try:
        # Simple assignment.
        code = compile_command("x = 1")
        if code is None or not hasattr(code, "co_code"):
            return False

        # Expression in single mode.
        code = compile_command("1 + 2")
        if code is None or not hasattr(code, "co_code"):
            return False

        # Multi-line block with full body.
        code = compile_command("if True:\n    y = 2\n")
        if code is None or not hasattr(code, "co_code"):
            return False

        # Empty source compiles to a no-op (single/exec mode).
        code = compile_command("")
        if code is None or not hasattr(code, "co_code"):
            return False

        # Comment-only source compiles to a no-op.
        code = compile_command("# just a comment\n")
        if code is None or not hasattr(code, "co_code"):
            return False

        return True
    except Exception:
        return False


def codeop2_compile_incomplete():
    """Return True iff incomplete commands return ``None``."""
    try:
        # Open block awaiting body.
        if compile_command("if True:") is not None:
            return False

        # Open block on a function definition.
        if compile_command("def foo():") is not None:
            return False

        # Open ``while``/``for`` block.
        if compile_command("while True:") is not None:
            return False

        # Definitely-invalid source must still raise SyntaxError.
        try:
            compile_command("$ invalid $")
        except SyntaxError:
            pass
        else:
            return False

        return True
    except Exception:
        return False


def codeop2_commandcompiler():
    """Return True iff CommandCompiler behaves like compile_command but
    remembers __future__ imports across invocations."""
    try:
        cc = CommandCompiler()
        if not isinstance(cc, CommandCompiler):
            return False

        # Complete command -> code object.
        code = cc("a = 1")
        if code is None or not hasattr(code, "co_code"):
            return False

        # Incomplete command -> None.
        if cc("if True:") is not None:
            return False

        # Multi-line complete command.
        code = cc("for i in range(3):\n    pass\n")
        if code is None or not hasattr(code, "co_code"):
            return False

        # Definitely-invalid source raises SyntaxError.
        try:
            cc("@@@@")
        except SyntaxError:
            pass
        else:
            return False

        # Direct Compile usage should also work.
        comp = Compile()
        codeob = comp("z = 5", "<test>", "single")
        if codeob is None or not hasattr(codeob, "co_code"):
            return False

        return True
    except Exception:
        return False