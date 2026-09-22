# generation A recursive match

__all__ = [
    "SequenceMatcher",
    "get_close_matches",
    "IS_CHARACTER_JUNK",
    "IS_LINE_JUNK",
]


def IS_CHARACTER_JUNK(ch):
    return ch in (" ", "\t")


def IS_LINE_JUNK(line):
    if not line.strip():
        return True
    i = 0
    n = len(line)
    while i < n and line[i] in " \t":
        i += 1
    if i >= n or line[i] != "#":
        return False
    i += 1
    while i < n and line[i] in " \t":
        i += 1
    return i == n


def _recursive_match_count(a, b, alo, ahi, blo, bhi, isjunk):
    best_i = alo
    best_j = blo
    best_size = 0
    for i in range(alo, ahi):
        if isjunk is not None and isjunk(a[i]):
            continue
        for j in range(blo, bhi):
            if isjunk is not None and isjunk(b[j]):
                continue
            if a[i] != b[j]:
                continue
            k = 1
            while (
                i + k < ahi
                and j + k < bhi
                and a[i + k] == b[j + k]
                and not (
                    isjunk is not None
                    and (isjunk(a[i + k]) or isjunk(b[j + k]))
                )
            ):
                k += 1
            if k > best_size:
                best_i = i
                best_j = j
                best_size = k
    if best_size == 0:
        return 0
    left = _recursive_match_count(
        a, b, alo, best_i, blo, best_j, isjunk
    )
    right = _recursive_match_count(
        a,
        b,
        best_i + best_size,
        ahi,
        best_j + best_size,
        bhi,
        isjunk,
    )
    return best_size + left + right


def _element_counts(seq, isjunk):
    counts = {}
    for item in seq:
        if isjunk is not None and isjunk(item):
            continue
        counts[item] = counts.get(item, 0) + 1
    return counts


class SequenceMatcher(object):
    def __init__(self, isjunk=None, a="", b="", autojunk=True):
        self.isjunk = isjunk
        self.autojunk = autojunk
        self.a = a
        self.b = b
        self._match_count = None

    def _invalidate(self):
        self._match_count = None

    def set_seqs(self, a, b):
        self.a = a
        self.b = b
        self._invalidate()

    def set_seq1(self, a):
        self.a = a
        self._invalidate()

    def set_seq2(self, b):
        self.b = b
        self._invalidate()

    def _total_length(self):
        return len(self.a) + len(self.b)

    def _matching_elements(self):
        if self._match_count is None:
            self._match_count = _recursive_match_count(
                self.a,
                self.b,
                0,
                len(self.a),
                0,
                len(self.b),
                self.isjunk,
            )
        return self._match_count

    def ratio(self):
        total = self._total_length()
        if total == 0:
            return 1.0
        return 2.0 * self._matching_elements() / total

    def quick_ratio(self):
        total = self._total_length()
        if total == 0:
            return 1.0
        counts_a = _element_counts(self.a, self.isjunk)
        counts_b = _element_counts(self.b, self.isjunk)
        matches = 0
        for key, count_a in counts_a.items():
            count_b = counts_b.get(key, 0)
            if count_b:
                if count_a < count_b:
                    matches += count_a
                else:
                    matches += count_b
        return 2.0 * matches / total

    def real_quick_ratio(self):
        total = self._total_length()
        if total == 0:
            return 1.0
        la = len(self.a)
        lb = len(self.b)
        if la < lb:
            return 2.0 * la / total
        return 2.0 * lb / total


def get_close_matches(word, possibilities, n=3, cutoff=0.6):
    if not n:
        return []
    if n < 0:
        raise ValueError("n must be >= 0")
    if not 0.0 <= cutoff <= 1.0:
        raise ValueError("cutoff must be in [0.0, 1.0]")
    matcher = SequenceMatcher()
    matcher.set_seq2(word)
    scored = []
    for idx, possibility in enumerate(possibilities):
        matcher.set_seq1(possibility)
        score = matcher.ratio()
        if score >= cutoff:
            scored.append((score, idx, possibility))
    scored.sort(key=lambda item: (-item[0], item[1]))
    result = []
    for score, idx, possibility in scored[:n]:
        result.append(possibility)
    return result
