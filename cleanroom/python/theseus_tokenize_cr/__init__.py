"""
theseus_tokenize_cr — Clean-room Python tokenizer.
No import of the standard `tokenize` module.
"""

import re
import io

# Token type constants
ENDMARKER = 0
NAME = 1
NUMBER = 2
STRING = 3
OP = 54
NEWLINE = 4
NL = 61
COMMENT = 60
INDENT = 5
DEDENT = 6
ERRORTOKEN = 59
ENCODING = 62

# Token name map
tok_name = {
    ENDMARKER: 'ENDMARKER',
    NAME: 'NAME',
    NUMBER: 'NUMBER',
    STRING: 'STRING',
    OP: 'OP',
    NEWLINE: 'NEWLINE',
    NL: 'NL',
    COMMENT: 'COMMENT',
    INDENT: 'INDENT',
    DEDENT: 'DEDENT',
    ERRORTOKEN: 'ERRORTOKEN',
    ENCODING: 'ENCODING',
}


class TokenInfo:
    """Represents a single token."""
    __slots__ = ('type', 'string', 'start', 'end', 'line')

    def __init__(self, type, string, start, end, line):
        self.type = type
        self.string = string
        self.start = start
        self.end = end
        self.line = line

    def __repr__(self):
        return (f'TokenInfo(type={self.type} ({tok_name.get(self.type, "?")}), '
                f'string={self.string!r}, start={self.start}, end={self.end}, line={self.line!r})')

    def __iter__(self):
        yield self.type
        yield self.string
        yield self.start
        yield self.end
        yield self.line


# Regex patterns for token recognition (non-verbose for safe concatenation)
_NAME_PAT = r'[a-zA-Z_]\w*'
_NUMBER_PAT = r'(?:0[xX][0-9a-fA-F]+(?:_[0-9a-fA-F]+)*|0[oO][0-7]+(?:_[0-7]+)*|0[bB][01]+(?:_[01]+)*|(?:\d+(?:_\d+)*\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)[jJ]?'
_STRING_PAT = r'(?:[bBfFuUrR]{0,3})(?:"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')'
_OP_PAT = r'(?:<<=|>>=|\*\*=|//=|->|:=|==|!=|<=|>=|<<|>>|\*\*|//|\+=|-=|\*=|/=|%=|&=|\|=|\^=|[+\-*/%&|^~<>=!:;.,\[\]{}()])'
_COMMENT_PAT = r'#[^\r\n]*'
_WHITESPACE_PAT = r'[ \t]+'
_NEWLINE_PAT = r'\r?\n'
_CONTINUATION_PAT = r'\\\r?\n'

_TOKEN_RE = re.compile(
    r'(?P<STRING>' + _STRING_PAT + r')'
    r'|(?P<NUMBER>' + _NUMBER_PAT + r')'
    r'|(?P<NAME>' + _NAME_PAT + r')'
    r'|(?P<OP>' + _OP_PAT + r')'
    r'|(?P<COMMENT>' + _COMMENT_PAT + r')'
    r'|(?P<NEWLINE>' + _NEWLINE_PAT + r')'
    r'|(?P<CONTINUATION>' + _CONTINUATION_PAT + r')'
    r'|(?P<WHITESPACE>' + _WHITESPACE_PAT + r')'
    r'|(?P<ERRORTOKEN>.)',
    re.DOTALL,
)


def generate_tokens(readline):
    """Tokenize a source string via a readline callable.
    Yields TokenInfo objects.
    """
    lnum = 0
    indents = [0]
    parenlev = 0
    continued = False

    while True:
        try:
            line = readline()
        except StopIteration:
            line = ''

        if not line:
            # emit DEDENTs for remaining indents
            for _ in range(len(indents) - 1):
                yield TokenInfo(DEDENT, '', (lnum, 0), (lnum, 0), '')
            yield TokenInfo(ENDMARKER, '', (lnum, 0), (lnum, 0), '')
            return

        lnum += 1
        pos = 0
        max_pos = len(line)

        if not continued:
            # Handle INDENT/DEDENT
            stripped = line.lstrip(' \t')
            if stripped and stripped[0] not in ('#', '\n', '\r', '\\'):
                indent = len(line) - len(stripped)
                if indent > indents[-1]:
                    indents.append(indent)
                    yield TokenInfo(INDENT, line[:indent], (lnum, 0), (lnum, indent), line)
                while indent < indents[-1]:
                    indents.pop()
                    yield TokenInfo(DEDENT, '', (lnum, 0), (lnum, indent), line)

        for m in _TOKEN_RE.finditer(line):
            tok_type_name = m.lastgroup
            tok_string = m.group()
            start = (lnum, m.start())
            end = (lnum, m.end())

            if tok_type_name == 'NAME':
                yield TokenInfo(NAME, tok_string, start, end, line)
            elif tok_type_name == 'NUMBER':
                yield TokenInfo(NUMBER, tok_string, start, end, line)
            elif tok_type_name == 'STRING':
                yield TokenInfo(STRING, tok_string, start, end, line)
            elif tok_type_name == 'OP':
                yield TokenInfo(OP, tok_string, start, end, line)
            elif tok_type_name == 'COMMENT':
                yield TokenInfo(COMMENT, tok_string, start, end, line)
            elif tok_type_name == 'NEWLINE':
                if parenlev == 0:
                    yield TokenInfo(NEWLINE, tok_string, start, end, line)
                else:
                    yield TokenInfo(NL, tok_string, start, end, line)
            elif tok_type_name == 'CONTINUATION':
                continued = True
                continue
            elif tok_type_name == 'WHITESPACE':
                continue
            elif tok_type_name == 'ERRORTOKEN':
                yield TokenInfo(ERRORTOKEN, tok_string, start, end, line)


def tokenize(readline):
    """Tokenize a source, yielding TokenInfo objects (with ENCODING first)."""
    encoding = 'utf-8'
    yield TokenInfo(ENCODING, encoding, (0, 0), (0, 0), '')
    yield from generate_tokens(readline)


def _readline_from_string(source):
    """Return a readline callable for a source string."""
    lines = source.splitlines(keepends=True)
    if lines and not lines[-1].endswith('\n'):
        lines[-1] += '\n'
    lines.append('')
    idx = [0]

    def readline():
        if idx[0] < len(lines):
            line = lines[idx[0]]
            idx[0] += 1
            return line
        return ''
    return readline


def tokenize_string(source):
    """Tokenize a source string, returning a list of TokenInfo objects."""
    return list(generate_tokens(_readline_from_string(source)))


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def tokenize2_name():
    """tokenize 'x = 1' yields a NAME token for 'x'; returns True."""
    tokens = tokenize_string('x = 1')
    names = [t for t in tokens if t.type == NAME]
    return any(t.string == 'x' for t in names)


def tokenize2_number():
    """tokenize '42' yields a NUMBER token '42'; returns '42'."""
    tokens = tokenize_string('42')
    numbers = [t for t in tokens if t.type == NUMBER]
    return numbers[0].string if numbers else ''


def tokenize2_count():
    """tokenize 'a + b' yields at least 3 non-ENDMARKER tokens; returns True."""
    tokens = tokenize_string('a + b')
    non_end = [t for t in tokens if t.type not in (ENDMARKER, NEWLINE, NL, ENCODING, INDENT, DEDENT)]
    return len(non_end) >= 3


__all__ = [
    'ENDMARKER', 'NAME', 'NUMBER', 'STRING', 'OP', 'NEWLINE', 'NL',
    'COMMENT', 'INDENT', 'DEDENT', 'ERRORTOKEN', 'ENCODING',
    'tok_name', 'TokenInfo',
    'generate_tokens', 'tokenize', 'tokenize_string',
    'tokenize2_name', 'tokenize2_number', 'tokenize2_count',
]