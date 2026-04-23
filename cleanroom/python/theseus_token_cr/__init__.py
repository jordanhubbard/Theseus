"""
theseus_token_cr — Clean-room token constants.
No import of the standard `token` module.
"""

# Token type constants (mirrors CPython's token.py)
ENDMARKER  = 0
NAME       = 1
NUMBER     = 2
STRING     = 3
NEWLINE    = 4
INDENT     = 5
DEDENT     = 6
LPAR       = 7
RPAR       = 8
LSQB       = 9
RSQB       = 10
COLON      = 11
COMMA      = 12
SEMI       = 13
PLUS       = 14
MINUS      = 15
STAR       = 16
SLASH      = 17
VBAR       = 18
AMPER      = 19
LESS       = 20
GREATER    = 21
EQUAL      = 22
DOT        = 23
PERCENT    = 24
LBRACE     = 25
RBRACE     = 26
EQEQUAL    = 27
NOTEQUAL   = 28
LESSEQUAL  = 29
GREATEREQUAL = 30
TILDE      = 31
CIRCUMFLEX = 32
LEFTSHIFT  = 33
RIGHTSHIFT = 34
DOUBLESTAR = 35
PLUSEQUAL  = 36
MINEQUAL   = 37
STAREQUAL  = 38
SLASHEQUAL = 39
PERCENTEQUAL = 40
AMPEREQUAL = 41
VBAREQUAL  = 42
CIRCUMFLEXEQUAL = 43
LEFTSHIFTEQUAL  = 44
RIGHTSHIFTEQUAL = 45
DOUBLESTAREQUAL = 46
DOUBLESLASH     = 47
DOUBLESLASHEQUAL = 48
AT             = 49
ATEQUAL        = 50
RARROW         = 51
ELLIPSIS       = 52
COLONEQUAL     = 53
OP             = 54
AWAIT          = 55
ASYNC          = 56
TYPE_IGNORE    = 57
TYPE_COMMENT   = 58
SOFT_KEYWORD   = 59
ERRORTOKEN     = 60
COMMENT        = 61
NL             = 62
ENCODING       = 63
N_TOKENS       = 64
NT_OFFSET      = 256

# Token name map
tok_name = {
    ENDMARKER: 'ENDMARKER',
    NAME: 'NAME',
    NUMBER: 'NUMBER',
    STRING: 'STRING',
    NEWLINE: 'NEWLINE',
    INDENT: 'INDENT',
    DEDENT: 'DEDENT',
    LPAR: 'LPAR',
    RPAR: 'RPAR',
    LSQB: 'LSQB',
    RSQB: 'RSQB',
    COLON: 'COLON',
    COMMA: 'COMMA',
    SEMI: 'SEMI',
    PLUS: 'PLUS',
    MINUS: 'MINUS',
    STAR: 'STAR',
    SLASH: 'SLASH',
    VBAR: 'VBAR',
    AMPER: 'AMPER',
    LESS: 'LESS',
    GREATER: 'GREATER',
    EQUAL: 'EQUAL',
    DOT: 'DOT',
    PERCENT: 'PERCENT',
    LBRACE: 'LBRACE',
    RBRACE: 'RBRACE',
    EQEQUAL: 'EQEQUAL',
    NOTEQUAL: 'NOTEQUAL',
    LESSEQUAL: 'LESSEQUAL',
    GREATEREQUAL: 'GREATEREQUAL',
    TILDE: 'TILDE',
    CIRCUMFLEX: 'CIRCUMFLEX',
    LEFTSHIFT: 'LEFTSHIFT',
    RIGHTSHIFT: 'RIGHTSHIFT',
    DOUBLESTAR: 'DOUBLESTAR',
    PLUSEQUAL: 'PLUSEQUAL',
    MINEQUAL: 'MINEQUAL',
    STAREQUAL: 'STAREQUAL',
    SLASHEQUAL: 'SLASHEQUAL',
    PERCENTEQUAL: 'PERCENTEQUAL',
    AMPEREQUAL: 'AMPEREQUAL',
    VBAREQUAL: 'VBAREQUAL',
    CIRCUMFLEXEQUAL: 'CIRCUMFLEXEQUAL',
    LEFTSHIFTEQUAL: 'LEFTSHIFTEQUAL',
    RIGHTSHIFTEQUAL: 'RIGHTSHIFTEQUAL',
    DOUBLESTAREQUAL: 'DOUBLESTAREQUAL',
    DOUBLESLASH: 'DOUBLESLASH',
    DOUBLESLASHEQUAL: 'DOUBLESLASHEQUAL',
    AT: 'AT',
    ATEQUAL: 'ATEQUAL',
    RARROW: 'RARROW',
    ELLIPSIS: 'ELLIPSIS',
    COLONEQUAL: 'COLONEQUAL',
    OP: 'OP',
    AWAIT: 'AWAIT',
    ASYNC: 'ASYNC',
    TYPE_IGNORE: 'TYPE_IGNORE',
    TYPE_COMMENT: 'TYPE_COMMENT',
    SOFT_KEYWORD: 'SOFT_KEYWORD',
    ERRORTOKEN: 'ERRORTOKEN',
    COMMENT: 'COMMENT',
    NL: 'NL',
    ENCODING: 'ENCODING',
    N_TOKENS: 'N_TOKENS',
    NT_OFFSET: 'NT_OFFSET',
}

# Exact type mapping for operators
EXACT_TYPE = {
    '(': LPAR, ')': RPAR, '[': LSQB, ']': RSQB,
    ':': COLON, ',': COMMA, ';': SEMI, '+': PLUS,
    '-': MINUS, '*': STAR, '/': SLASH, '|': VBAR,
    '&': AMPER, '<': LESS, '>': GREATER, '=': EQUAL,
    '.': DOT, '%': PERCENT, '{': LBRACE, '}': RBRACE,
    '==': EQEQUAL, '!=': NOTEQUAL, '<=': LESSEQUAL, '>=': GREATEREQUAL,
    '~': TILDE, '^': CIRCUMFLEX, '<<': LEFTSHIFT, '>>': RIGHTSHIFT,
    '**': DOUBLESTAR, '+=': PLUSEQUAL, '-=': MINEQUAL, '*=': STAREQUAL,
    '/=': SLASHEQUAL, '%=': PERCENTEQUAL, '&=': AMPEREQUAL, '|=': VBAREQUAL,
    '^=': CIRCUMFLEXEQUAL, '<<=': LEFTSHIFTEQUAL, '>>=': RIGHTSHIFTEQUAL,
    '**=': DOUBLESTAREQUAL, '//': DOUBLESLASH, '//=': DOUBLESLASHEQUAL,
    '@': AT, '@=': ATEQUAL, '->': RARROW, '...': ELLIPSIS, ':=': COLONEQUAL,
}


def iseof(type):
    """Return True if the token type is ENDMARKER."""
    return type == ENDMARKER


def isexception(type):
    """Return True if the token type is ERRORTOKEN."""
    return type == ERRORTOKEN


def isnonterminal(type):
    """Return True if the type is a non-terminal."""
    return type >= NT_OFFSET


def isterminal(type):
    """Return True if the type is a terminal."""
    return type < NT_OFFSET


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def token2_name_value():
    """NAME == 1; returns 1."""
    return NAME


def token2_tok_name():
    """tok_name[1] == 'NAME'; returns 'NAME'."""
    return tok_name[1]


def token2_iseof():
    """iseof(ENDMARKER) is True; returns True."""
    return iseof(ENDMARKER)


__all__ = [
    'ENDMARKER', 'NAME', 'NUMBER', 'STRING', 'NEWLINE', 'INDENT', 'DEDENT',
    'LPAR', 'RPAR', 'LSQB', 'RSQB', 'COLON', 'COMMA', 'SEMI', 'PLUS',
    'MINUS', 'STAR', 'SLASH', 'VBAR', 'AMPER', 'LESS', 'GREATER', 'EQUAL',
    'DOT', 'PERCENT', 'LBRACE', 'RBRACE', 'EQEQUAL', 'NOTEQUAL',
    'LESSEQUAL', 'GREATEREQUAL', 'OP', 'ERRORTOKEN', 'COMMENT', 'NL',
    'ENCODING', 'N_TOKENS', 'NT_OFFSET',
    'tok_name', 'EXACT_TYPE',
    'iseof', 'isexception', 'isnonterminal', 'isterminal',
    'token2_name_value', 'token2_tok_name', 'token2_iseof',
]
