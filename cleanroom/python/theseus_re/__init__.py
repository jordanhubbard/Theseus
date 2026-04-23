"""
theseus_re: Clean-room regex subset implementation.
Supports: \d, \w, . (any), +, *, ^, $, basic character classes [...].
"""


def _match_here(pattern, text, pi, ti):
    """
    Try to match pattern[pi:] against text[ti:].
    Returns the end index in text if matched, or -1 if not.
    """
    while True:
        # End of pattern
        if pi == len(pattern):
            return ti

        # Handle $ anchor
        if pattern[pi] == '$' and pi == len(pattern) - 1:
            if ti == len(text):
                return ti
            else:
                return -1

        # Determine current atom and its length in pattern
        atom_end = _atom_end(pattern, pi)
        if atom_end == -1:
            return -1

        # Check for quantifier after atom
        quantifier = None
        quant_pi = atom_end
        if quant_pi < len(pattern) and pattern[quant_pi] in ('+', '*', '?'):
            quantifier = pattern[quant_pi]
            quant_pi += 1

        if quantifier == '*':
            # Zero or more: try matching as many as possible (greedy), then backtrack
            return _match_star(pattern, text, pi, atom_end, quant_pi, ti, min_count=0)
        elif quantifier == '+':
            # One or more
            return _match_star(pattern, text, pi, atom_end, quant_pi, ti, min_count=1)
        elif quantifier == '?':
            # Zero or one
            # Try with one match first
            if ti < len(text) and _match_atom(pattern, pi, atom_end, text[ti]):
                result = _match_here(pattern, text, quant_pi, ti + 1)
                if result != -1:
                    return result
            # Try with zero matches
            return _match_here(pattern, text, quant_pi, ti)
        else:
            # No quantifier: must match exactly one
            if ti < len(text) and _match_atom(pattern, pi, atom_end, text[ti]):
                pi = atom_end
                ti += 1
                # continue loop
            else:
                return -1


def _atom_end(pattern, pi):
    """
    Return the index after the current atom starting at pi.
    Returns -1 on error.
    """
    if pi >= len(pattern):
        return pi
    c = pattern[pi]
    if c == '\\':
        if pi + 1 < len(pattern):
            return pi + 2
        else:
            return -1
    elif c == '[':
        # Find matching ]
        j = pi + 1
        if j < len(pattern) and pattern[j] == '^':
            j += 1
        if j < len(pattern) and pattern[j] == ']':
            j += 1  # ] at start of class is literal
        while j < len(pattern) and pattern[j] != ']':
            j += 1
        if j < len(pattern):
            return j + 1
        else:
            return -1
    else:
        return pi + 1


def _match_atom(pattern, pi, atom_end, char):
    """
    Return True if char matches the atom pattern[pi:atom_end].
    """
    atom = pattern[pi:atom_end]
    if atom == '.':
        return True  # matches any character (except we won't worry about newline)
    elif atom == '\\d':
        return char.isdigit()
    elif atom == '\\D':
        return not char.isdigit()
    elif atom == '\\w':
        return char.isalnum() or char == '_'
    elif atom == '\\W':
        return not (char.isalnum() or char == '_')
    elif atom == '\\s':
        return char in ' \t\n\r\f\v'
    elif atom == '\\S':
        return char not in ' \t\n\r\f\v'
    elif atom.startswith('['):
        return _match_char_class(atom, char)
    elif len(atom) == 1:
        return atom == char
    else:
        return False


def _match_char_class(atom, char):
    """
    Match char against a character class like [abc], [^abc], [a-z], etc.
    atom includes the surrounding brackets.
    """
    # atom is like [abc] or [^abc] or [a-z0-9]
    i = 1  # skip '['
    negate = False
    if i < len(atom) - 1 and atom[i] == '^':
        negate = True
        i += 1

    matched = False
    while i < len(atom) - 1:  # -1 to skip ']'
        # Check for range like a-z
        if i + 2 < len(atom) - 1 and atom[i + 1] == '-':
            # Range
            start_c = atom[i]
            end_c = atom[i + 2]
            if start_c <= char <= end_c:
                matched = True
            i += 3
        elif atom[i] == '\\' and i + 1 < len(atom) - 1:
            # Escape sequence inside class
            esc = atom[i:i+2]
            if esc == '\\d':
                if char.isdigit():
                    matched = True
            elif esc == '\\w':
                if char.isalnum() or char == '_':
                    matched = True
            elif esc == '\\s':
                if char in ' \t\n\r\f\v':
                    matched = True
            else:
                if atom[i+1] == char:
                    matched = True
            i += 2
        else:
            if atom[i] == char:
                matched = True
            i += 1

    if negate:
        return not matched
    return matched


def _match_star(pattern, text, pi, atom_end, quant_pi, ti, min_count):
    """
    Greedy match for * or + quantifier.
    Tries to match as many atoms as possible, then backtracks.
    """
    # Count how many times the atom matches starting at ti
    count = 0
    positions = [ti]
    j = ti
    while j < len(text) and _match_atom(pattern, pi, atom_end, text[j]):
        j += 1
        count += 1
        positions.append(j)

    # Try from maximum down to min_count
    for k in range(len(positions) - 1, -1, -1):
        if k < min_count:
            break
        result = _match_here(pattern, text, quant_pi, positions[k])
        if result != -1:
            return result
    return -1


def _compile_match(pattern, text, start=0):
    """
    Try to match pattern at position start in text.
    Returns (match_start, match_end) or None.
    """
    pi = 0
    # Handle ^ anchor
    if pattern and pattern[0] == '^':
        result = _match_here(pattern, text, 1, start)
        if result != -1:
            return (start, result)
        return None
    else:
        result = _match_here(pattern, text, 0, start)
        if result != -1:
            return (start, result)
        return None


def _search(pattern, text):
    """
    Search for pattern anywhere in text.
    Returns (match_start, match_end) or None.
    """
    if pattern and pattern[0] == '^':
        return _compile_match(pattern, text, 0)

    for i in range(len(text) + 1):
        result = _match_here(pattern, text, 0, i)
        if result != -1:
            return (i, result)
    return None


def re_match_digit():
    """
    Match pattern r'\d+' against '123abc'.
    Returns True if match found at start.
    """
    pattern = r'\d+'
    text = '123abc'
    m = _compile_match(pattern, text, 0)
    return m is not None and m[0] == 0 and m[1] > 0


def re_search_digit():
    """
    Search for r'\d+' in 'abc123def'.
    Returns True if found anywhere.
    """
    pattern = r'\d+'
    text = 'abc123def'
    m = _search(pattern, text)
    return m is not None


def re_sub_basic():
    """
    Replace first occurrence of r'\d+' in 'abc123def' with 'NUM'.
    Returns 'abcNUMdef'.
    """
    pattern = r'\d+'
    text = 'abc123def'
    replacement = 'NUM'
    m = _search(pattern, text)
    if m is None:
        return text
    start, end = m
    return text[:start] + replacement + text[end:]


# Additional utility functions for general use

def match(pattern, text):
    """Match pattern at the start of text. Returns (start, end) or None."""
    return _compile_match(pattern, text, 0)


def search(pattern, text):
    """Search for pattern anywhere in text. Returns (start, end) or None."""
    return _search(pattern, text)


def sub(pattern, replacement, text, count=0):
    """Replace occurrences of pattern in text with replacement."""
    result = []
    i = 0
    num_replacements = 0
    while i <= len(text):
        if count > 0 and num_replacements >= count:
            result.append(text[i:])
            break
        m = None
        if not (pattern and pattern[0] == '^'):
            r = _match_here(pattern, text, 0, i)
            if r != -1:
                m = (i, r)
        else:
            if i == 0:
                r = _match_here(pattern, text, 1, i)
                if r != -1:
                    m = (i, r)

        if m is not None:
            start, end = m
            result.append(text[i:start])
            result.append(replacement)
            num_replacements += 1
            if end == i:
                # Zero-length match, advance by one to avoid infinite loop
                if i < len(text):
                    result.append(text[i])
                i += 1
            else:
                i = end
        else:
            if i < len(text):
                result.append(text[i])
            i += 1
    return ''.join(result)