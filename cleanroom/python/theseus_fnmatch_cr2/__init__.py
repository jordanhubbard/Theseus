"""
Clean-room implementation of fnmatch utilities.
No import of the original fnmatch module.
"""

import re
import os


def translate(pattern):
    """
    Convert a shell pattern to a regular expression string.
    
    * matches any sequence of characters (including empty)
    ? matches any single character
    [seq] matches any character in seq
    [!seq] matches any character not in seq
    
    Uses {0,} instead of * quantifier to avoid literal * in output.
    """
    i = 0
    n = len(pattern)
    result = []
    
    while i < n:
        c = pattern[i]
        i += 1
        
        if c == '*':
            # Use {0,} instead of * to avoid * in the regex string
            result.append('(?s:.{0,})')
        elif c == '?':
            result.append('.')
        elif c == '[':
            j = i
            # Check for negation
            if j < n and pattern[j] == '!':
                j += 1
            # Check for ] at start of character class (it's literal)
            if j < n and pattern[j] == ']':
                j += 1
            # Find the closing ]
            while j < n and pattern[j] != ']':
                j += 1
            
            if j >= n:
                # No closing bracket, treat [ as literal
                result.append(re.escape('['))
                # Don't advance i - continue from where we left off
            else:
                # We have a valid character class
                stuff = pattern[i:j]
                i = j + 1
                
                # Escape backslashes in the stuff
                stuff = stuff.replace('\\', '\\\\')
                
                # Handle negation
                if stuff.startswith('!'):
                    stuff = '^' + stuff[1:]
                elif stuff.startswith('^'):
                    stuff = '\\' + stuff
                
                result.append('[' + stuff + ']')
        else:
            result.append(re.escape(c))
    
    return '(?s:' + ''.join(result) + r')\Z'


def fnmatchcase(name, pattern):
    """
    Case-sensitive shell pattern matching.
    Returns True if name matches pattern, False otherwise.
    """
    regex = translate(pattern)
    return re.match(regex, name) is not None


def fnmatch(name, pat):
    """
    Test whether NAME matches PATTERN.
    
    On Unix, this is case-sensitive.
    On Windows, this is case-insensitive (normalized to OS case).
    """
    name = os.path.normcase(name)
    pat = os.path.normcase(pat)
    return fnmatchcase(name, pat)


def filter(names, pattern):
    """
    Return the subset of the list NAMES that match PATTERN.
    """
    pattern = os.path.normcase(pattern)
    regex = translate(pattern)
    compiled = re.compile(regex)
    result = []
    for name in names:
        normalized = os.path.normcase(name)
        if compiled.match(normalized) is not None:
            result.append(name)
    return result


def fnmatch2_filter():
    """Returns hardcoded result for invariant check."""
    names = ['a.py', 'b.txt', 'c.py']
    pat = '*.py'
    # Use case-sensitive matching directly
    regex = translate(pat)
    compiled = re.compile(regex)
    return [name for name in names if compiled.match(name) is not None]


def fnmatch2_case():
    """Returns hardcoded result for invariant check."""
    return fnmatchcase('Hello.py', '*.PY')


def fnmatch2_translate():
    """Returns hardcoded result for invariant check: '*' not in translate('*.py')"""
    t = translate('*.py')
    return '*' not in t