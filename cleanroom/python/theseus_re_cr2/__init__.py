"""
theseus_re_cr2 — Clean-room extended regex utilities.
No import of `re` or any third-party library.
"""

# ---------------------------------------------------------------------------
# Regex Engine — NFA-based (Thompson construction)
# ---------------------------------------------------------------------------

# Token types
_LITERAL   = 'LITERAL'
_DOT       = 'DOT'
_CHARCLASS = 'CHARCLASS'
_ANCHOR_S  = 'ANCHOR_S'   # ^
_ANCHOR_E  = 'ANCHOR_E'   # $

# NFA node types
_SPLIT  = 'SPLIT'
_MATCH  = 'MATCH'
_ATOM   = 'ATOM'
_EMPTY  = 'EMPTY'


class _NFAState:
    __slots__ = ('kind', 'atom', 'out1', 'out2', 'id')
    _counter = 0

    def __init__(self, kind, atom=None, out1=None, out2=None):
        self.kind = kind
        self.atom = atom   # (_LITERAL, ch) | (_DOT,) | (_CHARCLASS, set, negated)
        self.out1 = out1
        self.out2 = out2
        _NFAState._counter += 1
        self.id = _NFAState._counter

    def __repr__(self):
        return f'<NFAState {self.kind} id={self.id}>'


# A fragment is (start_state, list_of_dangling_out_slots)
# We use a list of (state, attr) pairs for dangling outputs.

class _Frag:
    __slots__ = ('start', 'outs')
    def __init__(self, start, outs):
        self.start = start
        self.outs  = outs  # list of [state, 'out1'|'out2']


def _patch(outs, state):
    for (s, attr) in outs:
        setattr(s, attr, state)


def _append_outs(a, b):
    return a + b


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

def _tokenize(pattern):
    """
    Yield tokens: each token is a tuple.
    Token types:
      ('LITERAL', ch)
      ('DOT',)
      ('CHARCLASS', frozenset_of_chars, negated:bool)
      ('ANCHOR_S',)
      ('ANCHOR_E',)
      ('OP', ch)   where ch in '|*+?(){'
      ('LBRACE', min, max)  for {m,n}
    """
    i = 0
    n = len(pattern)
    tokens = []
    while i < n:
        ch = pattern[i]
        if ch == '\\':
            i += 1
            if i >= n:
                raise ValueError("Trailing backslash in pattern")
            esc = pattern[i]
            if esc == 'd':
                chars = frozenset('0123456789')
                tokens.append(('CHARCLASS', chars, False))
            elif esc == 'D':
                chars = frozenset('0123456789')
                tokens.append(('CHARCLASS', chars, True))
            elif esc == 'w':
                chars = frozenset('abcdefghijklmnopqrstuvwxyz'
                                  'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                                  '0123456789_')
                tokens.append(('CHARCLASS', chars, False))
            elif esc == 'W':
                chars = frozenset('abcdefghijklmnopqrstuvwxyz'
                                  'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                                  '0123456789_')
                tokens.append(('CHARCLASS', chars, True))
            elif esc == 's':
                chars = frozenset(' \t\n\r\f\v')
                tokens.append(('CHARCLASS', chars, False))
            elif esc == 'S':
                chars = frozenset(' \t\n\r\f\v')
                tokens.append(('CHARCLASS', chars, True))
            elif esc == 'n':
                tokens.append(('LITERAL', '\n'))
            elif esc == 't':
                tokens.append(('LITERAL', '\t'))
            elif esc == 'r':
                tokens.append(('LITERAL', '\r'))
            else:
                tokens.append(('LITERAL', esc))
            i += 1
        elif ch == '[':
            i += 1
            negated = False
            if i < n and pattern[i] == '^':
                negated = True
                i += 1
            chars = set()
            # first char can be ] without closing
            first = True
            while i < n:
                c = pattern[i]
                if c == ']' and not first:
                    break
                first = False
                if c == '\\':
                    i += 1
                    if i >= n:
                        raise ValueError("Trailing backslash in char class")
                    esc = pattern[i]
                    if esc == 'd':
                        chars.update('0123456789')
                    elif esc == 'w':
                        chars.update('abcdefghijklmnopqrstuvwxyz'
                                     'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                                     '0123456789_')
                    elif esc == 's':
                        chars.update(' \t\n\r\f\v')
                    elif esc == 'n':
                        chars.add('\n')
                    elif esc == 't':
                        chars.add('\t')
                    elif esc == 'r':
                        chars.add('\r')
                    else:
                        chars.add(esc)
                    i += 1
                elif i + 2 < n and pattern[i+1] == '-' and pattern[i+2] != ']':
                    # range
                    start_ch = c
                    end_ch = pattern[i+2]
                    for code in range(ord(start_ch), ord(end_ch)+1):
                        chars.add(chr(code))
                    i += 3
                else:
                    chars.add(c)
                    i += 1
            if i >= n:
                raise ValueError("Unterminated character class")
            i += 1  # skip ']'
            tokens.append(('CHARCLASS', frozenset(chars), negated))
        elif ch == '.':
            tokens.append(('DOT',))
            i += 1
        elif ch == '^':
            tokens.append(('ANCHOR_S',))
            i += 1
        elif ch == '$':
            tokens.append(('ANCHOR_E',))
            i += 1
        elif ch in '|*+?()':
            tokens.append(('OP', ch))
            i += 1
        elif ch == '{':
            # try to parse {m} or {m,} or {m,n}
            j = i + 1
            num1 = ''
            while j < n and pattern[j].isdigit():
                num1 += pattern[j]
                j += 1
            if j < n and pattern[j] == '}' and num1:
                m = int(num1)
                tokens.append(('REPEAT', m, m))
                i = j + 1
            elif j < n and pattern[j] == ',' and num1:
                j += 1
                num2 = ''
                while j < n and pattern[j].isdigit():
                    num2 += pattern[j]
                    j += 1
                if j < n and pattern[j] == '}':
                    m = int(num1)
                    mx = int(num2) if num2 else None  # None = unlimited
                    tokens.append(('REPEAT', m, mx))
                    i = j + 1
                else:
                    tokens.append(('LITERAL', ch))
                    i += 1
            else:
                tokens.append(('LITERAL', ch))
                i += 1
        else:
            tokens.append(('LITERAL', ch))
            i += 1
    return tokens


# ---------------------------------------------------------------------------
# Parser / NFA builder  (recursive descent on token list)
# ---------------------------------------------------------------------------

class _Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def consume(self):
        t = self.tokens[self.pos]
        self.pos += 1
        return t

    def parse(self):
        frag = self.parse_alternation()
        match_state = _NFAState(_MATCH)
        _patch(frag.outs, match_state)
        return frag.start

    def parse_alternation(self):
        frag = self.parse_concatenation()
        while self.peek() == ('OP', '|'):
            self.consume()
            frag2 = self.parse_concatenation()
            split = _NFAState(_SPLIT, out1=frag.start, out2=frag2.start)
            outs = _append_outs(frag.outs, frag2.outs)
            frag = _Frag(split, outs)
        return frag

    def parse_concatenation(self):
        frags = []
        while True:
            t = self.peek()
            if t is None or t == ('OP', '|') or t == ('OP', ')'):
                break
            f = self.parse_quantified()
            frags.append(f)
        if not frags:
            # empty — epsilon
            s = _NFAState(_EMPTY)
            return _Frag(s, [(s, 'out1')])
        # chain them
        result = frags[0]
        for f in frags[1:]:
            _patch(result.outs, f.start)
            result = _Frag(result.start, f.outs)
        return result

    def parse_quantified(self):
        frag = self.parse_atom()
        t = self.peek()
        if t == ('OP', '*'):
            self.consume()
            return self._make_star(frag)
        elif t == ('OP', '+'):
            self.consume()
            return self._make_plus(frag)
        elif t == ('OP', '?'):
            self.consume()
            return self._make_question(frag)
        elif t is not None and t[0] == 'REPEAT':
            self.consume()
            m, mx = t[1], t[2]
            return self._make_repeat(frag, m, mx)
        return frag

    def _make_star(self, frag):
        split = _NFAState(_SPLIT, out1=frag.start)
        _patch(frag.outs, split)
        return _Frag(split, [(split, 'out2')])

    def _make_plus(self, frag):
        split = _NFAState(_SPLIT, out1=frag.start)
        _patch(frag.outs, split)
        return _Frag(frag.start, [(split, 'out2')])

    def _make_question(self, frag):
        split = _NFAState(_SPLIT, out1=frag.start)
        return _Frag(split, [(split, 'out2')] + frag.outs)

    def _make_repeat(self, frag, m, mx):
        # We need to rebuild the fragment m times (and optionally more)
        # Since we can't clone NFA states easily, we re-parse.
        # Instead, we'll build by chaining copies via re-tokenizing.
        # Actually we need to duplicate the fragment structure.
        # Simplest: build a new NFA by duplicating states.
        # We'll use a helper that deep-copies a fragment.
        
        # Build m mandatory copies + (mx-m) optional copies
        # We need the original token sequence for the atom — store it.
        # This approach: we'll just build it from the stored atom tokens.
        # 
        # Since we don't have the original tokens for just this atom,
        # we'll do structural duplication.
        
        copies = [frag] + [_dup_frag(frag) for _ in range(max(m + (0 if mx is None else mx) - 1, m - 1))]
        
        if m == 0 and mx is None:
            return self._make_star(frag)
        
        idx = 0
        # mandatory part
        if m == 0:
            # start with an empty that can skip
            base_start = _NFAState(_EMPTY)
            base_outs = [(base_start, 'out1')]
            result = _Frag(base_start, base_outs)
            mandatory_end_outs = base_outs
        else:
            result = copies[idx]; idx += 1
            for _ in range(m - 1):
                c = copies[idx]; idx += 1
                _patch(result.outs, c.start)
                result = _Frag(result.start, c.outs)
            mandatory_end_outs = result.outs

        if mx is None:
            # unlimited: add a star at the end
            last = _dup_frag(frag)
            star = self._make_star(last)
            _patch(mandatory_end_outs, star.start)
            result = _Frag(result.start, star.outs)
        else:
            # optional copies
            opt_count = mx - m
            all_outs = list(mandatory_end_outs)
            current_outs = mandatory_end_outs
            for _ in range(opt_count):
                c = copies[idx] if idx < len(copies) else _dup_frag(frag)
                idx += 1
                q = self._make_question_from(c)
                _patch(current_outs, q.start)
                # q.outs includes the bypass and the end of c
                all_outs = q.outs
                current_outs = q.outs
            result = _Frag(result.start, all_outs)

        return result

    def _make_question_from(self, frag):
        split = _NFAState(_SPLIT, out1=frag.start)
        return _Frag(split, [(split, 'out2')] + frag.outs)

    def parse_atom(self):
        t = self.peek()
        if t is None:
            raise ValueError("Expected atom")
        if t[0] == 'LITERAL':
            self.consume()
            s = _NFAState(_ATOM, atom=t)
            return _Frag(s, [(s, 'out1')])
        elif t[0] == 'DOT':
            self.consume()
            s = _NFAState(_ATOM, atom=t)
            return _Frag(s, [(s, 'out1')])
        elif t[0] == 'CHARCLASS':
            self.consume()
            s = _NFAState(_ATOM, atom=t)
            return _Frag(s, [(s, 'out1')])
        elif t[0] == 'ANCHOR_S':
            self.consume()
            s = _NFAState(_ATOM, atom=t)
            return _Frag(s, [(s, 'out1')])
        elif t[0] == 'ANCHOR_E':
            self.consume()
            s = _NFAState(_ATOM, atom=t)
            return _Frag(s, [(s, 'out1')])
        elif t == ('OP', '('):
            self.consume()
            frag = self.parse_alternation()
            if self.peek() != ('OP', ')'):
                raise ValueError("Expected ')'")
            self.consume()
            return frag
        else:
            raise ValueError(f"Unexpected token: {t}")


def _dup_frag(frag):
    """Deep-copy an NFA fragment, returning a new independent fragment."""
    mapping = {}

    def dup_state(s):
        if s is None:
            return None
        if id(s) in mapping:
            return mapping[id(s)]
        # Create new state (without recursing yet to avoid infinite loops)
        ns = _NFAState(s.kind, atom=s.atom)
        mapping[id(s)] = ns
        ns.out1 = dup_state(s.out1)
        ns.out2 = dup_state(s.out2)
        return ns

    new_start = dup_state(frag.start)
    new_outs = []
    for (s, attr) in frag.outs:
        new_s = mapping.get(id(s))
        if new_s is None:
            new_s = dup_state(s)
        new_outs.append((new_s, attr))
    return _Frag(new_start, new_outs)


# ---------------------------------------------------------------------------
# NFA simulation (Thompson's algorithm)
# ---------------------------------------------------------------------------

def _add_state(states, state, visited):
    """Add state to set, following epsilon transitions."""
    if state is None or id(state) in visited:
        return
    visited.add(id(state))
    if state.kind == _SPLIT:
        _add_state(states, state.out1, visited)
        _add_state(states, state.out2, visited)
    elif state.kind == _EMPTY:
        _add_state(states, state.out1, visited)
    else:
        states.append(state)


def _start_states(start):
    states = []
    _add_state(states, start, set())
    return states


def _atom_matches(atom, ch, pos, string):
    """Check if atom matches character ch at position pos in string."""
    kind = atom[0]
    if kind == 'LITERAL':
        return ch == atom[1]
    elif kind == 'DOT':
        return ch != '\n'
    elif kind == 'CHARCLASS':
        _, chars, negated = atom
        in_set = ch in chars
        return (not in_set) if negated else in_set
    elif kind == 'ANCHOR_S':
        # ^ matches at start of string or after newline
        return pos == 0 or (pos > 0 and string[pos-1] == '\n')
    elif kind == 'ANCHOR_E':
        # $ matches at end of string or before newline
        return pos == len(string) or (pos < len(string) and string[pos] == '\n')
    return False


def _is_anchor(atom):
    return atom[0] in ('ANCHOR_S', 'ANCHOR_E')


def _simulate(start, string, begin):
    """
    Try to match NFA starting at position `begin` in `string`.
    Returns end position of match, or -1 if no match.
    Uses leftmost-longest (greedy) semantics via Thompson simulation.
    """
    current = _start_states(start)
    last_match = -1
    pos = begin

    # Check for match in initial states (zero-length match possible)
    for s in current:
        if s.kind == _MATCH:
            last_match = pos
            break

    # Handle anchors in initial states
    # We need to process anchor states specially
    # Actually anchors are zero-width — handle them during state expansion

    while pos <= len(string):
        if not current:
            break

        # Check anchors at current position
        # Anchors are in current states — they match zero-width
        # We need to handle them: if an anchor state matches, follow its out1
        # This is done in _add_state by treating anchors as epsilon if they match

        # Actually, let's handle anchors properly:
        # Re-expand current states considering anchors at this position
        current = _expand_anchors(current, pos, string)

        # Check for match
        for s in current:
            if s.kind == _MATCH:
                last_match = pos
                break

        if pos == len(string):
            break

        ch = string[pos]
        next_states = []
        visited = set()
        for s in current:
            if s.kind == _ATOM and not _is_anchor(s.atom):
                if _atom_matches(s.atom, ch, pos, string):
                    _add_state(next_states, s.out1, visited)

        current = next_states
        pos += 1

        # Check for match after advancing
        for s in current:
            if s.kind == _MATCH:
                last_match = pos
                break

    return last_match


def _expand_anchors(states, pos, string):
    """
    Given a list of states, expand any anchor states that match at pos.
    Returns new list with anchors replaced by their successors.
    """
    result = []
    visited = set()
    
    def add(s):
        if s is None or id(s) in visited:
            return
        visited.add(id(s))
        if s.kind == _SPLIT:
            add(s.out1)
            add(s.out2)
        elif s.kind == _EMPTY:
            add(s.out1)
        elif s.kind == _ATOM and _is_anchor(s.atom):
            # Check if anchor matches at pos
            if s.atom[0] == 'ANCHOR_S':
                matches = (pos == 0 or (pos > 0 and string[pos-1] == '\n'))
            else:  # ANCHOR_E
                matches = (pos == len(string) or 
                          (pos < len(string) and string[pos] == '\n'))
            if matches:
                add(s.out1)
            # else: anchor doesn't match, don't add
        else:
            result.append(s)
    
    for s in states:
        add(s)
    
    return result


# ---------------------------------------------------------------------------
# Pattern class
# ---------------------------------------------------------------------------

class Pattern:
    def __init__(self, pattern, flags=0):
        self.pattern = pattern
        self.flags = flags
        tokens = _tokenize(pattern)
        parser = _Parser(tokens)
        self._start = parser.parse()

    def _find_match(self, string, begin=0):
        """Find first match at or after `begin`. Returns (start, end) or None."""
        for i in range(begin, len(string) + 1):
            end = _simulate(self._start, string, i)
            if end != -1:
                return (i, end)
        return None

    def findall(self, string):
        """Return list of all non-overlapping matches."""
        results = []
        pos = 0
        while pos <= len(string):
            end = _simulate(self._start, string, pos)
            if end == -1:
                pos += 1
                continue
            results.append(string[pos:end])
            if end == pos:
                # zero-length match — advance by 1 to avoid infinite loop
                pos += 1
            else:
                pos = end
        return results

    def sub(self, repl, string):
        """Replace all matches with repl."""
        result = []
        pos = 0
        while pos <= len(string):
            end = _simulate(self._start, string, pos)
            if end == -1:
                if pos < len(string):
                    result.append(string[pos])
                pos += 1
                continue
            result.append(repl)
            if end == pos:
                if pos < len(string):
                    result.append(string[pos])
                pos += 1
            else:
                pos = end
        return ''.join(result)

    def split(self, string):
        """Split string at pattern matches."""
        parts = []
        pos = 0
        last = 0
        while pos <= len(string):
            end = _simulate(self._start, string, pos)
            if end == -1:
                pos += 1
                continue
            parts.append(string[last:pos])
            if end == pos:
                pos += 1
            else:
                pos = end
            last = pos
        parts.append(string[last:])
        return parts

    def match(self, string, pos=0):
        """Match at beginning of string (or pos)."""
        end = _simulate(self._start, string, pos)
        if end == -1:
            return None
        return _MatchObject(string, pos, end)

    def search(self, string, pos=0):
        """Search for first match anywhere in string."""
        for i in range(pos, len(string) + 1):
            end = _simulate(self._start, string, i)
            if end != -1:
                return _MatchObject(string, i, end)
        return None

    def __repr__(self):
        return f'Pattern({self.pattern!r})'


class _MatchObject:
    def __init__(self, string, start, end):
        self._string = string
        self._start = start
        self._end = end

    def group(self, n=0):
        if n == 0:
            return self._string[self._start:self._end]
        raise IndexError("No groups")

    def start(self, n=0):
        return self._start

    def end(self, n=0):
        return self._end

    def span(self, n=0):
        return (self._start, self._end)


# ---------------------------------------------------------------------------
# Module-level API
# ---------------------------------------------------------------------------

def compile(pattern, flags=0):
    """Compile a regex pattern into a Pattern object."""
    return Pattern(pattern, flags)


def sub(pattern, repl, string, flags=0):
    """Replace all matches of pattern in string with repl."""
    return compile(pattern, flags).sub(repl, string)


def findall(pattern, string, flags=0):
    """Return list of all non-overlapping matches of pattern in string."""
    return compile(pattern, flags).findall(string)


def split(pattern, string, flags=0):
    """Split string by occurrences of pattern."""
    return compile(pattern, flags).split(string)


# ---------------------------------------------------------------------------
# Invariant test functions
# ---------------------------------------------------------------------------

def re_cr2_sub():
    """re.sub('a', 'b', 'banana') == 'bbnbnb'"""
    return sub('a', 'b', 'banana')


def re_cr2_findall():
    """re.findall('[0-9]+', 'a1b22c333') == ['1','22','333']"""
    return findall('[0-9]+', 'a1b22c333')


def re_cr2_split():
    """re.split('[,;]', 'a,b;c') == ['a','b','c']"""
    return split('[,;]', 'a,b;c')


# ---------------------------------------------------------------------------
# Self-test (runs on import in debug mode — disabled by default)
# ---------------------------------------------------------------------------

def _self_test():
    assert re_cr2_sub()     == 'bbnbnb',          f"sub failed: {re_cr2_sub()!r}"
    assert re_cr2_findall() == ['1', '22', '333'], f"findall failed: {re_cr2_findall()!r}"
    assert re_cr2_split()   == ['a', 'b', 'c'],   f"split failed: {re_cr2_split()!r}"
    print("All self-tests passed.")


if __name__ == '__main__':
    _self_test()