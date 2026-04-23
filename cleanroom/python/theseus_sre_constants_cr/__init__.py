"""
theseus_sre_constants_cr — Clean-room sre_constants module.
No import of the standard `sre_constants` module.
These are the internal constants used by the re module's compiler.
"""

import re as _re

# Opcode constants (from _sre C module)
FAILURE = 0
SUCCESS = 1
ANY = 2
ANY_ALL = 3
ASSERT = 4
ASSERT_NOT = 5
AT = 6
ATOMIC_GROUP = 7
BRANCH = 8
GROUPREF = 9
GROUPREF_IGNORE = 10
GROUPREF_UNI_IGNORE = 11
GROUPREF_LOC_IGNORE = 12
GROUPREF_EXISTS = 13
IN = 14
IN_IGNORE = 15
IN_UNI_IGNORE = 16
IN_LOC_IGNORE = 17
INFO = 18
JUMP = 19
LITERAL = 20
LITERAL_IGNORE = 21
LITERAL_UNI_IGNORE = 22
LITERAL_LOC_IGNORE = 23
MARK = 24
MAX_REPEAT = 25
MIN_REPEAT = 26
NOT_LITERAL = 27
NOT_LITERAL_IGNORE = 28
NOT_LITERAL_UNI_IGNORE = 29
NOT_LITERAL_LOC_IGNORE = 30
POSSESSIVE_REPEAT = 31
POSSESSIVE_IN = 32
REPEAT = 33
REPEAT_ONE = 34
SUBPATTERN = 35
MIN_REPEAT_ONE = 36
RANGE = 37
RANGE_UNI_IGNORE = 38
BIGCHARSET = 39
CATEGORY = 40
GROUPREF_LOC = 41

# AT codes (anchor positions)
AT_BEGINNING = 0
AT_BEGINNING_LINE = 1
AT_BEGINNING_STRING = 2
AT_BOUNDARY = 3
AT_NON_BOUNDARY = 4
AT_END = 5
AT_END_LINE = 6
AT_END_STRING = 7
AT_LOC_BOUNDARY = 8
AT_LOC_NON_BOUNDARY = 9
AT_UNI_BOUNDARY = 10
AT_UNI_NON_BOUNDARY = 11

ATCODES = {
    'at_beginning': AT_BEGINNING,
    'at_beginning_line': AT_BEGINNING_LINE,
    'at_beginning_string': AT_BEGINNING_STRING,
    'at_boundary': AT_BOUNDARY,
    'at_non_boundary': AT_NON_BOUNDARY,
    'at_end': AT_END,
    'at_end_line': AT_END_LINE,
    'at_end_string': AT_END_STRING,
    'at_loc_boundary': AT_LOC_BOUNDARY,
    'at_loc_non_boundary': AT_LOC_NON_BOUNDARY,
    'at_uni_boundary': AT_UNI_BOUNDARY,
    'at_uni_non_boundary': AT_UNI_NON_BOUNDARY,
}

# Category codes
CATEGORY_DIGIT = 0
CATEGORY_NOT_DIGIT = 1
CATEGORY_SPACE = 2
CATEGORY_NOT_SPACE = 3
CATEGORY_WORD = 4
CATEGORY_NOT_WORD = 5
CATEGORY_LINEBREAK = 6
CATEGORY_NOT_LINEBREAK = 7
CATEGORY_LOC_WORD = 8
CATEGORY_LOC_NOT_WORD = 9
CATEGORY_UNI_DIGIT = 10
CATEGORY_UNI_NOT_DIGIT = 11
CATEGORY_UNI_SPACE = 12
CATEGORY_UNI_NOT_SPACE = 13
CATEGORY_UNI_WORD = 14
CATEGORY_UNI_NOT_WORD = 15
CATEGORY_UNI_LINEBREAK = 16
CATEGORY_UNI_NOT_LINEBREAK = 17

CHCODES = {
    'category_digit': CATEGORY_DIGIT,
    'category_not_digit': CATEGORY_NOT_DIGIT,
    'category_space': CATEGORY_SPACE,
    'category_not_space': CATEGORY_NOT_SPACE,
    'category_word': CATEGORY_WORD,
    'category_not_word': CATEGORY_NOT_WORD,
}

# Flag constants (same as in re module)
SRE_FLAG_TEMPLATE = 1
SRE_FLAG_IGNORECASE = 2
SRE_FLAG_LOCALE = 4
SRE_FLAG_MULTILINE = 8
SRE_FLAG_DOTALL = 16
SRE_FLAG_UNICODE = 32
SRE_FLAG_VERBOSE = 64
SRE_FLAG_DEBUG = 128
SRE_FLAG_ASCII = 256

# Max repeat
MAXREPEAT = 2**32 - 1

# Opcode names table
OPCODES = [
    'failure', 'success', 'any', 'any_all', 'assert', 'assert_not',
    'at', 'atomic_group', 'branch', 'groupref', 'groupref_ignore',
    'groupref_uni_ignore', 'groupref_loc_ignore', 'groupref_exists',
    'in', 'in_ignore', 'in_uni_ignore', 'in_loc_ignore', 'info',
    'jump', 'literal', 'literal_ignore', 'literal_uni_ignore',
    'literal_loc_ignore', 'mark', 'max_repeat', 'min_repeat',
    'not_literal', 'not_literal_ignore', 'not_literal_uni_ignore',
    'not_literal_loc_ignore', 'possessive_repeat', 'possessive_in',
    'repeat', 'repeat_one', 'subpattern', 'min_repeat_one',
    'range', 'range_uni_ignore', 'bigcharset', 'category',
    'groupref_loc', 'at_beginning',
]


class error(Exception):
    """Exception raised for errors in the regular expression."""
    def __init__(self, msg, pattern=None, pos=None):
        self.msg = msg
        self.pattern = pattern
        self.pos = pos
        if pattern is not None and pos is not None:
            msg = f'{msg} at position {pos}'
            if isinstance(pattern, str):
                msg += f' (line {pattern.count(chr(10), 0, pos) + 1}, col {pos - pattern.rfind(chr(10), 0, pos)})'
        super().__init__(msg)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def srec2_opcodes():
    """Regex opcode constants are defined; returns True."""
    return (FAILURE == 0 and
            SUCCESS == 1 and
            ANY == 2 and
            LITERAL == 20 and
            isinstance(OPCODES, list))


def srec2_flags():
    """Regex flag constants are defined; returns True."""
    return (SRE_FLAG_IGNORECASE == 2 and
            SRE_FLAG_MULTILINE == 8 and
            SRE_FLAG_DOTALL == 16 and
            SRE_FLAG_VERBOSE == 64)


def srec2_error():
    """error exception class exists; returns True."""
    e = error('test error')
    return (issubclass(error, Exception) and
            str(e) == 'test error')


__all__ = [
    'error', 'MAXREPEAT', 'OPCODES', 'ATCODES', 'CHCODES',
    'FAILURE', 'SUCCESS', 'ANY', 'ANY_ALL', 'ASSERT', 'ASSERT_NOT',
    'AT', 'BRANCH', 'GROUPREF', 'GROUPREF_EXISTS', 'IN', 'INFO',
    'JUMP', 'LITERAL', 'MARK', 'MAX_REPEAT', 'MIN_REPEAT',
    'NOT_LITERAL', 'REPEAT', 'REPEAT_ONE', 'SUBPATTERN', 'MIN_REPEAT_ONE',
    'RANGE', 'BIGCHARSET', 'CATEGORY',
    'AT_BEGINNING', 'AT_BEGINNING_LINE', 'AT_BEGINNING_STRING',
    'AT_BOUNDARY', 'AT_NON_BOUNDARY', 'AT_END', 'AT_END_LINE',
    'AT_END_STRING', 'AT_UNI_BOUNDARY', 'AT_UNI_NON_BOUNDARY',
    'CATEGORY_DIGIT', 'CATEGORY_NOT_DIGIT', 'CATEGORY_SPACE',
    'CATEGORY_NOT_SPACE', 'CATEGORY_WORD', 'CATEGORY_NOT_WORD',
    'SRE_FLAG_TEMPLATE', 'SRE_FLAG_IGNORECASE', 'SRE_FLAG_LOCALE',
    'SRE_FLAG_MULTILINE', 'SRE_FLAG_DOTALL', 'SRE_FLAG_UNICODE',
    'SRE_FLAG_VERBOSE', 'SRE_FLAG_DEBUG', 'SRE_FLAG_ASCII',
    'srec2_opcodes', 'srec2_flags', 'srec2_error',
]
