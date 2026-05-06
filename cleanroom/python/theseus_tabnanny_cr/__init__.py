"""Clean-room implementation of tabnanny-like indentation checking.

This module detects ambiguous indentation in Python source files —
specifically, mixing of tabs and spaces in a way that would be
interpreted differently under different tab-size assumptions.

No code from the original `tabnanny` module is used.
"""

import os
import tokenize


class NannyNag(Exception):
    """Raised when ambiguous indentation is found.

    Carries the offending line number, a human-readable message,
    and the offending source line.
    """

    def __init__(self, lineno, msg, line):
        self._lineno = lineno
        self._msg = msg
        self._line = line

    def get_lineno(self):
        return self._lineno

    def get_msg(self):
        return self._msg

    def get_line(self):
        return self._line


# ---------------------------------------------------------------------------
# Whitespace abstraction
# ---------------------------------------------------------------------------


class _Whitespace:
    """Represents a leading-whitespace prefix as a sequence of tabs/spaces.

    Provides indent-level computation for arbitrary tab sizes so we can
    detect when two indents agree at one tab size but disagree at another.
    """

    # Tab sizes we'll probe to compare two indents.
    _TAB_SIZES = (1, 2, 3, 4, 5, 6, 7, 8, 9)

    def __init__(self, ws):
        self.raw = ws
        n_tabs = 0
        n_spaces_after = 0
        for ch in ws:
            if ch == "\t":
                n_tabs += 1
                n_spaces_after = 0
            elif ch == " ":
                n_spaces_after += 1
            else:
                n_spaces_after += 1
        self.n_tabs = n_tabs
        self.n_spaces_after_last_tab = n_spaces_after

    def indent_level(self, tabsize):
        """Compute the visual indent column under a given tab size."""
        col = 0
        for ch in self.raw:
            if ch == "\t":
                col = (col // tabsize + 1) * tabsize
            else:
                col += 1
        return col

    def longest_run_of_spaces(self):
        best = 0
        run = 0
        for ch in self.raw:
            if ch == " ":
                run += 1
                if run > best:
                    best = run
            else:
                run = 0
        return best

    def indent_levels(self):
        """Return the set of indent levels for our probe tab sizes."""
        return {ts: self.indent_level(ts) for ts in self._TAB_SIZES}

    def less(self, other):
        """Return True iff self < other consistently across all probe tab sizes."""
        for ts in self._TAB_SIZES:
            if self.indent_level(ts) >= other.indent_level(ts):
                return False
        return True

    def not_less_or_equal(self, other):
        """Return witnesses showing self !<= other under different tab sizes."""
        a_levels = self.indent_levels()
        b_levels = other.indent_levels()
        witnesses = []
        for ts1 in self._TAB_SIZES:
            for ts2 in self._TAB_SIZES:
                if a_levels[ts1] <= b_levels[ts1] and a_levels[ts2] > b_levels[ts2]:
                    witnesses.append((ts1, ts2))
        return witnesses


def _format_witness(witnesses):
    if not witnesses:
        return "indent not greater e.g. at tab size 1"
    ts1, ts2 = witnesses[0]
    return "at tab size %d, %d but at tab size %d, %d" % (ts1, ts2, ts1, ts2)


def _leading_ws(line):
    i = 0
    for ch in line:
        if ch in (" ", "\t"):
            i += 1
        else:
            break
    return line[:i]


# ---------------------------------------------------------------------------
# Token processing
# ---------------------------------------------------------------------------


def tabnanny2_process_tokens(tokens=None):
    """Walk a token stream and raise NannyNag on ambiguous indentation.

    Mirrors tabnanny.process_tokens semantics in spirit: maintain a stack
    of indents seen so far; on INDENT verify the new indent is unambiguously
    deeper than the top of the stack; on DEDENT pop matched indents and
    verify the new indent is unambiguously shallower.

    If called with no arguments, runs a sanity self-test and returns True
    on success.

    Returns True on successful processing of the supplied token stream.
    """
    if tokens is None:
        # Self-test: build a tiny clean token stream from a string and process it.
        import io
        src = "def f():\n    return 1\n"
        toks = tokenize.generate_tokens(io.StringIO(src).readline)
        try:
            return tabnanny2_process_tokens(toks)
        except (NannyNag, tokenize.TokenError, IndentationError, SyntaxError):
            return False

    INDENT = tokenize.INDENT
    DEDENT = tokenize.DEDENT
    NEWLINE = tokenize.NEWLINE
    JUNK = (tokenize.COMMENT, tokenize.NL)

    indents = [_Whitespace("")]
    check_equal = 0

    for tok_type, tok_str, start, end, line in tokens:
        if tok_type == NEWLINE:
            check_equal = 1
        elif tok_type == INDENT:
            check_equal = 0
            this_indent = _Whitespace(tok_str)
            if not indents[-1].less(this_indent):
                witnesses = indents[-1].not_less_or_equal(this_indent)
                msg = "indent not greater e.g. " + _format_witness(witnesses)
                raise NannyNag(start[0], msg, line)
            indents.append(this_indent)
        elif tok_type == DEDENT:
            check_equal = 1
            if len(indents) > 1:
                del indents[-1]
        elif check_equal and tok_type not in JUNK:
            check_equal = 0
            this_indent = _Whitespace(_leading_ws(line))
            top = indents[-1]
            if this_indent.raw != top.raw:
                a_levels = this_indent.indent_levels()
                b_levels = top.indent_levels()
                bad = []
                for ts in _Whitespace._TAB_SIZES:
                    if a_levels[ts] != b_levels[ts]:
                        bad.append(ts)
                if bad:
                    msg = "indent not equal e.g. at tab size %d" % bad[0]
                    raise NannyNag(start[0], msg, line)

    return True


# ---------------------------------------------------------------------------
# Single-file check
# ---------------------------------------------------------------------------


def tabnanny2_check(file=None):
    """Check a single file (or directory) for ambiguous indentation.

    For a directory, recurse over .py files inside. For a file, tokenize it
    and feed the stream to tabnanny2_process_tokens.

    If called with no arguments, runs a sanity self-test and returns True.

    Returns True if the file (or all files in the directory) check out clean,
    False otherwise.
    """
    if file is None:
        # Self-test: feed a clean snippet of source through the pipeline.
        import io
        src = "def f():\n    return 1\n"
        try:
            toks = tokenize.generate_tokens(io.StringIO(src).readline)
            tabnanny2_process_tokens(toks)
        except (NannyNag, tokenize.TokenError, IndentationError, SyntaxError):
            return False
        return True

    if isinstance(file, str) and os.path.isdir(file):
        ok = True
        try:
            names = sorted(os.listdir(file))
        except OSError:
            return False
        for name in names:
            full = os.path.join(file, name)
            if os.path.isdir(full) and not os.path.islink(full):
                if not tabnanny2_check(full):
                    ok = False
            elif os.path.isfile(full) and name.endswith(".py"):
                if not tabnanny2_check(full):
                    ok = False
        return ok

    close_after = False
    f = None
    try:
        if hasattr(file, "read"):
            tokens = tokenize.generate_tokens(file.readline)
        else:
            try:
                f = tokenize.open(file)
            except (OSError, SyntaxError, UnicodeDecodeError):
                return False
            close_after = True
            tokens = tokenize.generate_tokens(f.readline)

        try:
            tabnanny2_process_tokens(tokens)
        except NannyNag:
            return False
        except (tokenize.TokenError, IndentationError, SyntaxError):
            return False
    finally:
        if close_after and f is not None:
            try:
                f.close()
            except OSError:
                pass

    return True


# ---------------------------------------------------------------------------
# Nag entry point
# ---------------------------------------------------------------------------


def tabnanny2_nannynag(*args):
    """Construct/raise a NannyNag-style report.

    Two call patterns are supported:

    * tabnanny2_nannynag()                — sanity self-test, returns True
    * tabnanny2_nannynag(lineno, msg, line) — return a NannyNag instance
      whose accessors match the supplied values
    """
    if not args:
        nag = NannyNag(1, "test", "    \tx")
        if nag.get_lineno() != 1:
            return False
        if nag.get_msg() != "test":
            return False
        if nag.get_line() != "    \tx":
            return False
        return True

    if len(args) == 3:
        lineno, msg, line = args
        return NannyNag(lineno, msg, line)

    raise TypeError(
        "tabnanny2_nannynag() takes 0 or 3 positional arguments (got %d)"
        % len(args)
    )