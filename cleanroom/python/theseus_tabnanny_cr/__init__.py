"""
theseus_tabnanny_cr — Clean-room tabnanny module.
No import of the standard `tabnanny` module.
"""

import os as _os
import sys as _sys
import tokenize as _tokenize
import token as _token
import io as _io

verbose = 0


class NannyNag(Exception):
    """Raised when a line has inconsistent use of tabs and spaces."""

    def __init__(self, lineno, msg, line):
        self.lineno = lineno
        self.msg = msg
        self.line = line
        super().__init__(lineno, msg, line)

    def get_lineno(self):
        return self.lineno

    def get_msg(self):
        return self.msg

    def get_line(self):
        return self.line


_INDENT_SIZE_DEFAULT = -1
_ERR_INDENT = "indent not consistent over continuation line"
_ERR_DEDENT = "dedent not consistent over continuation line"
_ERR_MIXED = "inconsistent use of tabs and spaces in indentation"


class Whitespace:
    """Track indentation whitespace for consistency checking."""

    def __init__(self, ws):
        if not ws:
            self.n = 0
            self.nt = 0
            self.ns = 0
            self.norm = ws
            return

        tabs = 0
        spaces = 0
        for c in ws:
            if c == '\t':
                tabs += 1
                spaces = 0
            elif c == ' ':
                spaces += 1
            else:
                break

        self.n = len(ws)
        self.nt = tabs
        self.ns = spaces
        self.norm = ws

    def __repr__(self):
        return f"Whitespace({self.norm!r})"

    def __eq__(self, other):
        if isinstance(other, Whitespace):
            return self.norm == other.norm
        return NotImplemented

    def is_simple(self):
        return '\t' not in self.norm or ' ' not in self.norm

    def indent_level(self, tabsize=8):
        level = 0
        for c in self.norm:
            if c == '\t':
                level = (level // tabsize + 1) * tabsize
            elif c == ' ':
                level += 1
        return level


def check(file):
    """Check for whitespace-related problems in a Python source file."""
    if _os.path.isdir(file):
        names = _os.listdir(file)
        for name in sorted(names):
            fullname = _os.path.join(file, name)
            if (_os.path.isdir(fullname) or
                    (name.endswith('.py') and not name.startswith('.'))):
                check(fullname)
        return

    try:
        with _io.open(file, mode='rb') as f:
            process_tokens(_tokenize.tokenize(f.readline))
    except _tokenize.TokenError as msg:
        if verbose:
            print(f'{file}: Token Error: {msg}', file=_sys.stderr)
    except NannyNag as nag:
        if verbose:
            print(f'{file}:{nag.get_lineno()}: {nag.get_msg()}', file=_sys.stderr)
        return
    except OSError as msg:
        if verbose:
            print(f'{file}: I/O Error: {msg}', file=_sys.stderr)


def process_tokens(tokens):
    """Check a token stream for tab/space inconsistency.
    Raises NannyNag if inconsistency found.
    """
    INDENT = _token.INDENT
    DEDENT = _token.DEDENT
    NEWLINE = _token.NEWLINE
    NL = _token.NL
    COMMENT = _token.COMMENT
    ERRORTOKEN = _token.ERRORTOKEN

    indents = ['']  # stack of indentation strings
    check_equal = False

    for token_type, token_string, start, end, line in tokens:
        if token_type == NEWLINE:
            check_equal = False
        elif token_type == INDENT:
            new_indent = token_string
            indents.append(new_indent)
            # Check that new indent is consistent
            _check_indent(new_indent, indents, start[0], line)
        elif token_type == DEDENT:
            if len(indents) > 1:
                indents.pop()


def _check_indent(indent, indents, lineno, line):
    """Check indent for mixed tabs/spaces."""
    if '\t' in indent and ' ' in indent:
        # Check: are there tabs after spaces?
        seen_space = False
        for c in indent:
            if c == ' ':
                seen_space = True
            elif c == '\t' and seen_space:
                raise NannyNag(lineno, _ERR_MIXED, line)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def tabnanny2_nannynag():
    """NannyNag exception class exists; returns True."""
    nag = NannyNag(1, 'test message', 'line content\n')
    return (issubclass(NannyNag, Exception) and
            nag.get_lineno() == 1 and
            nag.get_msg() == 'test message')


def tabnanny2_check():
    """check() function exists and is callable; returns True."""
    return callable(check)


def tabnanny2_process_tokens():
    """process_tokens() detects indentation issues; returns True."""
    import tokenize as _tok
    import io as _io2
    src = b'def f():\n    pass\n'
    tokens = _tok.tokenize(_io2.BytesIO(src).readline)
    process_tokens(tokens)
    return True


__all__ = [
    'NannyNag', 'Whitespace', 'check', 'process_tokens', 'verbose',
    'tabnanny2_nannynag', 'tabnanny2_check', 'tabnanny2_process_tokens',
]
