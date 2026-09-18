"""
theseus_difflib_q — Clean-room sequence comparison helpers.
Do NOT import difflib.
"""


class SequenceMatcher(object):
    def __init__(self, isjunk=None, a="", b="", autojunk=True):
        self.isjunk = isjunk
        self.a = a
        self.b = b
        self.autojunk = autojunk

    def set_seqs(self, a, b):
        self.a = a
        self.b = b

    def _longest(self, alo, ahi, blo, bhi):
        a = self.a
        b = self.b
        best_i = alo
        best_j = blo
        best_size = 0
        j_map = {}
        for j in range(blo, bhi):
            j_map.setdefault(b[j], []).append(j)
        for i in range(alo, ahi):
            elem = a[i]
            for j in j_map.get(elem, ()):
                k = 0
                while i + k < ahi and j + k < bhi and a[i + k] == b[j + k]:
                    k += 1
                if k > best_size:
                    best_i, best_j, best_size = i, j, k
        return best_i, best_j, best_size

    def get_matching_blocks(self):
        a = self.a
        b = self.b
        queue = [(0, len(a), 0, len(b))]
        matches = []
        while queue:
            alo, ahi, blo, bhi = queue.pop()
            i, j, size = self._longest(alo, ahi, blo, bhi)
            if size:
                matches.append((i, j, size))
                if alo < i and blo < j:
                    queue.append((alo, i, blo, j))
                if i + size < ahi and j + size < bhi:
                    queue.append((i + size, ahi, j + size, bhi))
        matches.sort()
        collapsed = []
        for i, j, size in matches:
            if collapsed:
                ci, cj, cs = collapsed[-1]
                if i == ci + cs and j == cj + cs:
                    collapsed[-1] = (ci, cj, cs + size)
                    continue
            collapsed.append((i, j, size))
        collapsed.append((len(a), len(b), 0))
        return collapsed

    def find_longest_match(self, alo=0, ahi=None, blo=0, bhi=None):
        if ahi is None:
            ahi = len(self.a)
        if bhi is None:
            bhi = len(self.b)
        i, j, size = self._longest(alo, ahi, blo, bhi)

        class Match(object):
            pass

        m = Match()
        m.a = i
        m.b = j
        m.size = size
        return m

    def ratio(self):
        matches = sum(size for _i, _j, size in self.get_matching_blocks())
        total = len(self.a) + len(self.b)
        if total == 0:
            return 1.0
        return (2.0 * matches) / total

    def quick_ratio(self):
        return self.ratio()

    def real_quick_ratio(self):
        la = len(self.a)
        lb = len(self.b)
        if la + lb == 0:
            return 1.0
        return (2.0 * min(la, lb)) / (la + lb)


def get_close_matches(word, possibilities, n=3, cutoff=0.6):
    scored = []
    for cand in possibilities:
        ratio = SequenceMatcher(None, word, cand).ratio()
        if ratio >= cutoff:
            scored.append((ratio, cand))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [cand for _ratio, cand in scored[:n]]


def IS_CHARACTER_JUNK(ch, ws=" \t"):
    return ch in ws


def IS_LINE_JUNK(line, pat=None):
    stripped = line.strip()
    return stripped == "" or stripped == "#"


__all__ = [
    "SequenceMatcher",
    "get_close_matches",
    "IS_CHARACTER_JUNK",
    "IS_LINE_JUNK",
]
