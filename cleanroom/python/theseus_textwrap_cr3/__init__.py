"""
theseus_textwrap_cr3 - Clean-room implementation of textwrap utilities.
Do NOT import textwrap or any third-party library.
"""

import re


def dedent(text):
    """Remove common leading whitespace from all lines."""
    lines = text.splitlines(True)
    
    # Find common leading whitespace among non-empty lines
    common = None
    for line in lines:
        # Strip trailing newline to check content
        stripped = line.rstrip('\n').rstrip('\r')
        if not stripped:
            # Skip empty/whitespace-only lines for common prefix calculation
            continue
        # Find leading whitespace
        leading = len(stripped) - len(stripped.lstrip())
        prefix = stripped[:leading]
        if common is None:
            common = prefix
        else:
            # Find common prefix between current common and this line's prefix
            new_common = []
            for a, b in zip(common, prefix):
                if a == b:
                    new_common.append(a)
                else:
                    break
            common = ''.join(new_common)
        
        if common == '':
            break
    
    if not common:
        return text
    
    # Remove common prefix from each line
    result = []
    for line in lines:
        stripped = line.rstrip('\n').rstrip('\r')
        if stripped:  # non-empty line
            if line.startswith(common):
                line = line[len(common):]
        result.append(line)
    
    return ''.join(result)


def wrap(text, width=70):
    """Wrap text to lines of at most width characters. Returns list of lines."""
    # Split into words (collapse whitespace)
    words = text.split()
    
    if not words:
        return []
    
    lines = []
    current_line = []
    current_length = 0
    
    for word in words:
        word_len = len(word)
        if current_line:
            # Would adding this word exceed width?
            if current_length + 1 + word_len <= width:
                current_line.append(word)
                current_length += 1 + word_len
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
                current_length = word_len
        else:
            # First word on line - if word itself exceeds width, still add it
            current_line = [word]
            current_length = word_len
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return lines


def fill(text, width=70):
    """Wrap text and join lines with newlines."""
    return '\n'.join(wrap(text, width))


def shorten(text, width, placeholder='...'):
    """Collapse whitespace and truncate to width with placeholder if needed."""
    # Collapse whitespace
    collapsed = ' '.join(text.split())
    
    if len(collapsed) <= width:
        return collapsed
    
    # Need to truncate
    # We need result to fit in width including placeholder
    placeholder_len = len(placeholder)
    
    if width <= placeholder_len:
        # Can only fit placeholder (or less)
        return placeholder[:width]
    
    # Find the longest prefix of words that fits in width - placeholder_len
    available = width - placeholder_len
    
    words = collapsed.split()
    result_words = []
    current_length = 0
    
    for word in words:
        if current_length == 0:
            # First word
            if len(word) <= available:
                result_words.append(word)
                current_length = len(word)
            else:
                # Even first word doesn't fit
                break
        else:
            if current_length + 1 + len(word) <= available:
                result_words.append(word)
                current_length += 1 + len(word)
            else:
                break
    
    if result_words:
        return ' '.join(result_words) + placeholder
    else:
        return placeholder


# Zero-arg invariant functions

def textwrap3_dedent():
    """Returns dedent('  hello\\n  world')"""
    return dedent('  hello\n  world')


def textwrap3_wrap():
    """Returns True if wrap('hello world', width=5) contains lines of at most 5 chars."""
    lines = wrap('hello world', width=5)
    return all(len(line) <= 5 for line in lines)


def textwrap3_shorten():
    """Returns shorten('hello world', width=8, placeholder='...')"""
    return shorten('hello world', width=8, placeholder='...')