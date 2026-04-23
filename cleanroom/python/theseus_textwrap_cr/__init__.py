"""
theseus_textwrap_cr — Clean-room textwrap module.
No import of the standard `textwrap` module.
"""

import re as _re


def wrap(text, width=70, **kwargs):
    """Wrap text to width, returning a list of lines."""
    # Split into words preserving whitespace-separated tokens
    words = text.split()
    if not words:
        return []
    lines = []
    current = []
    current_len = 0
    for word in words:
        if current and current_len + 1 + len(word) > width:
            lines.append(' '.join(current))
            current = [word]
            current_len = len(word)
        else:
            if current:
                current_len += 1 + len(word)
            else:
                current_len = len(word)
            current.append(word)
    if current:
        lines.append(' '.join(current))
    return lines


def fill(text, width=70, **kwargs):
    """Wrap text to width and return a single string."""
    return '\n'.join(wrap(text, width, **kwargs))


def dedent(text):
    """Remove common leading whitespace from all lines in text."""
    lines = text.splitlines(True)
    if not lines:
        return text
    # Find common leading whitespace (spaces/tabs only)
    margin = None
    for line in lines:
        stripped = line.lstrip()
        if stripped:
            indent = line[:len(line) - len(stripped)]
            if margin is None:
                margin = indent
            elif indent.startswith(margin):
                pass
            elif margin.startswith(indent):
                margin = indent
            else:
                margin = ''
                break
    if margin is None:
        margin = ''
    if margin:
        return ''.join(line[len(margin):] if line.startswith(margin) else line
                       for line in lines)
    return text


def indent(text, prefix, predicate=None):
    """Add prefix to the beginning of lines in text."""
    if predicate is None:
        def predicate(line):
            return line.strip()
    return ''.join(prefix + line if predicate(line) else line
                   for line in text.splitlines(True))


def shorten(text, width, placeholder=' ...', **kwargs):
    """Collapse and truncate text to width."""
    words = text.split()
    result = ' '.join(words)
    if len(result) <= width:
        return result
    target = width - len(placeholder)
    truncated = wrap(result, target)
    if truncated:
        return truncated[0] + placeholder
    return placeholder.lstrip()


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def textwrap2_wrap():
    """wrap('word ' * 20, width=20) returns multiple lines; returns True."""
    lines = wrap('word ' * 20, width=20)
    return len(lines) > 1


def textwrap2_dedent():
    """dedent strips common leading whitespace; returns True."""
    text = '    hello\n    world'
    return dedent(text) == 'hello\nworld'


def textwrap2_indent():
    """indent adds prefix to each non-empty line; returns True."""
    result = indent('hello\nworld\n', '  ')
    return result == '  hello\n  world\n'


def textwrap2_fill():
    """fill produces a string with newlines when text is long; returns True."""
    result = fill('word ' * 20, width=20)
    return '\n' in result


__all__ = [
    'wrap', 'fill', 'dedent', 'indent', 'shorten',
    'textwrap2_wrap', 'textwrap2_dedent', 'textwrap2_indent', 'textwrap2_fill',
]
