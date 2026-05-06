"""
Clean-room implementation of sre_constants.

This module provides the opcodes, flags, and error class used by the
regular-expression engine.  Implemented from scratch without importing
the standard sre_constants module.
"""

# ---------------------------------------------------------------------------
# Magic / limits
# ---------------------------------------------------------------------------

MAGIC = 20171005

MAXREPEAT = 4294967295         # 2**32 - 1
MAXGROUPS = 2147483647         # 2**31 - 1


# ---------------------------------------------------------------------------
# error exception
# ---------------------------------------------------------------------------

class error(Exception):
    """Exception raised for invalid regular expressions."""

    def __init__(self, msg, pattern=None, pos=None):
        self.msg = msg
        self.pattern = pattern
        self.pos = pos
        if pattern is not None and pos is not None:
            msg = '%s at position %d' % (msg, pos)
            if isinstance(pattern, (bytes, bytearray)):
                newline = b'\n'
            else:
                newline = '\n'
            self.lineno = pattern.count(newline, 0, pos) + 1
            self.colno = pos - pattern.rfind(newline, 0, pos)
            if newline in pattern:
                msg = '%s (line %d, column %d)' % (msg, self.lineno, self.colno)
        else:
            self.lineno = self.colno = None
        super().__init__(msg)


# ---------------------------------------------------------------------------
# Opcode helper
# ---------------------------------------------------------------------------

class _NamedIntConstant(int):
    """An int subclass that knows its symbolic name (mirrors CPython)."""

    def __new__(cls, value, name):
        self = super().__new__(cls, value)
        self.name = name
        return self

    def __repr__(self):
        return self.name

    __str__ = __repr__


def _make_codes(names, namespace):
    """Create _NamedIntConstant objects for each name and inject them
    into the supplied namespace.  Returns the list of created objects."""
    items = []
    for i, name in enumerate(names):
        constant = _NamedIntConstant(i, name)
        namespace[name] = constant
        items.append(constant)
    return items


# ---------------------------------------------------------------------------
# Opcodes
# ---------------------------------------------------------------------------

OPCODES = [
    "FAILURE", "SUCCESS",
    "ANY", "ANY_ALL",
    "ASSERT", "ASSERT_NOT",
    "AT",
    "BRANCH",
    "CALL",
    "CATEGORY",
    "CHARSET", "BIGCHARSET",
    "GROUPREF", "GROUPREF_EXISTS", "GROUPREF_IGNORE",
    "IN", "IN_IGNORE",
    "INFO",
    "JUMP",
    "LITERAL", "LITERAL_IGNORE",
    "MARK",
    "MAX_UNTIL",
    "MIN_UNTIL",
    "NOT_LITERAL", "NOT_LITERAL_IGNORE",
    "NEGATE",
    "RANGE",
    "REPEAT",
    "REPEAT_ONE",
    "SUBPATTERN",
    "MIN_REPEAT_ONE",
    "RANGE_IGNORE",
    "MIN_REPEAT", "MAX_REPEAT",
]

ATCODES = [
    "AT_BEGINNING", "AT_BEGINNING_LINE", "AT_BEGINNING_STRING",
    "AT_BOUNDARY", "AT_NON_BOUNDARY",
    "AT_END", "AT_END_LINE", "AT_END_STRING",
    "AT_LOC_BOUNDARY", "AT_LOC_NON_BOUNDARY",
    "AT_UNI_BOUNDARY", "AT_UNI_NON_BOUNDARY",
]

CHCODES = [
    "CATEGORY_DIGIT", "CATEGORY_NOT_DIGIT",
    "CATEGORY_SPACE", "CATEGORY_NOT_SPACE",
    "CATEGORY_WORD", "CATEGORY_NOT_WORD",
    "CATEGORY_LINEBREAK", "CATEGORY_NOT_LINEBREAK",
    "CATEGORY_LOC_WORD", "CATEGORY_LOC_NOT_WORD",
    "CATEGORY_UNI_DIGIT", "CATEGORY_UNI_NOT_DIGIT",
    "CATEGORY_UNI_SPACE", "CATEGORY_UNI_NOT_SPACE",
    "CATEGORY_UNI_WORD", "CATEGORY_UNI_NOT_WORD",
    "CATEGORY_UNI_LINEBREAK", "CATEGORY_UNI_NOT_LINEBREAK",
]

_opcode_objs = _make_codes(OPCODES, globals())
_atcode_objs = _make_codes(ATCODES, globals())
_chcode_objs = _make_codes(CHCODES, globals())

# Replace string lists with the named-int objects, matching the original.
OPCODES = _opcode_objs
ATCODES = _atcode_objs
CHCODES = _chcode_objs


# ---------------------------------------------------------------------------
# Mappings used by the compiler/engine
# ---------------------------------------------------------------------------

AT_MULTILINE = {
    AT_BEGINNING: AT_BEGINNING_LINE,
    AT_END: AT_END_LINE,
}

AT_LOCALE = {
    AT_BOUNDARY: AT_LOC_BOUNDARY,
    AT_NON_BOUNDARY: AT_LOC_NON_BOUNDARY,
}

AT_UNICODE = {
    AT_BOUNDARY: AT_UNI_BOUNDARY,
    AT_NON_BOUNDARY: AT_UNI_NON_BOUNDARY,
}

CH_LOCALE = {
    CATEGORY_DIGIT: CATEGORY_DIGIT,
    CATEGORY_NOT_DIGIT: CATEGORY_NOT_DIGIT,
    CATEGORY_SPACE: CATEGORY_SPACE,
    CATEGORY_NOT_SPACE: CATEGORY_NOT_SPACE,
    CATEGORY_WORD: CATEGORY_LOC_WORD,
    CATEGORY_NOT_WORD: CATEGORY_LOC_NOT_WORD,
    CATEGORY_LINEBREAK: CATEGORY_LINEBREAK,
    CATEGORY_NOT_LINEBREAK: CATEGORY_NOT_LINEBREAK,
}

CH_UNICODE = {
    CATEGORY_DIGIT: CATEGORY_UNI_DIGIT,
    CATEGORY_NOT_DIGIT: CATEGORY_UNI_NOT_DIGIT,
    CATEGORY_SPACE: CATEGORY_UNI_SPACE,
    CATEGORY_NOT_SPACE: CATEGORY_UNI_NOT_SPACE,
    CATEGORY_WORD: CATEGORY_UNI_WORD,
    CATEGORY_NOT_WORD: CATEGORY_UNI_NOT_WORD,
    CATEGORY_LINEBREAK: CATEGORY_UNI_LINEBREAK,
    CATEGORY_NOT_LINEBREAK: CATEGORY_UNI_NOT_LINEBREAK,
}


# ---------------------------------------------------------------------------
# Flags
# ---------------------------------------------------------------------------

SRE_FLAG_TEMPLATE   = 1     # template mode (disable backtracking)
SRE_FLAG_IGNORECASE = 2     # case insensitive
SRE_FLAG_LOCALE     = 4     # honour system locale
SRE_FLAG_MULTILINE  = 8     # treat target as multiline string
SRE_FLAG_DOTALL     = 16    # treat target as a single string
SRE_FLAG_UNICODE    = 32    # use unicode "locale"
SRE_FLAG_VERBOSE    = 64    # ignore whitespace and comments
SRE_FLAG_DEBUG      = 128   # debugging
SRE_FLAG_ASCII      = 256   # use ascii "locale"


# ---------------------------------------------------------------------------
# Sanity-check / verification functions
# ---------------------------------------------------------------------------

def srec2_opcodes():
    """Verify that the opcode table is well-formed."""
    # The first two entries must be FAILURE=0 and SUCCESS=1.
    if int(FAILURE) != 0 or int(SUCCESS) != 1:
        return False
    # Every opcode is a unique consecutive integer with a name attribute.
    for index, op in enumerate(OPCODES):
        if int(op) != index:
            return False
        if not isinstance(op, int):
            return False
        if not hasattr(op, "name"):
            return False
        if op.name not in globals():
            return False
        if globals()[op.name] is not op:
            return False
    # Spot check a few well-known opcodes exist.
    required = ("ANY", "BRANCH", "LITERAL", "MAX_REPEAT",
                "MIN_REPEAT", "GROUPREF", "IN", "MARK", "JUMP")
    for name in required:
        if name not in globals():
            return False
    # AT and CH code tables must also be well-formed.
    for index, op in enumerate(ATCODES):
        if int(op) != index or op.name != ATCODES[index].name:
            return False
    for index, op in enumerate(CHCODES):
        if int(op) != index or op.name != CHCODES[index].name:
            return False
    return True


def srec2_flags():
    """Verify the SRE_FLAG_* constants."""
    expected = {
        "SRE_FLAG_TEMPLATE":   1,
        "SRE_FLAG_IGNORECASE": 2,
        "SRE_FLAG_LOCALE":     4,
        "SRE_FLAG_MULTILINE":  8,
        "SRE_FLAG_DOTALL":     16,
        "SRE_FLAG_UNICODE":    32,
        "SRE_FLAG_VERBOSE":    64,
        "SRE_FLAG_DEBUG":      128,
        "SRE_FLAG_ASCII":      256,
    }
    g = globals()
    for name, value in expected.items():
        if name not in g:
            return False
        if g[name] != value:
            return False
    # All flag bits should be distinct powers of two.
    seen = 0
    for value in expected.values():
        if value & (value - 1) != 0:        # not a power of two
            return False
        if seen & value:
            return False
        seen |= value
    return True


def srec2_error():
    """Verify the error exception class."""
    if not isinstance(error, type):
        return False
    if not issubclass(error, Exception):
        return False

    # No-context construction: lineno/colno should be None.
    e1 = error("bad escape")
    if e1.msg != "bad escape":
        return False
    if e1.pattern is not None or e1.pos is not None:
        return False
    if e1.lineno is not None or e1.colno is not None:
        return False
    if "bad escape" not in str(e1):
        return False

    # With a single-line pattern: positional info, no line/column suffix.
    e2 = error("oops", "abc", 1)
    if e2.pattern != "abc" or e2.pos != 1:
        return False
    if e2.lineno != 1 or e2.colno != 2:
        return False
    if "at position 1" not in str(e2):
        return False

    # Multi-line pattern: line and column numbers should be reported.
    pat = "abc\ndef\nghi"
    e3 = error("boom", pat, 9)              # position 9 is on line 3, col 2
    if e3.lineno != 3 or e3.colno != 2:
        return False
    if "line 3" not in str(e3) or "column 2" not in str(e3):
        return False

    # Bytes patterns must also be supported.
    e4 = error("bytes", b"abc\ndef", 5)
    if e4.lineno != 2 or e4.colno != 2:
        return False

    # Ensure raise/catch round-trips correctly.
    try:
        raise error("rethrow", "xy", 0)
    except error as caught:
        if caught.msg != "rethrow":
            return False
    else:
        return False

    return True