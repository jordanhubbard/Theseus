"""
theseus_shlex: Clean-room shell lexer/splitter implementation.
"""


def split(s: str) -> list:
    """
    Tokenize a shell-style string respecting quotes and escapes.
    
    Examples:
        split('ls -la /tmp') == ['ls', '-la', '/tmp']
        split('echo "hello world"') == ['echo', 'hello world']
    """
    tokens = []
    current = []
    in_single_quote = False
    in_double_quote = False
    i = 0
    
    while i < len(s):
        c = s[i]
        
        if in_single_quote:
            if c == "'":
                in_single_quote = False
            else:
                current.append(c)
        elif in_double_quote:
            if c == '"':
                in_double_quote = False
            elif c == '\\':
                # In double quotes, backslash escapes certain characters
                if i + 1 < len(s):
                    next_c = s[i + 1]
                    if next_c in ('"', '\\', '$', '`', '\n'):
                        current.append(next_c)
                        i += 1
                    else:
                        current.append(c)
                else:
                    current.append(c)
            else:
                current.append(c)
        else:
            if c == '\\':
                # Escape next character
                if i + 1 < len(s):
                    if s[i + 1] == '\n':
                        # Line continuation - skip both
                        i += 1
                    else:
                        current.append(s[i + 1])
                        i += 1
                # else: trailing backslash, ignore
            elif c == "'":
                in_single_quote = True
            elif c == '"':
                in_double_quote = True
            elif c in (' ', '\t', '\n', '\r'):
                if current:
                    tokens.append(''.join(current))
                    current = []
            else:
                current.append(c)
        
        i += 1
    
    if in_single_quote or in_double_quote:
        raise ValueError("No closing quotation")
    
    if current:
        tokens.append(''.join(current))
    
    return tokens


def quote(s: str) -> str:
    """
    Return a shell-escaped version of the string s.
    
    The returned value is a string that can safely be used as one token
    in a shell command line, for cases where you cannot use a list.
    
    Examples:
        quote('hello world') == "'hello world'"
        quote('') == "''"
    """
    if not s:
        return "''"
    
    # Check if the string is safe without quoting
    # Safe characters: alphanumeric, and @%+=:,./-_
    safe_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@%+=:,./-_')
    
    if all(c in safe_chars for c in s):
        return s
    
    # Wrap in single quotes, escaping any single quotes in the string
    # Single quotes cannot appear inside single-quoted strings,
    # so we end the quote, add an escaped single quote, and restart
    return "'" + s.replace("'", "'\\''") + "'"


def split_simple(s: str) -> list:
    """
    Split a string on whitespace, respecting single and double quotes,
    but without backslash escape processing.
    
    Examples:
        split_simple('ls -la /tmp') == ['ls', '-la', '/tmp']
        split_simple('echo "hello world"') == ['echo', 'hello world']
        split_simple("echo 'hello world'") == ['echo', 'hello world']
    """
    tokens = []
    current = []
    in_single_quote = False
    in_double_quote = False
    
    for c in s:
        if in_single_quote:
            if c == "'":
                in_single_quote = False
            else:
                current.append(c)
        elif in_double_quote:
            if c == '"':
                in_double_quote = False
            else:
                current.append(c)
        else:
            if c == "'":
                in_single_quote = True
            elif c == '"':
                in_double_quote = True
            elif c in (' ', '\t', '\n', '\r'):
                if current:
                    tokens.append(''.join(current))
                    current = []
            else:
                current.append(c)
    
    if in_single_quote or in_double_quote:
        raise ValueError("No closing quotation")
    
    if current:
        tokens.append(''.join(current))
    
    return tokens


def split_quoted(s: str) -> list:
    """
    Tokenize a shell-style string respecting quotes and backslash escapes.
    This is equivalent to the full POSIX shell word splitting.
    
    Examples:
        split_quoted('ls -la /tmp') == ['ls', '-la', '/tmp']
        split_quoted('echo "hello world"') == ['echo', 'hello world']
        split_quoted("echo 'it'\\''s'") == ['echo', "it's"]
    """
    return split(s)


def quote_with_space(s: str) -> str:
    """
    Quote a string if it contains spaces or special characters,
    so it can be safely used in a shell command.
    
    If the string contains no spaces or special characters, return it as-is.
    Otherwise, wrap it in single quotes (escaping any single quotes within).
    
    Examples:
        quote_with_space('hello') == 'hello'
        quote_with_space('hello world') == "'hello world'"
        quote_with_space('') == "''"
    """
    return quote(s)


def shlex_split_simple():
    return split('ls -la /tmp')

def shlex_split_quoted():
    return split('echo "hello world"')

def shlex_quote_space():
    return quote('hello world')