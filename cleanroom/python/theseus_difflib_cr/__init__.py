"""
theseus_difflib_cr — Clean-room difflib module.
No import of the standard `difflib` module.
"""


class SequenceMatcher:
    """Compute similarity between two sequences."""

    def __init__(self, isjunk=None, a='', b='', autojunk=True):
        self.isjunk = isjunk
        self.a = a
        self.b = b
        self._matching_blocks = None

    def set_seqs(self, a, b):
        self.a = a
        self.b = b
        self._matching_blocks = None

    def get_matching_blocks(self):
        if self._matching_blocks is not None:
            return self._matching_blocks
        self._matching_blocks = list(self._find_matching_blocks(
            self.a, self.b, 0, len(self.a), 0, len(self.b)))
        self._matching_blocks.append((len(self.a), len(self.b), 0))
        return self._matching_blocks

    def _find_longest_match(self, a, b, alo, ahi, blo, bhi):
        b_index = {}
        for i in range(blo, bhi):
            elem = b[i]
            if elem not in b_index:
                b_index[elem] = []
            b_index[elem].append(i)

        best_i = alo
        best_j = blo
        best_size = 0
        j2len = {}

        for i in range(alo, ahi):
            new_j2len = {}
            for j in b_index.get(a[i], []):
                if j < blo:
                    continue
                if j >= bhi:
                    break
                k = new_j2len[j] = j2len.get(j - 1, 0) + 1
                if k > best_size:
                    best_i, best_j, best_size = i - k + 1, j - k + 1, k
            j2len = new_j2len

        while best_i > alo and best_j > blo and a[best_i - 1] == b[best_j - 1]:
            best_i -= 1
            best_j -= 1
            best_size += 1
        while best_i + best_size < ahi and best_j + best_size < bhi and a[best_i + best_size] == b[best_j + best_size]:
            best_size += 1

        return best_i, best_j, best_size

    def _find_matching_blocks(self, a, b, alo, ahi, blo, bhi):
        i, j, k = self._find_longest_match(a, b, alo, ahi, blo, bhi)
        if k:
            if alo < i and blo < j:
                yield from self._find_matching_blocks(a, b, alo, i, blo, j)
            yield i, j, k
            if i + k < ahi and j + k < bhi:
                yield from self._find_matching_blocks(a, b, i + k, ahi, j + k, bhi)

    def ratio(self):
        matches = sum(n for i, j, n in self.get_matching_blocks())
        total = len(self.a) + len(self.b)
        if total == 0:
            return 1.0
        return 2.0 * matches / total

    def quick_ratio(self):
        return self.ratio()

    def real_quick_ratio(self):
        return self.ratio()

    def get_opcodes(self):
        opcodes = []
        i = j = 0
        for ai, bj, size in self.get_matching_blocks():
            tag = ''
            if i < ai and j < bj:
                tag = 'replace'
            elif i < ai:
                tag = 'delete'
            elif j < bj:
                tag = 'insert'
            if tag:
                opcodes.append((tag, i, ai, j, bj))
            if size:
                opcodes.append(('equal', ai, ai + size, bj, bj + size))
            i = ai + size
            j = bj + size
        return opcodes


def get_close_matches(word, possibilities, n=3, cutoff=0.6):
    """Return a list of the best 'good enough' matches."""
    if not (0.0 <= cutoff <= 1.0):
        raise ValueError(f"cutoff must be in [0.0, 1.0]: {cutoff!r}")
    result = []
    sm = SequenceMatcher()
    sm.set_seqs(word, word)
    for x in possibilities:
        sm.set_seqs(word, x)
        score = sm.ratio()
        if score >= cutoff:
            result.append((score, x))
    result.sort(reverse=True)
    return [x for score, x in result[:n]]


def unified_diff(a, b, fromfile='', tofile='', fromfiledate='', tofiledate='',
                 n=3, lineterm='\n'):
    """Generate unified diff lines between a and b (sequences of strings)."""
    sm = SequenceMatcher(a=a, b=b)
    opcodes = sm.get_opcodes()

    # Yield header
    if fromfile or tofile:
        yield f'--- {fromfile}\t{fromfiledate}{lineterm}'
        yield f'+++ {tofile}\t{tofiledate}{lineterm}'

    for group in _group_opcodes(opcodes, n):
        first, last = group[0], group[-1]
        i1, i2, j1, j2 = first[1], last[2], first[3], last[4]
        yield f'@@ -{i1 + 1},{i2 - i1} +{j1 + 1},{j2 - j1} @@{lineterm}'
        for tag, i1, i2, j1, j2 in group:
            if tag == 'equal':
                for line in a[i1:i2]:
                    yield ' ' + line
            if tag in ('replace', 'delete'):
                for line in a[i1:i2]:
                    yield '-' + line
            if tag in ('replace', 'insert'):
                for line in b[j1:j2]:
                    yield '+' + line


def _group_opcodes(opcodes, n=3):
    """Group opcodes into hunks with context."""
    groups = []
    group = []
    for tag, i1, i2, j1, j2 in opcodes:
        if tag == 'equal':
            if i2 - i1 > 2 * n:
                group.append((tag, i1, min(i2, i1 + n), j1, min(j2, j1 + n)))
                groups.append(group)
                group = []
                i1, j1 = max(i1, i2 - n), max(j1, j2 - n)
            group.append((tag, i1, i2, j1, j2))
        else:
            group.append((tag, i1, i2, j1, j2))
    if group and not (len(group) == 1 and group[0][0] == 'equal'):
        groups.append(group)
    return groups


def ndiff(a, b, linejunk=None, charjunk=None):
    """Compare a and b, returning delta lines."""
    sm = SequenceMatcher(a=a, b=b)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            for line in a[i1:i2]:
                yield '  ' + line
        elif tag == 'replace':
            for line in a[i1:i2]:
                yield '- ' + line
            for line in b[j1:j2]:
                yield '+ ' + line
        elif tag == 'delete':
            for line in a[i1:i2]:
                yield '- ' + line
        elif tag == 'insert':
            for line in b[j1:j2]:
                yield '+ ' + line


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def difflib2_ratio():
    """SequenceMatcher('abc','abc').ratio() == 1.0; returns 1.0."""
    sm = SequenceMatcher(a='abc', b='abc')
    return sm.ratio()


def difflib2_close_matches():
    """get_close_matches('appel', ['ape','apple','peach']) includes 'apple'; returns True."""
    result = get_close_matches('appel', ['ape', 'apple', 'peach'])
    return 'apple' in result


def difflib2_unified_diff():
    """unified_diff on changed lines yields diff output; returns True."""
    a = ['line1\n', 'line2\n', 'line3\n']
    b = ['line1\n', 'changed\n', 'line3\n']
    diff = list(unified_diff(a, b, fromfile='a.txt', tofile='b.txt'))
    return len(diff) > 0


__all__ = [
    'SequenceMatcher', 'get_close_matches', 'unified_diff', 'ndiff',
    'difflib2_ratio', 'difflib2_close_matches', 'difflib2_unified_diff',
]
