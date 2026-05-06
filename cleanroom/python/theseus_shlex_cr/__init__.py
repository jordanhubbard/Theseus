"""
theseus_shlex_cr — Clean-room shlex module.
No import of the standard `shlex` module.
"""

import io as _io


_WHITESPACE = ' \t\n\r'
_WORDCHARS = ('abcdefghijklmnopqrstuvwxyz'
              'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_'
              '@%+=:,./-')


class shlex:
    """A lexical analyzer for simple shell-like syntaxes."""

    def __init__(self, instream=None, infile=None, posix=False, punctuation_chars=False):
        if isinstance(instream, str):
            instream = _io.StringIO(instream)
        if instream is not None:
            self.instream = instream
            self.infile = infile
        else:
            self.instream = None
            self.infile = None
        self.posix = posix
        self.wordchars = _WORDCHARS
        self.whitespace = _WHITESPACE
        self.whitespace_split = False
        self.quotes = '\'"'
        self.escape = '\\'
        self.escapedquotes = '"'
        self.commenters = '#'
        self.token = ''
        self._token_list = []
        self._eof = ''

    def get_token(self):
        if self._token_list:
            return self._token_list.pop(0)
        return self.read_token()

    def push_token(self, tok):
        self._token_list.insert(0, tok)

    def read_token(self):
        quoted = False
        escapedstate = ' '
        state = ' '
        token = ''

        while True:
            nextchar = self.instream.read(1) if self.instream else ''
            if not nextchar:
                if state in self.quotes:
                    raise ValueError("No closing quotation")
                if state == self.escape:
                    raise ValueError("No escaped character")
                if token:
                    return token
                return self._eof

            if state == ' ':
                if nextchar in self.whitespace:
                    if token:
                        return token
                elif nextchar in self.commenters:
                    self.instream.readline()
                elif nextchar in self.quotes:
                    if not self.posix:
                        token = nextchar
                    state = nextchar
                elif nextchar == self.escape and self.posix:
                    escapedstate = 'a'
                    state = nextchar
                elif nextchar in self.wordchars or (self.whitespace_split and nextchar not in self.whitespace):
                    token = nextchar
                    state = 'a'
                else:
                    token = nextchar
                    return token
            elif state in self.quotes:
                quoted = True
                if nextchar == state:
                    if self.posix:
                        state = 'a'
                    else:
                        token += nextchar
                        return token
                elif self.posix and nextchar in self.escape and state in self.escapedquotes:
                    escapedstate = state
                    state = nextchar
                else:
                    token += nextchar
            elif state == self.escape:
                if nextchar in self.whitespace and escapedstate == ' ':
                    state = escapedstate
                    if token or self.posix:
                        token += nextchar
                else:
                    token += nextchar
                    state = escapedstate
            elif state == 'a':
                if nextchar in self.whitespace:
                    state = ' '
                    if token or (self.posix and quoted):
                        return token
                elif nextchar in self.commenters:
                    self.instream.readline()
                    state = ' '
                    if token:
                        return token
                elif nextchar in self.quotes and self.posix:
                    state = nextchar
                elif nextchar in self.quotes:
                    token += nextchar
                    state = nextchar
                elif nextchar == self.escape and self.posix:
                    escapedstate = 'a'
                    state = nextchar
                elif nextchar in self.wordchars or nextchar in self.quotes or self.whitespace_split:
                    token += nextchar
                else:
                    self.push_token(nextchar)
                    state = ' '
                    if token:
                        return token

    def __iter__(self):
        return self

    def __next__(self):
        token = self.get_token()
        if token == self._eof:
            raise StopIteration
        return token


def split(s, comments=False, posix=True):
    """Split a shell-like string into tokens."""
    lex = shlex(s, posix=posix)
    lex.whitespace_split = True
    if not comments:
        lex.commenters = ''
    return list(lex)


def join(split_command):
    """Join tokens back into a single command string."""
    return ' '.join(quote(arg) for arg in split_command)


_SAFE = frozenset(_WORDCHARS)


def quote(s):
    """Return a shell-safe quoted version of s."""
    if not s:
        return "''"
    if all(c in _SAFE for c in s):
        return s
    return "'" + s.replace("'", "'\"'\"'") + "'"


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def shlex2_split():
    """split('echo hello world') returns 3 tokens; returns 3."""
    return len(split('echo hello world'))


def shlex2_quoted():
    """split respects quoted strings as single token; returns True."""
    tokens = split('echo "hello world"')
    return tokens == ['echo', 'hello world']


def shlex2_quote():
    """quote wraps strings with spaces in single quotes; returns True."""
    q = quote('hello world')
    return q.startswith("'") and q.endswith("'")


__all__ = [
    'shlex', 'split', 'join', 'quote',
    'shlex2_split', 'shlex2_quoted', 'shlex2_quote',
]