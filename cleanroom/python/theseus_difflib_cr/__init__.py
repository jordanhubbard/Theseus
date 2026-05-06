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

    def set_seq1(self, a):
        self.a = a
        self._matching_blocks = None

    def set_seq2(self, b):
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
        while (best_i + best_size < ahi and best_j + best_size < bhi
               and a[best_i + best_size] == b[best_j + best_size]):
            best_size += 1

        return best_i, best_j, best_size

    def find_longest_match(self, alo=0, ahi=None, blo=0, bhi=None):
        if ahi is None:
            ahi = len(self.a)
        if bhi is None:
            bhi = len(self.b)
        return self._find_longest_match(self.a, self.b, alo, ahi, blo, bhi)

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
        la, lb = len(self.a), len(self.b)
        if la + lb == 0:
            return 1.0
        return 2.0 * min(la, lb) / (la + lb)

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

    def get_grouped_opcodes(self, n=3):
        codes = self.get_opcodes()
        if not codes:
            codes = [('equal', 0, 1, 0, 1)]
        # trim leading/trailing equal blocks
        if codes[0][0] == 'equal':
            tag, i1, i2, j1, j2 = codes[0]
            codes[0] = (tag, max(i1, i2 - n), i2, max(j1, j2 - n), j2)
        if codes[-1][0] == 'equal':
            tag, i1, i2, j1, j2 = codes[-1]
            codes[-1] = (tag, i1, min(i2, i1 + n), j1, min(j2, j1 + n))
        nn = n + n
        group = []
        for tag, i1, i2, j1, j2 in codes:
            if tag == 'equal' and i2 - i1 > nn:
                group.append((tag, i1, min(i2, i1 + n), j1, min(j2, j1 + n)))
                yield group
                group = []
                i1, j1 = max(i1, i2 - n), max(j1, j2 - n)
            group.append((tag, i1, i2, j1, j2))
        if group and not (len(group) == 1 and group[0][0] == 'equal'):
            yield group


def get_close_matches(word, possibilities, n=3, cutoff=0.6):
    """Return a list of the best 'good enough' matches."""
    if n <= 0:
        raise ValueError("n must be > 0: %r" % (n,))
    if not (0.0 <= cutoff <= 1.0):
        raise ValueError("cutoff must be in [0.0, 1.0]: %r" % (cutoff,))
    result = []
    sm = SequenceMatcher()
    for x in possibilities:
        sm.set_seqs(word, x)
        score = sm.ratio()
        if score >= cutoff:
            result.append((score, x))
    result.sort(reverse=True)
    return [x for score, x in result[:n]]


def _format_range_unified(start, stop):
    beginning = start + 1
    length = stop - start
    if length == 1:
        return '{}'.format(beginning)
    if not length:
        beginning -= 1
    return '{},{}'.format(beginning, length)


def unified_diff(a, b, fromfile='', tofile='', fromfiledate='', tofiledate='',
                 n=3, lineterm='\n'):
    """Generate unified diff lines between a and b (sequences of strings)."""
    started = False
    for group in SequenceMatcher(a=a, b=b).get_grouped_opcodes(n):
        if not started:
            started = True
            fromdate = '\t{}'.format(fromfiledate) if fromfiledate else ''
            todate = '\t{}'.format(tofiledate) if tofiledate else ''
            yield '--- {}{}{}'.format(fromfile, fromdate, lineterm)
            yield '+++ {}{}{}'.format(tofile, todate, lineterm)
        first, last = group[0], group[-1]
        file1_range = _format_range_unified(first[1], last[2])
        file2_range = _format_range_unified(first[3], last[4])
        yield '@@ -{} +{} @@{}'.format(file1_range, file2_range, lineterm)
        for tag, i1, i2, j1, j2 in group:
            if tag == 'equal':
                for line in a[i1:i2]:
                    yield ' ' + line
                continue
            if tag in ('replace', 'delete'):
                for line in a[i1:i2]:
                    yield '-' + line
            if tag in ('replace', 'insert'):
                for line in b[j1:j2]:
                    yield '+' + line


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
    """get_close_matches('appel', [...]) includes 'apple'; returns True."""
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