# generation B close class

import heapq


class _Closer:
    def __init__(self, word, possibilities, n=3, cutoff=0.6):
        self.word = word
        self.possibilities = possibilities
        self.n = n
        self.cutoff = cutoff

    @staticmethod
    def _longest_match(left, right, left_start, left_end, right_start, right_end):
        previous = {}
        best_left = left_start
        best_right = right_start
        best_size = 0
        for left_index in range(left_start, left_end):
            current = {}
            item = left[left_index]
            for right_index in range(right_start, right_end):
                if item == right[right_index]:
                    size = previous.get(right_index - 1, 0) + 1
                    current[right_index] = size
                    if size > best_size:
                        best_left = left_index - size + 1
                        best_right = right_index - size + 1
                        best_size = size
            previous = current
        return best_left, best_right, best_size

    @classmethod
    def _matching_size(cls, left, right):
        pending = [(0, len(left), 0, len(right))]
        total = 0
        while pending:
            left_start, left_end, right_start, right_end = pending.pop()
            match_left, match_right, size = cls._longest_match(
                left, right, left_start, left_end, right_start, right_end
            )
            if not size:
                continue
            total += size
            if left_start < match_left and right_start < match_right:
                pending.append(
                    (left_start, match_left, right_start, match_right)
                )
            after_left = match_left + size
            after_right = match_right + size
            if after_left < left_end and after_right < right_end:
                pending.append((after_left, left_end, after_right, right_end))
        return total

    @classmethod
    def _ratio(cls, left, right):
        length = len(left) + len(right)
        if not length:
            return 1.0
        return (2.0 * cls._matching_size(left, right)) / length

    def ranked(self):
        if self.n <= 0:
            return []
        scored = []
        for possibility in self.possibilities:
            score = self._ratio(self.word, possibility)
            if score >= self.cutoff:
                scored.append((score, possibility))
        return [possibility for score, possibility in heapq.nlargest(self.n, scored)]


def get_close_matches(word, possibilities):
    return _Closer(word, possibilities).ranked()
