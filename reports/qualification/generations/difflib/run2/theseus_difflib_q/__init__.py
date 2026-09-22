# generation B dp table

__all__ = [
    "SequenceMatcher",
    "get_close_matches",
    "IS_CHARACTER_JUNK",
    "IS_LINE_JUNK",
]


def _calculate_ratio(matches, length):
    if length:
        return 2.0 * matches / length
    return 1.0


class SequenceMatcher:
    def __init__(self, isjunk=None, a="", b="", autojunk=True):
        self.isjunk = isjunk
        self.autojunk = autojunk
        self.a = None
        self.b = None
        self.b2j = {}
        self.bjunk = set()
        self.bpopular = set()
        self.matching_blocks = None
        self.fullbcount = None
        self.set_seqs(a, b)

    def set_seqs(self, a, b):
        self.set_seq1(a)
        self.set_seq2(b)

    def set_seq1(self, a):
        if a is self.a:
            return
        self.a = a
        self.matching_blocks = None

    def set_seq2(self, b):
        if b is self.b:
            return
        self.b = b
        self.matching_blocks = None
        self.fullbcount = None
        self._chain_b()

    def _chain_b(self):
        b2j = {}
        for index, element in enumerate(self.b):
            b2j.setdefault(element, []).append(index)

        self.bjunk = set()
        if self.isjunk is not None:
            for element in list(b2j):
                if self.isjunk(element):
                    self.bjunk.add(element)
                    del b2j[element]

        self.bpopular = set()
        if self.autojunk and len(self.b) >= 200:
            threshold = len(self.b) // 100 + 1
            for element, indexes in list(b2j.items()):
                if len(indexes) > threshold:
                    self.bpopular.add(element)
                    del b2j[element]
        self.b2j = b2j

    def _find_longest_match(self, alo, ahi, blo, bhi):
        rows = ahi - alo + 1
        columns = bhi - blo + 1
        table = [[0] * columns for unused in range(rows)]
        best_i = alo
        best_j = blo
        best_size = 0

        for row, i in enumerate(range(alo, ahi), 1):
            for column, j in enumerate(range(blo, bhi), 1):
                element = self.b[j]
                if (
                    self.a[i] == element
                    and element not in self.bjunk
                    and element not in self.bpopular
                ):
                    size = table[row - 1][column - 1] + 1
                    table[row][column] = size
                    start_i = i - size + 1
                    start_j = j - size + 1
                    if size > best_size:
                        best_i = start_i
                        best_j = start_j
                        best_size = size

        while (
            best_i > alo
            and best_j > blo
            and self.b[best_j - 1] not in self.bjunk
            and self.a[best_i - 1] == self.b[best_j - 1]
        ):
            best_i -= 1
            best_j -= 1
            best_size += 1
        while (
            best_i + best_size < ahi
            and best_j + best_size < bhi
            and self.b[best_j + best_size] not in self.bjunk
            and self.a[best_i + best_size] == self.b[best_j + best_size]
        ):
            best_size += 1
        while (
            best_i > alo
            and best_j > blo
            and self.b[best_j - 1] in self.bjunk
            and self.a[best_i - 1] == self.b[best_j - 1]
        ):
            best_i -= 1
            best_j -= 1
            best_size += 1
        while (
            best_i + best_size < ahi
            and best_j + best_size < bhi
            and self.b[best_j + best_size] in self.bjunk
            and self.a[best_i + best_size] == self.b[best_j + best_size]
        ):
            best_size += 1
        return best_i, best_j, best_size

    def _get_matching_blocks(self):
        if self.matching_blocks is not None:
            return self.matching_blocks

        pending = [(0, len(self.a), 0, len(self.b))]
        matches = []
        while pending:
            alo, ahi, blo, bhi = pending.pop()
            i, j, size = self._find_longest_match(alo, ahi, blo, bhi)
            if not size:
                continue
            matches.append((i, j, size))
            if alo < i and blo < j:
                pending.append((alo, i, blo, j))
            if i + size < ahi and j + size < bhi:
                pending.append((i + size, ahi, j + size, bhi))

        matches.sort()
        collapsed = []
        for i, j, size in matches:
            if collapsed:
                last_i, last_j, last_size = collapsed[-1]
                if last_i + last_size == i and last_j + last_size == j:
                    collapsed[-1] = (last_i, last_j, last_size + size)
                    continue
            collapsed.append((i, j, size))
        collapsed.append((len(self.a), len(self.b), 0))
        self.matching_blocks = collapsed
        return collapsed

    def ratio(self):
        matches = sum(block[2] for block in self._get_matching_blocks())
        return _calculate_ratio(matches, len(self.a) + len(self.b))

    def quick_ratio(self):
        if self.fullbcount is None:
            self.fullbcount = {}
            for element in self.b:
                self.fullbcount[element] = self.fullbcount.get(element, 0) + 1

        available = {}
        matches = 0
        for element in self.a:
            remaining = available.get(element)
            if remaining is None:
                remaining = self.fullbcount.get(element, 0)
            if remaining > 0:
                matches += 1
            available[element] = remaining - 1
        return _calculate_ratio(matches, len(self.a) + len(self.b))

    def real_quick_ratio(self):
        matches = min(len(self.a), len(self.b))
        return _calculate_ratio(matches, len(self.a) + len(self.b))


def get_close_matches(word, possibilities, n=3, cutoff=0.6):
    if n <= 0:
        raise ValueError("n must be > 0")
    if cutoff < 0.0 or cutoff > 1.0:
        raise ValueError("cutoff must be in [0.0, 1.0]")

    matcher = SequenceMatcher()
    matcher.set_seq2(word)
    scored = []
    for order, possibility in enumerate(possibilities):
        matcher.set_seq1(possibility)
        if (
            matcher.real_quick_ratio() >= cutoff
            and matcher.quick_ratio() >= cutoff
            and matcher.ratio() >= cutoff
        ):
            scored.append((matcher.ratio(), order, possibility))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [item[2] for item in scored[:n]]


def IS_CHARACTER_JUNK(ch):
    return ch in " \t"


def IS_LINE_JUNK(line):
    stripped = line.strip()
    return stripped == "" or stripped == "#"
