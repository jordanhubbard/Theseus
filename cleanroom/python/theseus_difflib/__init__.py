"""
theseus_difflib - Clean-room implementation of diff/similarity utilities.
No import of difflib or any third-party library.
"""

def _lcs_length(a, b):
    """Compute the length of the longest common subsequence of a and b."""
    m, n = len(a), len(b)
    # Use two-row DP to save memory
    prev = [0] * (n + 1)
    curr = [0] * (n + 1)
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                curr[j] = prev[j - 1] + 1
            else:
                curr[j] = max(prev[j], curr[j - 1])
        prev, curr = curr, [0] * (n + 1)
    return prev[n]


def _matching_blocks(a, b):
    """
    Find matching blocks between sequences a and b using a recursive approach
    similar to SequenceMatcher. Returns list of (i, j, size) triples.
    """
    blocks = []
    _find_matching_blocks(a, b, 0, len(a), 0, len(b), blocks)
    blocks.append((len(a), len(b), 0))  # sentinel
    return blocks


def _find_longest_match(a, b, alo, ahi, blo, bhi):
    """Find the longest matching block in a[alo:ahi] and b[blo:bhi]."""
    best_i, best_j, best_size = alo, blo, 0
    
    # Build index of b elements
    b_index = {}
    for j in range(blo, bhi):
        elem = b[j]
        if elem not in b_index:
            b_index[elem] = []
        b_index[elem].append(j)
    
    # j2len[j] = length of longest match ending at b[j]
    j2len = {}
    
    for i in range(alo, ahi):
        new_j2len = {}
        elem = a[i]
        if elem in b_index:
            for j in b_index[elem]:
                if j < blo:
                    continue
                if j >= bhi:
                    break
                k = j2len.get(j - 1, 0) + 1
                new_j2len[j] = k
                if k > best_size:
                    best_i, best_j, best_size = i - k + 1, j - k + 1, k
        j2len = new_j2len
    
    # Extend the match to include adjacent equal elements
    while best_i > alo and best_j > blo and a[best_i - 1] == b[best_j - 1]:
        best_i -= 1
        best_j -= 1
        best_size += 1
    while best_i + best_size < ahi and best_j + best_size < bhi and \
          a[best_i + best_size] == b[best_j + best_size]:
        best_size += 1
    
    return best_i, best_j, best_size


def _find_matching_blocks(a, b, alo, ahi, blo, bhi, blocks):
    """Recursively find all matching blocks."""
    i, j, k = _find_longest_match(a, b, alo, ahi, blo, bhi)
    if k > 0:
        if alo < i and blo < j:
            _find_matching_blocks(a, b, alo, i, blo, j, blocks)
        blocks.append((i, j, k))
        if i + k < ahi and j + k < bhi:
            _find_matching_blocks(a, b, i + k, ahi, j + k, bhi, blocks)


def _count_matches(a, b):
    """Count the number of matching characters between a and b using matching blocks."""
    if isinstance(a, str):
        a_seq = list(a)
        b_seq = list(b)
    else:
        a_seq = list(a)
        b_seq = list(b)
    
    blocks = _matching_blocks(a_seq, b_seq)
    matches = sum(size for _, _, size in blocks)
    return matches


def sequence_matcher_ratio(a, b):
    """
    Compute similarity ratio between two strings.
    ratio = 2.0 * M / T where M is number of matching characters
    and T is total number of characters in both sequences.
    Returns a float between 0.0 and 1.0.
    """
    if not a and not b:
        return 1.0
    total = len(a) + len(b)
    if total == 0:
        return 1.0
    matches = _count_matches(a, b)
    return 2.0 * matches / total


def get_close_matches(word, possibilities, n=3, cutoff=0.6):
    """
    Return a list of the best 'good enough' matches of word in possibilities.
    
    word: a string for which close matches are desired
    possibilities: a list of strings to match against
    n: maximum number of close matches to return (default 3)
    cutoff: minimum similarity ratio (default 0.6)
    
    Returns a list of the best matches, sorted by similarity (best first).
    """
    if not isinstance(word, str):
        raise TypeError("word must be a string")
    if not isinstance(possibilities, (list, tuple)):
        raise TypeError("possibilities must be a list or tuple")
    if not isinstance(n, int) or n <= 0:
        raise ValueError("n must be a positive integer")
    if not (0.0 <= cutoff <= 1.0):
        raise ValueError("cutoff must be in [0.0, 1.0]")
    
    result = []
    for possibility in possibilities:
        if not isinstance(possibility, str):
            continue
        ratio = sequence_matcher_ratio(word, possibility)
        if ratio >= cutoff:
            result.append((ratio, possibility))
    
    # Sort by ratio descending, then by the string for stability
    result.sort(key=lambda x: (-x[0], x[1]))
    
    return [match for _, match in result[:n]]


def unified_diff(a, b, fromfile='', tofile='', fromfiledate='', tofiledate='',
                 lineterm='\n', n=3):
    """
    Compare two sequences of lines and generate a unified format diff.
    
    a, b: sequences of strings (lines)
    fromfile, tofile: file names for the diff header
    fromfiledate, tofiledate: file dates for the diff header
    lineterm: line terminator (default '\n')
    n: number of context lines (default 3)
    
    Yields lines of the unified diff.
    """
    # Ensure a and b are lists
    a = list(a)
    b = list(b)
    
    # Generate header
    if fromfile or tofile:
        from_header = '--- ' + fromfile
        if fromfiledate:
            from_header += '\t' + fromfiledate
        yield from_header + lineterm
        
        to_header = '+++ ' + tofile
        if tofiledate:
            to_header += '\t' + tofiledate
        yield to_header + lineterm
    
    # Find matching blocks
    blocks = _matching_blocks(a, b)
    
    # Generate diff groups
    # Each group is a set of changes with context
    groups = _group_opcodes(_get_opcodes(a, b, blocks), n)
    
    for group in groups:
        # Determine range for the hunk header
        i1 = group[0][1]
        i2 = group[-1][2]
        j1 = group[0][3]
        j2 = group[-1][4]
        
        # Format hunk header
        if i2 - i1 == 1:
            from_range = str(i1 + 1)
        elif i2 - i1 == 0:
            from_range = '{},0'.format(i1)
        else:
            from_range = '{},{}'.format(i1 + 1, i2 - i1)
        
        if j2 - j1 == 1:
            to_range = str(j1 + 1)
        elif j2 - j1 == 0:
            to_range = '{},0'.format(j1)
        else:
            to_range = '{},{}'.format(j1 + 1, j2 - j1)
        
        yield '@@ -{} +{} @@{}'.format(from_range, to_range, lineterm)
        
        for tag, i1, i2, j1, j2 in group:
            if tag == 'equal':
                for line in a[i1:i2]:
                    yield ' ' + line
            elif tag == 'replace':
                for line in a[i1:i2]:
                    yield '-' + line
                for line in b[j1:j2]:
                    yield '+' + line
            elif tag == 'delete':
                for line in a[i1:i2]:
                    yield '-' + line
            elif tag == 'insert':
                for line in b[j1:j2]:
                    yield '+' + line


def _get_opcodes(a, b, blocks):
    """
    Return list of 5-tuples describing how to turn a into b.
    Each tuple is (tag, i1, i2, j1, j2) where tag is one of:
    'replace', 'delete', 'insert', 'equal'
    """
    opcodes = []
    i = j = 0
    for ai, bj, size in blocks:
        tag = ''
        if i < ai and j < bj:
            tag = 'replace'
        elif i < ai:
            tag = 'delete'
        elif j < bj:
            tag = 'insert'
        if tag:
            opcodes.append((tag, i, ai, j, bj))
        i, j = ai + size, bj + size
        if size:
            opcodes.append(('equal', ai, i, bj, j))
    return opcodes


def _group_opcodes(opcodes, n=3):
    """
    Isolate change clusters by eliminating ranges with no changes.
    Groups opcodes into hunks with n lines of context.
    """
    if not opcodes:
        return
    
    # Trim leading/trailing equal blocks
    codes = list(opcodes)
    if codes and codes[0][0] == 'equal':
        tag, i1, i2, j1, j2 = codes[0]
        codes[0] = tag, max(i1, i2 - n), i2, max(j1, j2 - n), j2
    if codes and codes[-1][0] == 'equal':
        tag, i1, i2, j1, j2 = codes[-1]
        codes[-1] = tag, i1, min(i2, i1 + n), j1, min(j2, j1 + n)
    
    group = []
    for code in codes:
        tag, i1, i2, j1, j2 = code
        if tag == 'equal' and i2 - i1 > 2 * n:
            group.append((tag, i1, min(i2, i1 + n), j1, min(j2, j1 + n)))
            yield group
            group = [(tag, max(i1, i2 - n), i2, max(j1, j2 - n), j2)]
        else:
            group.append(code)
    
    if group and not (len(group) == 1 and group[0][0] == 'equal'):
        yield group


# ---- Required test/invariant functions ----

def difflib_ratio_identical():
    """Return the similarity ratio of 'hello' vs 'hello', which should be 1.0."""
    return sequence_matcher_ratio('hello', 'hello')


def difflib_close_matches_has_apple():
    """
    Return True if get_close_matches('appel', ['ape', 'apple', 'peach']) includes 'apple'.
    """
    matches = get_close_matches('appel', ['ape', 'apple', 'peach'])
    return 'apple' in matches


def difflib_ratio_different_lt_half():
    """Return True if the similarity ratio of 'abc' vs 'xyz' is less than 0.5."""
    return sequence_matcher_ratio('abc', 'xyz') < 0.5