"""Clean-room implementation of a Python opcode-like module.

Provides opmap (name -> code), opname (code -> name), and LOAD_CONST.
No imports from the original `opcode` module.
"""

# Internal opcode table: (name, code).  Codes are byte-sized (0..255).
# These values approximate a recent CPython opcode layout but are defined
# entirely from scratch here — we never import the real `opcode` module.
_OPCODE_TABLE = (
    ("CACHE", 0),
    ("POP_TOP", 1),
    ("PUSH_NULL", 2),
    ("INTERPRETER_EXIT", 3),
    ("END_FOR", 4),
    ("END_SEND", 5),
    ("NOP", 9),
    ("UNARY_NEGATIVE", 11),
    ("UNARY_NOT", 12),
    ("UNARY_INVERT", 15),
    ("RESERVED", 17),
    ("BINARY_SUBSCR", 25),
    ("BINARY_SLICE", 26),
    ("STORE_SLICE", 27),
    ("GET_LEN", 30),
    ("MATCH_MAPPING", 31),
    ("MATCH_SEQUENCE", 32),
    ("MATCH_KEYS", 33),
    ("PUSH_EXC_INFO", 35),
    ("CHECK_EXC_MATCH", 36),
    ("CHECK_EG_MATCH", 37),
    ("WITH_EXCEPT_START", 49),
    ("GET_AITER", 50),
    ("GET_ANEXT", 51),
    ("BEFORE_ASYNC_WITH", 52),
    ("BEFORE_WITH", 53),
    ("END_ASYNC_FOR", 54),
    ("CLEANUP_THROW", 55),
    ("STORE_SUBSCR", 60),
    ("DELETE_SUBSCR", 61),
    ("GET_ITER", 68),
    ("GET_YIELD_FROM_ITER", 69),
    ("LOAD_BUILD_CLASS", 71),
    ("LOAD_ASSERTION_ERROR", 74),
    ("RETURN_GENERATOR", 75),
    ("RETURN_VALUE", 83),
    ("SETUP_ANNOTATIONS", 85),
    ("LOAD_LOCALS", 87),
    ("POP_EXCEPT", 89),
    ("STORE_NAME", 90),
    ("DELETE_NAME", 91),
    ("UNPACK_SEQUENCE", 92),
    ("FOR_ITER", 93),
    ("UNPACK_EX", 94),
    ("STORE_ATTR", 95),
    ("DELETE_ATTR", 96),
    ("STORE_GLOBAL", 97),
    ("DELETE_GLOBAL", 98),
    ("SWAP", 99),
    ("LOAD_CONST", 100),
    ("LOAD_NAME", 101),
    ("BUILD_TUPLE", 102),
    ("BUILD_LIST", 103),
    ("BUILD_SET", 104),
    ("BUILD_MAP", 105),
    ("LOAD_ATTR", 106),
    ("COMPARE_OP", 107),
    ("IMPORT_NAME", 108),
    ("IMPORT_FROM", 109),
    ("JUMP_FORWARD", 110),
    ("POP_JUMP_IF_FALSE", 114),
    ("POP_JUMP_IF_TRUE", 115),
    ("LOAD_GLOBAL", 116),
    ("IS_OP", 117),
    ("CONTAINS_OP", 118),
    ("RERAISE", 119),
    ("COPY", 120),
    ("RETURN_CONST", 121),
    ("BINARY_OP", 122),
    ("SEND", 123),
    ("LOAD_FAST", 124),
    ("STORE_FAST", 125),
    ("DELETE_FAST", 126),
    ("LOAD_FAST_CHECK", 127),
    ("POP_JUMP_IF_NOT_NONE", 128),
    ("POP_JUMP_IF_NONE", 129),
    ("RAISE_VARARGS", 130),
    ("GET_AWAITABLE", 131),
    ("MAKE_FUNCTION", 132),
    ("BUILD_SLICE", 133),
    ("JUMP_BACKWARD_NO_INTERRUPT", 134),
    ("MAKE_CELL", 135),
    ("LOAD_DEREF", 137),
    ("STORE_DEREF", 138),
    ("DELETE_DEREF", 139),
    ("JUMP_BACKWARD", 140),
    ("LOAD_SUPER_ATTR", 141),
    ("CALL_FUNCTION_EX", 142),
    ("LOAD_FAST_AND_CLEAR", 143),
    ("EXTENDED_ARG", 144),
    ("LIST_APPEND", 145),
    ("SET_ADD", 146),
    ("MAP_ADD", 147),
    ("COPY_FREE_VARS", 149),
    ("YIELD_VALUE", 150),
    ("RESUME", 151),
    ("MATCH_CLASS", 152),
    ("FORMAT_VALUE", 155),
    ("BUILD_CONST_KEY_MAP", 156),
    ("BUILD_STRING", 157),
    ("LIST_EXTEND", 162),
    ("SET_UPDATE", 163),
    ("DICT_MERGE", 164),
    ("DICT_UPDATE", 165),
    ("CALL", 171),
    ("KW_NAMES", 172),
    ("CALL_INTRINSIC_1", 173),
    ("CALL_INTRINSIC_2", 174),
    ("LOAD_FROM_DICT_OR_GLOBALS", 175),
    ("LOAD_FROM_DICT_OR_DEREF", 176),
)


def _build_tables():
    mapping = {}
    names = ["<%d>" % i for i in range(256)]
    seen_codes = set()
    for n, c in _OPCODE_TABLE:
        if not isinstance(n, str) or not isinstance(c, int):
            raise ValueError("invalid opcode entry: %r" % ((n, c),))
        if c < 0 or c > 255:
            raise ValueError("opcode %r out of range: %d" % (n, c))
        if c in seen_codes:
            raise ValueError("duplicate opcode value: %d" % c)
        if n in mapping:
            raise ValueError("duplicate opcode name: %r" % n)
        seen_codes.add(c)
        mapping[n] = c
        names[c] = n
    return mapping, names


opmap, opname = _build_tables()

# Convenience constants
LOAD_CONST = opmap["LOAD_CONST"]
EXTENDED_ARG = opmap["EXTENDED_ARG"]
HAVE_ARGUMENT = 90  # Opcodes >= HAVE_ARGUMENT take an inline argument byte.


# Helpful classification sets (subset; useful for downstream consumers).
hasconst = frozenset({opmap["LOAD_CONST"], opmap["RETURN_CONST"]})
hasname = frozenset({
    opmap["STORE_NAME"], opmap["DELETE_NAME"], opmap["STORE_ATTR"],
    opmap["DELETE_ATTR"], opmap["STORE_GLOBAL"], opmap["DELETE_GLOBAL"],
    opmap["LOAD_NAME"], opmap["LOAD_ATTR"], opmap["IMPORT_NAME"],
    opmap["IMPORT_FROM"], opmap["LOAD_GLOBAL"], opmap["LOAD_SUPER_ATTR"],
    opmap["LOAD_FROM_DICT_OR_GLOBALS"],
})
hasjrel = frozenset({
    opmap["JUMP_FORWARD"], opmap["POP_JUMP_IF_FALSE"], opmap["POP_JUMP_IF_TRUE"],
    opmap["POP_JUMP_IF_NONE"], opmap["POP_JUMP_IF_NOT_NONE"],
    opmap["JUMP_BACKWARD"], opmap["JUMP_BACKWARD_NO_INTERRUPT"],
    opmap["FOR_ITER"], opmap["SEND"],
})
haslocal = frozenset({
    opmap["LOAD_FAST"], opmap["STORE_FAST"], opmap["DELETE_FAST"],
    opmap["LOAD_FAST_CHECK"], opmap["LOAD_FAST_AND_CLEAR"],
})
hasfree = frozenset({
    opmap["LOAD_DEREF"], opmap["STORE_DEREF"], opmap["DELETE_DEREF"],
    opmap["MAKE_CELL"], opmap["COPY_FREE_VARS"], opmap["LOAD_FROM_DICT_OR_DEREF"],
})
hascompare = frozenset({opmap["COMPARE_OP"]})


cmp_op = ("<", "<=", "==", "!=", ">", ">=")


# --- Invariant self-tests -------------------------------------------------

def opcode2_opmap():
    """Return True iff opmap is a well-formed name->code mapping."""
    if not isinstance(opmap, dict):
        return False
    if not opmap:
        return False
    seen = set()
    for name, code in opmap.items():
        if not isinstance(name, str) or not name:
            return False
        if not isinstance(code, int):
            return False
        if code < 0 or code > 255:
            return False
        if code in seen:
            return False
        seen.add(code)
    return "LOAD_CONST" in opmap and "EXTENDED_ARG" in opmap


def opcode2_opname():
    """Return True iff opname is a well-formed code->name list."""
    if not isinstance(opname, list):
        return False
    if len(opname) != 256:
        return False
    for entry in opname:
        if not isinstance(entry, str):
            return False
    # Round-trip: every name in opmap maps back through opname.
    for name, code in opmap.items():
        if opname[code] != name:
            return False
    return True


def opcode2_load_const():
    """Return True iff LOAD_CONST is consistently registered."""
    if "LOAD_CONST" not in opmap:
        return False
    code = opmap["LOAD_CONST"]
    if not isinstance(code, int) or code < 0 or code > 255:
        return False
    if opname[code] != "LOAD_CONST":
        return False
    if LOAD_CONST != code:
        return False
    if code not in hasconst:
        return False
    return True