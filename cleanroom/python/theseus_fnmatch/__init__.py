"""
theseus_fnmatch - Clean-room implementation of Unix shell-style wildcard matching.
"""

import os
import re


def _translate(pat: str) -> str:
    """Translate a shell pattern to a regular expression string."""
    i = 0
    n = len(pat)
    res = ''
    
    while i < n:
        c = pat[i]
        i += 1
        
        if c == '*':
            res += '.*'
        elif c == '?':
            res += '.'
        elif c == '[':
            j = i
            # Check for negation
            if j < n and pat[j] == '!':
                j += 1
            # Check for ] at start of class
            if j < n and pat[j] == ']':
                j += 1
            # Find the end of the character class
            while j < n and pat[j] != ']':
                j += 1
            
            if j >= n:
                # No closing bracket, treat [ as literal
                res += re.escape('[')
            else:
                # We have a valid character class
                stuff = pat[i:j]
                i = j + 1
                
                if not stuff:
                    res += re.escape('[]')
                else:
                    # Handle negation
                    if stuff[0] == '!':
                        stuff = '^' + stuff[1:]
                    elif stuff[0] in ('^', ']'):
                        stuff = '\\' + stuff
                    
                    # Escape backslashes in the character class
                    stuff = stuff.replace('\\', '\\\\')
                    res += '[' + stuff + ']'
        else:
            res += re.escape(c)
    
    return res + r'\Z'


def fnmatch(name: str, pat: str) -> bool:
    """
    Test whether the filename string matches the pattern string.
    
    Patterns:
      '*'     matches everything
      '?'     matches any single character
      '[seq]' matches any character in seq
      '[!seq]' matches any character not in seq
    
    The match is case-sensitive on case-sensitive filesystems.
    """
    try:
        name = os.path.normcase(name)
        pat = os.path.normcase(pat)
    except Exception:
        pass
    
    regex = _translate(pat)
    return re.match(regex, name) is not None


def fnmatchcase(name: str, pat: str) -> bool:
    """
    Test whether the filename string matches the pattern string,
    always performing a case-sensitive comparison.
    """
    regex = _translate(pat)
    return re.match(regex, name) is not None


def filter(names, pat: str):
    """
    Return the subset of the list of names that match the pattern.
    """
    result = []
    try:
        pat = os.path.normcase(pat)
    except Exception:
        pass
    regex = _translate(pat)
    for name in names:
        try:
            normalized = os.path.normcase(name)
        except Exception:
            normalized = name
        if re.match(regex, normalized) is not None:
            result.append(name)
    return result


def translate(pat: str) -> str:
    """
    Translate a shell pattern to a regular expression string.
    """
    return _translate(pat)


def fnmatch_star_match() -> bool:
    return fnmatch('foo.py', '*.py')


def fnmatch_star_no_match() -> bool:
    return fnmatch('foo.txt', '*.py')


def fnmatch_question_match() -> bool:
    return fnmatch('file_a.py', 'file_?.py')


def match_star(name: str, pat: str) -> bool:
    """
    Test whether the filename string matches the pattern string using
    star ('*') wildcard matching. Returns True if the name matches the
    pattern containing '*' wildcards.
    """
    return fnmatch(name, pat)


def no_match(name: str, pat: str) -> bool:
    """
    Test whether the filename string does NOT match the pattern string.
    Returns True if the name does NOT match the pattern.
    """
    return not fnmatch(name, pat)


def question_mark(name: str, pat: str) -> bool:
    """
    Test whether the filename string matches the pattern string using
    question mark ('?') wildcard matching. Returns True if the name
    matches the pattern containing '?' wildcards.
    """
    return fnmatch(name, pat)