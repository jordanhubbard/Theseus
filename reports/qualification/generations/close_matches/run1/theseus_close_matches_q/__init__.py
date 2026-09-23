# generation A close scan

import heapq

__all__ = ["get_close_matches"]


def _find_longest_match(a, alo, ahi, b, blo, bhi):
    best_i = best_j = best_size = 0
    j2len = {}
    for i in range(alo, ahi):
        newj2len = {}
        for j in range(blo, bhi):
            if a[i] == b[j]:
                size = j2len.get(j - 1, 0) + 1
                newj2len[j] = size
                if size > best_size:
                    best_i = i - size + 1
                    best_j = j - size + 1
                    best_size = size
        j2len = newj2len
    return best_i, best_j, best_size


def _matching_blocks(a, b):
    queue = [(0, len(a), 0, len(b))]
    blocks = []
    while queue:
        alo, ahi, blo, bhi = queue.pop()
        i, j, k = _find_longest_match(a, alo, ahi, b, blo, bhi)
        if k:
            blocks.append((i, j, k))
            if alo < i and blo < j:
                queue.append((alo, i, blo, j))
            if i + k < ahi and j + k < bhi:
                queue.append((i + k, ahi, j + k, bhi))
    blocks.sort()
    return blocks


def _sequence_ratio(a, b):
    if not a and not b:
        return 1.0
    total = len(a) + len(b)
    if not total:
        return 1.0
    matches = sum(k for _i, _j, k in _matching_blocks(a, b))
    return 2.0 * matches / total


def get_close_matches(word, possibilities, n=3, cutoff=0.6):
    if not n > 0:
        raise ValueError("n must be > 0: %r" % (n,))
    if not 0.0 <= cutoff <= 1.0:
        raise ValueError("cutoff must be in [0.0, 1.0]: %r" % (cutoff,))
    result = []
    for possibility in possibilities:
        score = _sequence_ratio(possibility, word)
        if score >= cutoff:
            result.append((score, possibility))
    return [x for score, x in heapq.nlargest(n, result)]
