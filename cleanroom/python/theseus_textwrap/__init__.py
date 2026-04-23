"""
theseus_textwrap - Clean-room implementation of text wrapping utilities.
No import of textwrap or any text formatting library.
"""


def wrap(text, width=70):
    """
    Wrap text to the given width, returning a list of lines.
    Each line will be at most `width` characters long.
    Words are split on whitespace.
    """
    if not text or not text.strip():
        return []
    
    # Split text into words (handles multiple spaces, tabs, newlines)
    words = text.split()
    
    if not words:
        return []
    
    lines = []
    current_line = []
    current_length = 0
    
    for word in words:
        word_len = len(word)
        
        if current_line:
            # Check if adding this word (with a space) exceeds width
            if current_length + 1 + word_len <= width:
                current_line.append(word)
                current_length += 1 + word_len
            else:
                # Finish current line and start a new one
                lines.append(' '.join(current_line))
                current_line = [word]
                current_length = word_len
        else:
            # Starting a new line
            if word_len <= width:
                current_line = [word]
                current_length = word_len
            else:
                # Word is longer than width; break it up
                while word_len > width:
                    lines.append(word[:width])
                    word = word[width:]
                    word_len = len(word)
                if word:
                    current_line = [word]
                    current_length = word_len
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return lines


def fill(text, width=70):
    """
    Wrap text to the given width and return a single string with
    lines joined by newlines.
    """
    return '\n'.join(wrap(text, width))


def dedent(text):
    """
    Remove any common leading whitespace from all lines in text.
    
    Lines that consist solely of whitespace are ignored when determining
    the common leading whitespace, but they are still dedented.
    """
    if not text:
        return text
    
    lines = text.split('\n')
    
    # Find common leading whitespace among non-empty lines
    # (lines that have at least one non-whitespace character)
    non_empty_lines = [line for line in lines if line.strip()]
    
    if not non_empty_lines:
        return text
    
    # Find the common prefix of whitespace
    def leading_whitespace(line):
        stripped = line.lstrip()
        return line[:len(line) - len(stripped)]
    
    common = leading_whitespace(non_empty_lines[0])
    
    for line in non_empty_lines[1:]:
        lws = leading_whitespace(line)
        # Find common prefix between current common and this line's whitespace
        new_common = []
        for c1, c2 in zip(common, lws):
            if c1 == c2:
                new_common.append(c1)
            else:
                break
        common = ''.join(new_common)
        if not common:
            break
    
    if not common:
        return text
    
    # Remove the common prefix from each line
    common_len = len(common)
    result_lines = []
    for line in lines:
        if line.startswith(common):
            result_lines.append(line[common_len:])
        elif not line.strip():
            # Whitespace-only line: remove as much as possible
            result_lines.append(line.lstrip() if len(line) <= common_len else line[common_len:])
        else:
            result_lines.append(line)
    
    return '\n'.join(result_lines)


# Test helper / invariant verification functions

def textwrap_wrap_is_list(text=None, width=70):
    """
    Returns True if wrap() returns a list for the given text and width.
    """
    if text is None:
        text = "The quick brown fox jumps over the lazy dog"
    result = wrap(text, width)
    return isinstance(result, list)


def textwrap_fill_has_newline(text=None, width=70):
    """
    Returns True if fill() on multi-word text that needs wrapping
    produces a string containing a newline character.
    For short text that fits on one line, returns True as long as
    fill() returns a string (no newline required for single-line output).
    """
    if text is None:
        # Use text that will definitely need wrapping at default width
        text = ("The quick brown fox jumps over the lazy dog. " * 3).strip()
    result = fill(text, width)
    if not isinstance(result, str):
        return False
    # Check that the result is a string; newline presence depends on wrapping
    lines = wrap(text, width)
    if len(lines) > 1:
        return '\n' in result
    return True


def textwrap_dedent_basic():
    return dedent("  hello")