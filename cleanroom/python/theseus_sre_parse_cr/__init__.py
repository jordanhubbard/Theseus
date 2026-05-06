"""Clean-room re-implementation of selected sre_parse helpers.

This module exposes a tiny subset of behaviour modelled after CPython's
``sre_parse`` regular-expression parser.  The implementation is written from
scratch and does not import or wrap ``sre_parse``/``re``/``sre_compile``.
"""

# ---------------------------------------------------------------------------
# Token / opcode constants
# ---------------------------------------------------------------------------

LITERAL = "literal"
NOT_LITERAL = "not_literal"
ANY = "any"
IN = "in"
RANGE = "range"
CATEGORY = "category"
BRANCH = "branch"
SUBPATTERN = "subpattern"
MAX_REPEAT = "max_repeat"
MIN_REPEAT = "min_repeat"
AT = "at"
NEGATE = "negate"

AT_BEGINNING = "at_beginning"
AT_END = "at_end"
AT_BOUNDARY = "at_boundary"

CATEGORY_DIGIT = "category_digit"
CATEGORY_NOT_DIGIT = "category_not_digit"
CATEGORY_SPACE = "category_space"
CATEGORY_NOT_SPACE = "category_not_space"
CATEGORY_WORD = "category_word"
CATEGORY_NOT_WORD = "category_not_word"

MAXREPEAT = 4294967295  # mirrors sys.maxsize sentinel from sre_constants

ESCAPE_CATEGORIES = {
    "d": CATEGORY_DIGIT,
    "D": CATEGORY_NOT_DIGIT,
    "s": CATEGORY_SPACE,
    "S": CATEGORY_NOT_SPACE,
    "w": CATEGORY_WORD,
    "W": CATEGORY_NOT_WORD,
}

ESCAPE_LITERALS = {
    "n": ord("\n"),
    "r": ord("\r"),
    "t": ord("\t"),
    "f": ord("\f"),
    "v": ord("\v"),
    "a": ord("\a"),
    "b": ord("\b"),
    "0": 0,
}


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class error(Exception):
    """Raised for malformed regular-expression input."""

    def __init__(self, msg, pattern=None, pos=None):
        super().__init__(msg)
        self.msg = msg
        self.pattern = pattern
        self.pos = pos


# ---------------------------------------------------------------------------
# Parser state
# ---------------------------------------------------------------------------


class State:
    """Tracks bookkeeping shared across nested sub-patterns during parsing."""

    def __init__(self):
        self.flags = 0
        self.groups = 1  # group 0 is the whole match
        self.groupdict = {}
        self.grouprefpos = {}
        self.lookbehindgroups = None

    def opengroup(self, name=None):
        gid = self.groups
        self.groups += 1
        if name is not None:
            if not isinstance(name, str) or not name:
                raise error("bad group name")
            if name in self.groupdict:
                raise error("redefinition of group name %r" % name)
            self.groupdict[name] = gid
        return gid

    def closegroup(self, gid, p):
        # Hook kept for API parity; nothing extra required for our parser.
        return gid

    def checkgroup(self, gid):
        return 0 < gid < self.groups

    def checklookbehindgroup(self, gid, source):
        if self.lookbehindgroups is None:
            return
        if gid >= self.lookbehindgroups:
            raise error("cannot refer to an open group")


# Backwards compatible alias, mirroring the original module's name.
Pattern = State


# ---------------------------------------------------------------------------
# Sub-pattern container
# ---------------------------------------------------------------------------


class SubPattern:
    """Sequence of (opcode, argument) tuples representing a parsed pattern."""

    def __init__(self, state, data=None):
        self.state = state
        self.data = [] if data is None else list(data)
        self.width = None

    # ------------------------------------------------------------------
    # Container protocol
    # ------------------------------------------------------------------
    def __len__(self):
        return len(self.data)

    def __getitem__(self, index):
        if isinstance(index, slice):
            return SubPattern(self.state, self.data[index])
        return self.data[index]

    def __setitem__(self, index, value):
        self.data[index] = value

    def __delitem__(self, index):
        del self.data[index]

    def __iter__(self):
        return iter(self.data)

    def __bool__(self):
        return True  # a freshly built SubPattern is always truthy

    def __repr__(self):
        return "SubPattern(%r)" % (self.data,)

    # ------------------------------------------------------------------
    # Mutators / queries
    # ------------------------------------------------------------------
    def append(self, item):
        self.data.append(item)

    def extend(self, items):
        self.data.extend(items)

    def insert(self, index, item):
        self.data.insert(index, item)

    def getwidth(self):
        if self.width is not None:
            return self.width
        lo = 0
        hi = 0
        for op, av in self.data:
            if op is BRANCH:
                branches = av[1]
                if not branches:
                    blo, bhi = 0, 0
                else:
                    blo, bhi = MAXREPEAT, 0
                    for branch in branches:
                        i, j = branch.getwidth()
                        blo = min(blo, i)
                        bhi = max(bhi, j)
                lo += blo
                hi += bhi
            elif op is SUBPATTERN:
                _gid, _add, _sub, sub = av
                i, j = sub.getwidth()
                lo += i
                hi += j
            elif op is MAX_REPEAT or op is MIN_REPEAT:
                mn, mx, sub = av
                i, j = sub.getwidth()
                lo += i * mn
                if mx == MAXREPEAT or j == MAXREPEAT:
                    hi = MAXREPEAT
                else:
                    hi += j * mx
            elif op in (LITERAL, NOT_LITERAL, ANY, IN):
                lo += 1
                hi += 1
            elif op is AT:
                pass  # zero-width assertion
            else:
                lo += 0
        if hi > MAXREPEAT:
            hi = MAXREPEAT
        self.width = (min(lo, MAXREPEAT), hi)
        return self.width


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------


class _Tokenizer:
    def __init__(self, source):
        self.source = source
        self.pos = 0

    def peek(self, offset=0):
        idx = self.pos + offset
        if 0 <= idx < len(self.source):
            return self.source[idx]
        return ""

    def get(self):
        if self.pos >= len(self.source):
            return ""
        ch = self.source[self.pos]
        self.pos += 1
        return ch

    def match(self, ch):
        if self.peek() == ch:
            self.pos += 1
            return True
        return False

    def at_end(self):
        return self.pos >= len(self.source)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _parse_escape(tok, in_class=False):
    ch = tok.get()
    if ch == "":
        raise error("bogus escape (end of pattern)")
    if ch in ESCAPE_CATEGORIES:
        return (IN, [(CATEGORY, ESCAPE_CATEGORIES[ch])]) if not in_class else (
            CATEGORY,
            ESCAPE_CATEGORIES[ch],
        )
    if ch in ESCAPE_LITERALS:
        return (LITERAL, ESCAPE_LITERALS[ch])
    if ch == "A":
        return (AT, AT_BEGINNING)
    if ch == "Z":
        return (AT, AT_END)
    if ch == "x":
        hexdigits = ""
        for _ in range(2):
            c = tok.peek()
            if c and c in "0123456789abcdefABCDEF":
                hexdigits += c
                tok.get()
            else:
                break
        if not hexdigits:
            raise error("incomplete escape \\x")
        return (LITERAL, int(hexdigits, 16))
    if ch.isdigit():
        digits = ch
        while tok.peek().isdigit() and len(digits) < 3:
            digits += tok.get()
        return (LITERAL, int(digits, 8) if digits[0] == "0" else int(digits))
    return (LITERAL, ord(ch))


def _parse_class(tok):
    items = []
    if tok.match("^"):
        items.append((NEGATE, None))
    if tok.peek() == "]":
        items.append((LITERAL, ord(tok.get())))
    while True:
        ch = tok.peek()
        if ch == "":
            raise error("unterminated character set")
        if ch == "]":
            tok.get()
            break
        if ch == "\\":
            tok.get()
            items.append(_parse_escape(tok, in_class=True))
            continue
        tok.get()
        if tok.peek() == "-" and tok.peek(1) not in ("", "]"):
            tok.get()  # consume '-'
            end = tok.get()
            if end == "\\":
                esc = _parse_escape(tok, in_class=True)
                if esc[0] is LITERAL:
                    items.append((RANGE, (ord(ch), esc[1])))
                else:
                    items.append((LITERAL, ord(ch)))
                    items.append((LITERAL, ord("-")))
                    items.append(esc)
            else:
                items.append((RANGE, (ord(ch), ord(end))))
        else:
            items.append((LITERAL, ord(ch)))
    return (IN, items)


def _parse_repeat(tok):
    # We've already consumed '{'. Try to read {m,n} else treat as literal '{'.
    start_pos = tok.pos
    digits = ""
    while tok.peek().isdigit():
        digits += tok.get()
    mn = int(digits) if digits else None
    mx = mn
    if tok.match(","):
        digits2 = ""
        while tok.peek().isdigit():
            digits2 += tok.get()
        mx = int(digits2) if digits2 else MAXREPEAT
    if not tok.match("}"):
        # Roll back: not a real repeat specifier.
        tok.pos = start_pos
        return None
    if mn is None:
        mn = 0
    return mn, mx


def _parse_alternation(tok, state, nested):
    branches = [_parse_sequence(tok, state, nested)]
    while tok.peek() == "|":
        tok.get()
        branches.append(_parse_sequence(tok, state, nested))
    if len(branches) == 1:
        return branches[0]
    out = SubPattern(state)
    out.append((BRANCH, (None, branches)))
    return out


def _parse_sequence(tok, state, nested):
    seq = SubPattern(state)
    while True:
        ch = tok.peek()
        if ch == "" or ch == "|":
            break
        if nested and ch == ")":
            break
        if ch == "(":
            tok.get()
            name = None
            capture = True
            if tok.match("?"):
                if tok.match(":"):
                    capture = False
                elif tok.match("P"):
                    if tok.match("<"):
                        name_chars = []
                        while tok.peek() != ">":
                            if tok.at_end():
                                raise error("missing >, unterminated name")
                            name_chars.append(tok.get())
                        tok.get()  # consume '>'
                        name = "".join(name_chars)
                    else:
                        raise error("unknown extension ?P")
                else:
                    # Unsupported extension; treat as non-capturing best effort.
                    capture = False
            gid = state.opengroup(name) if capture else None
            inner = _parse_alternation(tok, state, nested=True)
            if not tok.match(")"):
                raise error("missing ), unterminated subpattern")
            if capture:
                state.closegroup(gid, inner)
                seq.append((SUBPATTERN, (gid, 0, 0, inner)))
            else:
                seq.extend(inner.data)
            _maybe_apply_quantifier(tok, seq)
            continue
        if ch == ")":
            break
        if ch == "^":
            tok.get()
            seq.append((AT, AT_BEGINNING))
            continue
        if ch == "$":
            tok.get()
            seq.append((AT, AT_END))
            continue
        if ch == ".":
            tok.get()
            seq.append((ANY, None))
            _maybe_apply_quantifier(tok, seq)
            continue
        if ch == "[":
            tok.get()
            seq.append(_parse_class(tok))
            _maybe_apply_quantifier(tok, seq)
            continue
        if ch == "\\":
            tok.get()
            seq.append(_parse_escape(tok, in_class=False))
            _maybe_apply_quantifier(tok, seq)
            continue
        # Literal character.
        tok.get()
        seq.append((LITERAL, ord(ch)))
        _maybe_apply_quantifier(tok, seq)
    return seq


def _maybe_apply_quantifier(tok, seq):
    if not seq.data:
        return
    ch = tok.peek()
    if ch not in ("*", "+", "?", "{"):
        return
    if ch == "{":
        save_pos = tok.pos
        tok.get()
        spec = _parse_repeat(tok)
        if spec is None:
            tok.pos = save_pos
            return
        mn, mx = spec
    elif ch == "*":
        tok.get()
        mn, mx = 0, MAXREPEAT
    elif ch == "+":
        tok.get()
        mn, mx = 1, MAXREPEAT
    else:  # '?'
        tok.get()
        mn, mx = 0, 1
    greedy = True
    if tok.match("?"):
        greedy = False
    last = seq.data.pop()
    sub = SubPattern(seq.state, [last])
    op = MAX_REPEAT if greedy else MIN_REPEAT
    seq.append((op, (mn, mx, sub)))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse(pattern, flags=0, state=None):
    """Parse *pattern* into a :class:`SubPattern` instance."""

    if not isinstance(pattern, str):
        raise TypeError("pattern must be a string")
    if state is None:
        state = State()
    state.flags = flags
    tok = _Tokenizer(pattern)
    parsed = _parse_alternation(tok, state, nested=False)
    if not tok.at_end():
        raise error("unbalanced parenthesis", pattern, tok.pos)
    return parsed


def parse_template(template, pattern_or_groups):
    """Parse a regex replacement *template* into ``(literals, groups)``.

    ``pattern_or_groups`` may be either a mapping describing named groups (or
    an integer giving the highest valid group number) or any object exposing a
    ``groups`` integer attribute / a ``groupindex`` mapping.
    """

    if hasattr(pattern_or_groups, "groupindex"):
        groupindex = dict(pattern_or_groups.groupindex)
        groups_count = getattr(pattern_or_groups, "groups", 0) + 1
    elif isinstance(pattern_or_groups, dict):
        groupindex = dict(pattern_or_groups)
        groups_count = max(groupindex.values(), default=0) + 1
    else:
        groupindex = {}
        groups_count = int(pattern_or_groups) + 1

    literals = []
    groups = []
    i = 0
    while i < len(template):
        ch = template[i]
        if ch != "\\":
            literals.append(ch)
            i += 1
            continue
        i += 1
        if i >= len(template):
            raise error("bad escape (end of pattern)")
        nxt = template[i]
        if nxt == "g":
            i += 1
            if i >= len(template) or template[i] != "<":
                raise error("missing < in group reference")
            i += 1
            end = template.find(">", i)
            if end == -1:
                raise error("missing > in group reference")
            name = template[i:end]
            i = end + 1
            if name.isdigit():
                gid = int(name)
            elif name in groupindex:
                gid = groupindex[name]
            else:
                raise error("unknown group name %r" % name)
            if gid >= groups_count:
                raise error("invalid group reference %d" % gid)
            groups.append((len(literals), gid))
            literals.append(None)
        elif nxt.isdigit():
            digits = nxt
            i += 1
            while i < len(template) and template[i].isdigit() and len(digits) < 2:
                digits += template[i]
                i += 1
            gid = int(digits)
            if gid >= groups_count:
                raise error("invalid group reference %d" % gid)
            groups.append((len(literals), gid))
            literals.append(None)
        elif nxt in ESCAPE_LITERALS:
            literals.append(chr(ESCAPE_LITERALS[nxt]))
            i += 1
        else:
            literals.append(nxt)
            i += 1
    return literals, groups


def expand_template(template, match):
    """Render *template* against a regex *match* object."""

    literals, groups = parse_template(template, match.re if hasattr(match, "re") else match)
    out = list(literals)
    for index, gid in groups:
        out[index] = match.group(gid) or ""
    return "".join(out)


# ---------------------------------------------------------------------------
# Invariant probes (clean-room markers)
# ---------------------------------------------------------------------------


def srep2_parse():
    """Smoke-test the parser end-to-end and return ``True`` if it works."""

    sp = parse("a(b|c)d*")
    if not isinstance(sp, SubPattern):
        return False
    if len(sp) == 0:
        return False
    # Confirm we have a SUBPATTERN node and a MAX_REPEAT node in the parse.
    ops = {item[0] for item in sp}
    if SUBPATTERN not in ops:
        return False
    if MAX_REPEAT not in ops:
        return False
    sp2 = parse("[abc]+")
    if len(sp2) != 1:
        return False
    return True


def srep2_state():
    """Verify :class:`State` allocates groups correctly."""

    state = State()
    if state.groups != 1:
        return False
    gid = state.opengroup("first")
    if gid != 1:
        return False
    if state.opengroup() != 2:
        return False
    if state.groupdict.get("first") != 1:
        return False
    if not state.checkgroup(1):
        return False
    if state.checkgroup(99):
        return False
    try:
        state.opengroup("first")
    except error:
        return True
    return False


def srep2_subpattern():
    """Verify :class:`SubPattern` container and width logic."""

    state = State()
    sp = SubPattern(state)
    if len(sp) != 0:
        return False
    sp.append((LITERAL, ord("a")))
    sp.append((ANY, None))
    if len(sp) != 2:
        return False
    if sp[0] != (LITERAL, ord("a")):
        return False
    lo, hi = sp.getwidth()
    if lo != 2 or hi != 2:
        return False
    sp2 = SubPattern(state, [(LITERAL, ord("x"))])
    sp2.append((MAX_REPEAT, (0, MAXREPEAT, SubPattern(state, [(LITERAL, ord("y"))]))))
    lo2, hi2 = sp2.getwidth()
    if lo2 != 1 or hi2 != MAXREPEAT:
        return False
    # Slicing should yield a fresh SubPattern.
    sliced = sp2[0:1]
    if not isinstance(sliced, SubPattern) or len(sliced) != 1:
        return False
    return True


__all__ = [
    "error",
    "State",
    "Pattern",
    "SubPattern",
    "parse",
    "parse_template",
    "expand_template",
    "MAXREPEAT",
    "LITERAL",
    "NOT_LITERAL",
    "ANY",
    "IN",
    "RANGE",
    "CATEGORY",
    "BRANCH",
    "SUBPATTERN",
    "MAX_REPEAT",
    "MIN_REPEAT",
    "AT",
    "NEGATE",
    "AT_BEGINNING",
    "AT_END",
    "AT_BOUNDARY",
    "CATEGORY_DIGIT",
    "CATEGORY_NOT_DIGIT",
    "CATEGORY_SPACE",
    "CATEGORY_NOT_SPACE",
    "CATEGORY_WORD",
    "CATEGORY_NOT_WORD",
    "srep2_parse",
    "srep2_state",
    "srep2_subpattern",
]