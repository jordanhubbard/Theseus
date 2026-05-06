"""Clean-room implementation of a regex module for Theseus.

Implements pattern compilation, findall, and sub using a backtracking
regex engine built entirely from Python primitives.

The top-level ``re2_*`` functions are boolean predicates: they return
True when the operation succeeds (compiles / has matches / made
substitutions) and False otherwise.
"""

# ---------------------------------------------------------------------------
# Flag constants (numerically aligned with stdlib re for compatibility)
# ---------------------------------------------------------------------------
IGNORECASE = I = 2
MULTILINE = M = 8
DOTALL = S = 16
VERBOSE = X = 64


# ---------------------------------------------------------------------------
# Character class predicates
# ---------------------------------------------------------------------------
def _is_digit(c):
    return c.isdigit()


def _is_word(c):
    return c.isalnum() or c == '_'


def _is_space(c):
    return c in ' \t\n\r\f\v'


# ---------------------------------------------------------------------------
# Parser - produces a tree of tuples representing the regex AST
# ---------------------------------------------------------------------------
class _Parser:
    def __init__(self, pattern):
        self.pattern = pattern
        self.pos = 0
        self.group_count = 0

    def peek(self, offset=0):
        p = self.pos + offset
        if p < len(self.pattern):
            return self.pattern[p]
        return None

    def advance(self):
        c = self.pattern[self.pos]
        self.pos += 1
        return c

    def parse(self):
        tree = self.parse_alt()
        if self.pos != len(self.pattern):
            raise ValueError("unexpected character at position %d" % self.pos)
        return tree, self.group_count

    def parse_alt(self):
        branches = [self.parse_concat()]
        while self.peek() == '|':
            self.advance()
            branches.append(self.parse_concat())
        if len(branches) == 1:
            return branches[0]
        return ('alt', branches)

    def parse_concat(self):
        items = []
        while self.pos < len(self.pattern) and self.peek() not in ('|', ')'):
            items.append(self.parse_quant())
        if not items:
            return ('empty',)
        if len(items) == 1:
            return items[0]
        return ('concat', items)

    def parse_quant(self):
        atom = self.parse_atom()
        c = self.peek()
        if c in ('*', '+', '?'):
            self.advance()
            greedy = True
            if self.peek() == '?':
                self.advance()
                greedy = False
            if c == '*':
                return ('rep', atom, 0, -1, greedy)
            if c == '+':
                return ('rep', atom, 1, -1, greedy)
            return ('rep', atom, 0, 1, greedy)
        if c == '{':
            save = self.pos
            self.advance()
            num = ''
            while self.peek() and self.peek().isdigit():
                num += self.advance()
            if not num:
                self.pos = save
                return atom
            mn = int(num)
            mx = mn
            if self.peek() == ',':
                self.advance()
                num2 = ''
                while self.peek() and self.peek().isdigit():
                    num2 += self.advance()
                mx = int(num2) if num2 else -1
            if self.peek() != '}':
                self.pos = save
                return atom
            self.advance()
            greedy = True
            if self.peek() == '?':
                self.advance()
                greedy = False
            return ('rep', atom, mn, mx, greedy)
        return atom

    def parse_atom(self):
        c = self.peek()
        if c == '(':
            self.advance()
            if self.peek() == '?':
                self.advance()
                if self.peek() == ':':
                    self.advance()
                    inner = self.parse_alt()
                    if self.peek() != ')':
                        raise ValueError("expected )")
                    self.advance()
                    return inner
                raise ValueError("unsupported group syntax")
            self.group_count += 1
            idx = self.group_count
            inner = self.parse_alt()
            if self.peek() != ')':
                raise ValueError("expected )")
            self.advance()
            return ('group', idx, inner)
        if c == '[':
            return self.parse_charclass()
        if c == '.':
            self.advance()
            return ('any',)
        if c == '^':
            self.advance()
            return ('start_anchor',)
        if c == '$':
            self.advance()
            return ('end_anchor',)
        if c == '\\':
            self.advance()
            if self.pos >= len(self.pattern):
                raise ValueError("trailing backslash")
            esc = self.advance()
            return self._parse_escape(esc)
        if c is None:
            raise ValueError("unexpected end of pattern")
        self.advance()
        return ('lit', c)

    def _parse_escape(self, c):
        mapping = {
            'd': ('class_pred', _is_digit, False),
            'D': ('class_pred', _is_digit, True),
            'w': ('class_pred', _is_word, False),
            'W': ('class_pred', _is_word, True),
            's': ('class_pred', _is_space, False),
            'S': ('class_pred', _is_space, True),
            'b': ('wb',),
            'B': ('nwb',),
            'n': ('lit', '\n'),
            't': ('lit', '\t'),
            'r': ('lit', '\r'),
            'f': ('lit', '\f'),
            'v': ('lit', '\v'),
            'A': ('start_anchor',),
            'Z': ('end_anchor',),
        }
        if c in mapping:
            return mapping[c]
        if c.isdigit():
            return ('backref', int(c))
        return ('lit', c)

    def parse_charclass(self):
        self.advance()  # '['
        negated = False
        if self.peek() == '^':
            self.advance()
            negated = True
        items = []
        while self.peek() != ']':
            if self.pos >= len(self.pattern):
                raise ValueError("unterminated character class")
            c = self.advance()
            if c == '\\':
                if self.pos >= len(self.pattern):
                    raise ValueError("trailing backslash in class")
                e = self.advance()
                emap = {
                    'd': ('pred', _is_digit, False),
                    'D': ('pred', _is_digit, True),
                    'w': ('pred', _is_word, False),
                    'W': ('pred', _is_word, True),
                    's': ('pred', _is_space, False),
                    'S': ('pred', _is_space, True),
                    'n': ('char', '\n'),
                    't': ('char', '\t'),
                    'r': ('char', '\r'),
                    'f': ('char', '\f'),
                    'v': ('char', '\v'),
                }
                items.append(emap.get(e, ('char', e)))
            elif self.peek() == '-' and self.peek(1) and self.peek(1) != ']':
                self.advance()  # '-'
                end = self.advance()
                if end == '\\':
                    if self.pos >= len(self.pattern):
                        raise ValueError("bad escape")
                    end = self.advance()
                items.append(('range', c, end))
            else:
                items.append(('char', c))
        self.advance()  # ']'
        return ('class_set', items, negated)


def _class_set_match(items, c):
    for it in items:
        kind = it[0]
        if kind == 'char':
            if c == it[1]:
                return True
        elif kind == 'range':
            if it[1] <= c <= it[2]:
                return True
        elif kind == 'pred':
            f, negated = it[1], it[2]
            if f(c) != negated:
                return True
    return False


# ---------------------------------------------------------------------------
# Matching engine - generator based backtracking
# ---------------------------------------------------------------------------
def _match_at(node, s, pos, groups):
    kind = node[0]
    if kind == 'lit':
        if pos < len(s) and s[pos] == node[1]:
            yield pos + 1
        return
    if kind == 'any':
        if pos < len(s) and s[pos] != '\n':
            yield pos + 1
        return
    if kind == 'class_pred':
        f, negated = node[1], node[2]
        if pos < len(s) and (f(s[pos]) != negated):
            yield pos + 1
        return
    if kind == 'class_set':
        items, negated = node[1], node[2]
        if pos < len(s):
            m = _class_set_match(items, s[pos])
            if m != negated:
                yield pos + 1
        return
    if kind == 'start_anchor':
        if pos == 0:
            yield pos
        return
    if kind == 'end_anchor':
        if pos == len(s):
            yield pos
        return
    if kind == 'wb':
        before = pos > 0 and _is_word(s[pos - 1])
        after = pos < len(s) and _is_word(s[pos])
        if before != after:
            yield pos
        return
    if kind == 'nwb':
        before = pos > 0 and _is_word(s[pos - 1])
        after = pos < len(s) and _is_word(s[pos])
        if before == after:
            yield pos
        return
    if kind == 'empty':
        yield pos
        return
    if kind == 'concat':
        yield from _match_concat(node[1], 0, s, pos, groups)
        return
    if kind == 'alt':
        saved_outer = list(groups)
        for branch in node[1]:
            groups[:] = saved_outer
            for end in _match_at(branch, s, pos, groups):
                yield end
                groups[:] = saved_outer
        return
    if kind == 'rep':
        item, mn, mx, greedy = node[1], node[2], node[3], node[4]
        yield from _match_rep(item, mn, mx, greedy, s, pos, groups, 0)
        return
    if kind == 'group':
        idx, inner = node[1], node[2]
        saved = groups[idx]
        for end in _match_at(inner, s, pos, groups):
            groups[idx] = (pos, end)
            yield end
            groups[idx] = saved
        groups[idx] = saved
        return
    if kind == 'backref':
        idx = node[1]
        g = groups[idx] if idx < len(groups) else None
        if g is None:
            return
        text = s[g[0]:g[1]]
        if s[pos:pos + len(text)] == text:
            yield pos + len(text)
        return


def _match_concat(items, i, s, pos, groups):
    if i == len(items):
        yield pos
        return
    for end in _match_at(items[i], s, pos, groups):
        yield from _match_concat(items, i + 1, s, end, groups)


def _match_rep(item, mn, mx, greedy, s, pos, groups, count):
    if greedy:
        if mx == -1 or count < mx:
            saved = list(groups)
            for end in _match_at(item, s, pos, groups):
                if end > pos:
                    yield from _match_rep(item, mn, mx, greedy, s, end,
                                          groups, count + 1)
                groups[:] = saved
        if count >= mn:
            yield pos
    else:
        if count >= mn:
            yield pos
        if mx == -1 or count < mx:
            saved = list(groups)
            for end in _match_at(item, s, pos, groups):
                if end > pos:
                    yield from _match_rep(item, mn, mx, greedy, s, end,
                                          groups, count + 1)
                groups[:] = saved


# ---------------------------------------------------------------------------
# Match object
# ---------------------------------------------------------------------------
class _Match:
    def __init__(self, string, groups, pattern_obj=None):
        self.string = string
        self._groups = groups
        self.re = pattern_obj
        self.pos = 0
        self.endpos = len(string)

    def group(self, *args):
        if not args:
            args = (0,)
        if len(args) == 1:
            idx = args[0]
            if not isinstance(idx, int) or idx < 0 or idx >= len(self._groups):
                raise IndexError("no such group")
            g = self._groups[idx]
            if g is None:
                return None
            return self.string[g[0]:g[1]]
        return tuple(self.group(i) for i in args)

    def groups(self, default=None):
        result = []
        for i in range(1, len(self._groups)):
            g = self._groups[i]
            result.append(default if g is None else self.string[g[0]:g[1]])
        return tuple(result)

    def start(self, idx=0):
        if idx < 0 or idx >= len(self._groups):
            raise IndexError("no such group")
        g = self._groups[idx]
        return g[0] if g else -1

    def end(self, idx=0):
        if idx < 0 or idx >= len(self._groups):
            raise IndexError("no such group")
        g = self._groups[idx]
        return g[1] if g else -1

    def span(self, idx=0):
        return (self.start(idx), self.end(idx))

    def __bool__(self):
        return True

    def __repr__(self):
        return "<Match span=%r match=%r>" % (self.span(), self.group())


# ---------------------------------------------------------------------------
# Pattern object
# ---------------------------------------------------------------------------
class Pattern:
    def __init__(self, pattern, flags=0):
        self.pattern = pattern
        self.flags = flags
        parser = _Parser(pattern)
        self._tree, self._group_count = parser.parse()

    @property
    def groups(self):
        return self._group_count

    def _new_groups(self):
        return [None] * (self._group_count + 1)

    def _find_next(self, string, start, endpos):
        for j in range(start, endpos + 1):
            grps = self._new_groups()
            for end in _match_at(self._tree, string, j, grps):
                grps[0] = (j, end)
                return grps, j, end
        return None

    def search(self, string, pos=0, endpos=None):
        if endpos is None:
            endpos = len(string)
        s = string if endpos == len(string) else string[:endpos]
        result = self._find_next(s, pos, endpos)
        if result is None:
            return None
        groups, _start, _end = result
        return _Match(string, groups, self)

    def match(self, string, pos=0, endpos=None):
        if endpos is None:
            endpos = len(string)
        s = string if endpos == len(string) else string[:endpos]
        groups = self._new_groups()
        for end in _match_at(self._tree, s, pos, groups):
            groups[0] = (pos, end)
            return _Match(string, groups, self)
        return None

    def fullmatch(self, string, pos=0, endpos=None):
        if endpos is None:
            endpos = len(string)
        s = string if endpos == len(string) else string[:endpos]
        groups = self._new_groups()
        for end in _match_at(self._tree, s, pos, groups):
            if end == endpos:
                groups[0] = (pos, end)
                return _Match(string, groups, self)
        return None

    def findall(self, string, pos=0, endpos=None):
        if endpos is None:
            endpos = len(string)
        results = []
        i = pos
        while i <= endpos:
            found = self._find_next(string, i, endpos)
            if not found:
                break
            groups, start, end = found
            if self._group_count == 0:
                results.append(string[start:end])
            elif self._group_count == 1:
                g = groups[1]
                results.append(string[g[0]:g[1]] if g else '')
            else:
                results.append(tuple(
                    string[g[0]:g[1]] if g else ''
                    for g in groups[1:]
                ))
            i = end + 1 if end == start else end
        return results

    def finditer(self, string, pos=0, endpos=None):
        if endpos is None:
            endpos = len(string)
        i = pos
        while i <= endpos:
            found = self._find_next(string, i, endpos)
            if not found:
                break
            groups, start, end = found
            yield _Match(string, groups, self)
            i = end + 1 if end == start else end

    def sub(self, repl, string, count=0):
        return self.subn(repl, string, count)[0]

    def subn(self, repl, string, count=0):
        out = []
        i = 0
        endpos = len(string)
        n = 0
        last_end = 0
        while i <= endpos:
            if count and n >= count:
                break
            found = self._find_next(string, i, endpos)
            if not found:
                break
            groups, start, end = found
            out.append(string[last_end:start])
            if callable(repl):
                m = _Match(string, groups, self)
                out.append(repl(m))
            else:
                out.append(_expand_template(repl, groups, string))
            n += 1
            last_end = end
            if end == start:
                if end < endpos:
                    out.append(string[end])
                i = end + 1
                last_end = i
            else:
                i = end
        out.append(string[last_end:])
        return ''.join(out), n

    def split(self, string, maxsplit=0):
        results = []
        i = 0
        endpos = len(string)
        n = 0
        last_end = 0
        while i <= endpos:
            if maxsplit and n >= maxsplit:
                break
            found = self._find_next(string, i, endpos)
            if not found:
                break
            groups, start, end = found
            if start == end and start == last_end and i > 0:
                if end < endpos:
                    i = end + 1
                    continue
                break
            results.append(string[last_end:start])
            for g in groups[1:]:
                results.append(string[g[0]:g[1]] if g else None)
            last_end = end
            n += 1
            i = end + 1 if end == start else end
        results.append(string[last_end:])
        return results


# ---------------------------------------------------------------------------
# Replacement template expansion
# ---------------------------------------------------------------------------
def _expand_template(template, groups, string):
    out = []
    i = 0
    n = len(template)
    while i < n:
        c = template[i]
        if c == '\\':
            i += 1
            if i >= n:
                out.append('\\')
                break
            nc = template[i]
            if nc.isdigit():
                idx = int(nc)
                if idx < len(groups) and groups[idx]:
                    g = groups[idx]
                    out.append(string[g[0]:g[1]])
                i += 1
            elif nc == 'n':
                out.append('\n')
                i += 1
            elif nc == 't':
                out.append('\t')
                i += 1
            elif nc == 'r':
                out.append('\r')
                i += 1
            elif nc == 'f':
                out.append('\f')
                i += 1
            elif nc == 'v':
                out.append('\v')
                i += 1
            elif nc == '\\':
                out.append('\\')
                i += 1
            elif nc == 'g':
                if i + 1 < n and template[i + 1] == '<':
                    close = template.find('>', i + 2)
                    if close == -1:
                        out.append('\\g')
                        i += 1
                    else:
                        ref = template[i + 2:close]
                        if ref.isdigit():
                            idx = int(ref)
                            if idx < len(groups) and groups[idx]:
                                g = groups[idx]
                                out.append(string[g[0]:g[1]])
                        i = close + 1
                else:
                    out.append('\\g')
                    i += 1
            else:
                out.append('\\' + nc)
                i += 1
        else:
            out.append(c)
            i += 1
    return ''.join(out)


# ---------------------------------------------------------------------------
# Required public API — boolean predicates
# ---------------------------------------------------------------------------
def re2_compile(pattern='', flags=0):
    """Return True if ``pattern`` is a syntactically valid regex, else False."""
    try:
        Pattern(pattern, flags)
        return True
    except Exception:
        return False


def re2_findall(pattern='', string='', flags=0):
    """Return True if ``pattern`` finds at least one match in ``string``."""
    try:
        results = Pattern(pattern, flags).findall(string)
        return len(results) > 0
    except Exception:
        return False


def re2_sub(pattern='', repl='', string='', count=0, flags=0):
    """Return True if at least one substitution was performed, else False."""
    try:
        _result, n = Pattern(pattern, flags).subn(repl, string, count)
        return n > 0
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Convenience module-level aliases (mirror standard re module surface)
# ---------------------------------------------------------------------------
def compile(pattern, flags=0):
    return Pattern(pattern, flags)


def search(pattern, string, flags=0):
    return Pattern(pattern, flags).search(string)


def match(pattern, string, flags=0):
    return Pattern(pattern, flags).match(string)


def fullmatch(pattern, string, flags=0):
    return Pattern(pattern, flags).fullmatch(string)


def findall(pattern, string, flags=0):
    return Pattern(pattern, flags).findall(string)


def finditer(pattern, string, flags=0):
    return Pattern(pattern, flags).finditer(string)


def sub(pattern, repl, string, count=0, flags=0):
    return Pattern(pattern, flags).sub(repl, string, count)


def subn(pattern, repl, string, count=0, flags=0):
    return Pattern(pattern, flags).subn(repl, string, count)


def split(pattern, string, maxsplit=0, flags=0):
    return Pattern(pattern, flags).split(string, maxsplit)


__all__ = [
    're2_compile', 're2_findall', 're2_sub',
    'Pattern', 'compile', 'search', 'match', 'fullmatch',
    'findall', 'finditer', 'sub', 'subn', 'split',
    'IGNORECASE', 'I', 'MULTILINE', 'M', 'DOTALL', 'S', 'VERBOSE', 'X',
]