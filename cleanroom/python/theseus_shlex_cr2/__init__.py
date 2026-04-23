"""
theseus_shlex_cr2 - Clean-room extended shlex utilities.
Do NOT import shlex. Implemented from scratch.
"""

import re

# Characters that are safe and don't need quoting
_SAFE_CHARS_RE = re.compile(r'^[a-zA-Z0-9_\-./=:@,]+$')


def quote(s: str) -> str:
    """
    Return a shell-safe quoted form of string s.
    
    If the string contains only safe characters (alphanumeric + _-./=:@,),
    return it as-is. Otherwise, wrap in single quotes, escaping any
    single quotes within the string as '\''.
    """
    if not s:
        # Empty string needs quoting
        return "''"
    
    if _SAFE_CHARS_RE.match(s):
        return s
    
    # Wrap in single quotes, escaping internal single quotes
    # A single quote inside single-quoted string: end quote, escaped quote, start quote
    escaped = s.replace("'", "'\\''")
    return "'" + escaped + "'"


def join(iterable) -> str:
    """
    Join a list of tokens into a shell-safe string.
    Each token is quoted if necessary, then joined with spaces.
    """
    return ' '.join(quote(token) for token in iterable)


def split(s: str) -> list:
    """
    Split a shell string into a list of tokens, respecting quoting.
    Supports single quotes, double quotes, and backslash escaping.
    """
    tokens = []
    current = []
    i = 0
    n = len(s)
    
    while i < n:
        c = s[i]
        
        # Skip whitespace between tokens
        if c in (' ', '\t', '\n', '\r'):
            if current:
                tokens.append(''.join(current))
                current = []
            i += 1
            continue
        
        # Single-quoted string: no escaping inside
        if c == "'":
            i += 1
            while i < n and s[i] != "'":
                current.append(s[i])
                i += 1
            if i < n:
                i += 1  # skip closing quote
            continue
        
        # Double-quoted string: backslash escaping for special chars
        if c == '"':
            i += 1
            while i < n and s[i] != '"':
                if s[i] == '\\' and i + 1 < n and s[i + 1] in ('"', '\\', '$', '`', '\n'):
                    i += 1
                    current.append(s[i])
                else:
                    current.append(s[i])
                i += 1
            if i < n:
                i += 1  # skip closing quote
            continue
        
        # Backslash escape outside quotes
        if c == '\\':
            i += 1
            if i < n:
                current.append(s[i])
                i += 1
            continue
        
        # Regular character
        current.append(c)
        i += 1
    
    if current:
        tokens.append(''.join(current))
    
    return tokens


# --- Zero-arg invariant functions ---

def shlex2_quote() -> str:
    """Demonstrates quote('hello world') == \"'hello world'\" """
    return quote('hello world')


def shlex2_quote_safe() -> str:
    """Demonstrates quote('hello') == 'hello' (no quoting needed)"""
    return quote('hello')


def shlex2_join() -> str:
    """Demonstrates join(['ls', '-la', '/tmp']) == 'ls -la /tmp'"""
    return join(['ls', '-la', '/tmp'])