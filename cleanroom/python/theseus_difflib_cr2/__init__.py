"""
theseus_difflib_cr2 - Clean-room implementation of difflib utilities.
Do NOT import difflib or any third-party library.
"""


class SequenceMatcher:
    """
    Compare two sequences and compute similarity metrics.
    Uses dynamic programming (LCS-based) approach.
    """

    def __init__(self, isjunk, a, b):
        self.isjunk = isjunk
        self.a = a
        self.b = b
        self._matching_blocks = None
        self._opcodes = None

    def _compute_lcs_length(self):
        """Compute the length of the longest common subsequence."""
        a = self.a
        b = self.b
        la = len(a)
        lb = len(b)

        # Filter junk if isjunk is provided
        if self.isjunk is not None:
            a_filtered = [x for x in a if not self.isjunk(x)]
            b_filtered = [x for x in b if not self.isjunk(x)]
        else:
            a_filtered = list(a)
            b_filtered = list(b)

        la_f = len(a_filtered)
        lb_f = len(b_filtered)

        if la_f == 0 or lb_f == 0:
            return 0

        # Use two-row DP to save memory
        prev = [0] * (lb_f + 1)
        curr = [0] * (lb_f + 1)

        for i in range(1, la_f + 1):
            for j in range(1, lb_f + 1):
                if a_filtered[i - 1] == b_filtered[j - 1]:
                    curr[j] = prev[j - 1] + 1
                else:
                    curr[j] = max(prev[j], curr[j - 1])
            prev, curr = curr, [0] * (lb_f + 1)

        return prev[lb_f]

    def _find_matching_blocks(self):
        """
        Find matching blocks between a and b using a recursive approach
        similar to difflib's SequenceMatcher.
        Returns list of (i, j, n) triples where a[i:i+n] == b[j:j+n].
        """
        if self._matching_blocks is not None:
            return self._matching_blocks

        blocks = []
        self._find_longest_match_recursive(
            0, len(self.a), 0, len(self.b), blocks
        )
        blocks.append((len(self.a), len(self.b), 0))
        self._matching_blocks = blocks
        return blocks

    def _find_longest_match(self, alo, ahi, blo, bhi):
        """
        Find the longest matching block in a[alo:ahi] and b[blo:bhi].
        Returns (i, j, k) such that a[i:i+k] == b[j:j+k].
        """
        a = self.a
        b = self.b
        isjunk = self.isjunk

        best_i = alo
        best_j = blo
        best_size = 0

        # Build index of b elements
        b_index = {}
        for j in range(blo, bhi):
            elem = b[j]
            if isjunk is not None and isjunk(elem):
                continue
            if elem not in b_index:
                b_index[elem] = []
            b_index[elem].append(j)

        # j2len[j] = length of longest match ending with b[j]
        j2len = {}

        for i in range(alo, ahi):
            elem = a[i]
            if isjunk is not None and isjunk(elem):
                continue
            new_j2len = {}
            if elem in b_index:
                for j in b_index[elem]:
                    if j < blo:
                        continue
                    if j >= bhi:
                        break
                    k = j2len.get(j - 1, 0) + 1
                    new_j2len[j] = k
                    if k > best_size:
                        best_i = i - k + 1
                        best_j = j - k + 1
                        best_size = k
            j2len = new_j2len

        # Extend the match to include junk on both sides
        while (best_i > alo and best_j > blo and
               (isjunk is None or isjunk(a[best_i - 1])) and
               a[best_i - 1] == b[best_j - 1]):
            best_i -= 1
            best_j -= 1
            best_size += 1

        while (best_i + best_size < ahi and best_j + best_size < bhi and
               (isjunk is None or isjunk(a[best_i + best_size])) and
               a[best_i + best_size] == b[best_j + best_size]):
            best_size += 1

        return best_i, best_j, best_size

    def _find_longest_match_recursive(self, alo, ahi, blo, bhi, blocks):
        """Recursively find all matching blocks."""
        i, j, k = self._find_longest_match(alo, ahi, blo, bhi)
        if k > 0:
            if alo < i and blo < j:
                self._find_longest_match_recursive(alo, i, blo, j, blocks)
            blocks.append((i, j, k))
            if i + k < ahi and j + k < bhi:
                self._find_longest_match_recursive(i + k, ahi, j + k, bhi, blocks)

    def get_matching_blocks(self):
        """Return list of matching blocks."""
        return self._find_matching_blocks()

    def get_opcodes(self):
        """
        Return list of 5-tuples describing how to turn a into b.
        Each tuple is (tag, i1, i2, j1, j2) where tag is one of:
        'replace', 'delete', 'insert', 'equal'
        """
        if self._opcodes is not None:
            return self._opcodes

        opcodes = []
        i = 0
        j = 0
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
            i = ai + size
            j = bj + size
            if size:
                opcodes.append(('equal', ai, i, bj, j))

        self._opcodes = opcodes
        return opcodes

    def ratio(self):
        """
        Return a measure of the sequences' similarity as a float in [0, 1].
        """
        matches = sum(n for _, _, n in self.get_matching_blocks())
        total = len(self.a) + len(self.b)
        if total == 0:
            return 1.0
        return 2.0 * matches / total

    def quick_ratio(self):
        """Upper bound on ratio()."""
        la = len(self.a)
        lb = len(self.b)
        total = la + lb
        if total == 0:
            return 1.0
        # Count common elements
        avail = {}
        for elem in self.a:
            avail[elem] = avail.get(elem, 0) + 1
        matches = 0
        for elem in self.b:
            if avail.get(elem, 0) > 0:
                matches += 1
                avail[elem] -= 1
        return 2.0 * matches / total

    def real_quick_ratio(self):
        """Fastest upper bound on ratio()."""
        la = len(self.a)
        lb = len(self.b)
        total = la + lb
        if total == 0:
            return 1.0
        return 2.0 * min(la, lb) / total


def get_close_matches(word, possibilities, n=3, cutoff=0.6):
    """
    Return a list of the best "good enough" matches of word in possibilities.

    word: a string for which close matches are desired
    possibilities: a list of strings to match against
    n: maximum number of close matches to return (default 3)
    cutoff: minimum similarity score (default 0.6)

    Returns a list of the best matches, sorted by similarity score (best first).
    """
    if not isinstance(n, int):
        raise TypeError("n must be an int, not %s" % type(n).__name__)
    if n <= 0:
        raise ValueError("n must be > 0: %r" % (n,))
    if not 0.0 <= cutoff <= 1.0:
        raise ValueError("cutoff must be in [0.0, 1.0]: %r" % (cutoff,))

    result = []
    s = SequenceMatcher(None, word, None)
    for possibility in possibilities:
        s.b = possibility
        s._matching_blocks = None
        s._opcodes = None
        # Quick checks before full ratio
        if s.real_quick_ratio() >= cutoff and s.quick_ratio() >= cutoff:
            score = s.ratio()
            if score >= cutoff:
                result.append((score, possibility))

    # Sort by score descending, then by possibility for stability
    result.sort(key=lambda x: (-x[0], x[1]))
    return [x for _, x in result[:n]]


def ndiff(a, b):
    """
    Compare sequences of lines; generate delta in ndiff format.

    Each line of output is prefixed with:
      '  ' - line common to both
      '- ' - line only in a
      '+ ' - line only in b
      '? ' - hints about intraline differences

    a, b: sequences of strings (lines)
    Returns a list of strings.
    """
    result = []
    sm = SequenceMatcher(None, a, b)
    opcodes = sm.get_opcodes()

    for tag, i1, i2, j1, j2 in opcodes:
        if tag == 'equal':
            for line in a[i1:i2]:
                result.append('  ' + line)
        elif tag == 'replace':
            # For each pair of replaced lines, show hints
            a_lines = list(a[i1:i2])
            b_lines = list(b[j1:j2])
            # Interleave with hints
            for line in a_lines:
                result.append('- ' + line)
            for line in b_lines:
                result.append('+ ' + line)
            # Add '?' hints for the first pair if possible
            if a_lines and b_lines:
                hint = _make_hint(a_lines[0], b_lines[0])
                if hint:
                    result.append('? ' + hint)
        elif tag == 'delete':
            for line in a[i1:i2]:
                result.append('- ' + line)
        elif tag == 'insert':
            for line in b[j1:j2]:
                result.append('+ ' + line)

    return result


def _make_hint(a_line, b_line):
    """
    Generate a '?' hint line showing differences between two lines.
    Returns a string (without the '? ' prefix) or empty string.
    """
    # Strip trailing newline for comparison
    a_stripped = a_line.rstrip('\n\r')
    b_stripped = b_line.rstrip('\n\r')

    if not a_stripped and not b_stripped:
        return ''

    # Find common prefix length
    common_prefix = 0
    for i in range(min(len(a_stripped), len(b_stripped))):
        if a_stripped[i] == b_stripped[i]:
            common_prefix += 1
        else:
            break

    # Find common suffix length
    common_suffix = 0
    a_rev = a_stripped[common_prefix:]
    b_rev = b_stripped[common_prefix:]
    for i in range(1, min(len(a_rev), len(b_rev)) + 1):
        if a_rev[-i] == b_rev[-i]:
            common_suffix += 1
        else:
            break

    # Build hint
    hint_len = max(len(a_stripped), len(b_stripped))
    if hint_len == 0:
        return ''

    hint_chars = [' '] * hint_len
    # Mark the differing region
    diff_start = common_prefix
    diff_end_a = len(a_stripped) - common_suffix
    diff_end_b = len(b_stripped) - common_suffix
    diff_end = max(diff_end_a, diff_end_b)

    for i in range(diff_start, diff_end):
        if i < hint_len:
            hint_chars[i] = '^'

    hint = ''.join(hint_chars).rstrip()
    if hint.strip():
        return hint + '\n'
    return ''


# ---------------------------------------------------------------------------
# Zero-arg invariant functions
# ---------------------------------------------------------------------------

def difflib2_ratio():
    """SequenceMatcher(None, 'abcde', 'abcde').ratio() == 1.0"""
    return SequenceMatcher(None, 'abcde', 'abcde').ratio()


def difflib2_close_matches():
    """get_close_matches('appel', ['apple', 'mango'])[0] == 'apple'"""
    return get_close_matches('appel', ['apple', 'mango'])[0]


def difflib2_ndiff():
    """some line from ndiff(['a\\n'], ['b\\n']) starts with '?' — returns True"""
    lines = ndiff(['a\n'], ['b\n'])
    return any(line.startswith('?') for line in lines)