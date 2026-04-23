"""
theseus_textwrap_cr2 - Clean-room implementation of textwrap functionality.
"""

import re


class TextWrapper:
    """
    Wraps text to a specified width.
    """

    def __init__(self, width=70, initial_indent='', subsequent_indent='',
                 break_long_words=True, break_on_hyphens=True,
                 placeholder='...'):
        self.width = width
        self.initial_indent = initial_indent
        self.subsequent_indent = subsequent_indent
        self.break_long_words = break_long_words
        self.break_on_hyphens = break_on_hyphens
        self.placeholder = placeholder

    def _split_into_chunks(self, text):
        """Split text into words and whitespace chunks."""
        # Split on whitespace, keeping track of words
        chunks = re.split(r'(\s+)', text)
        return [c for c in chunks if c]

    def _wrap_chunks(self, chunks):
        """Wrap chunks into lines."""
        lines = []
        current_line = []
        current_length = 0

        indent = self.initial_indent
        indent_len = len(indent)

        for chunk in chunks:
            chunk_len = len(chunk)

            # Skip pure whitespace at the beginning of a line
            if not current_line and chunk.strip() == '':
                continue

            if current_length + chunk_len <= self.width - indent_len:
                current_line.append(chunk)
                current_length += chunk_len
            else:
                # Need to start a new line
                if current_line:
                    # Strip trailing whitespace from current line
                    line_text = ''.join(current_line).rstrip()
                    if line_text:
                        lines.append(indent + line_text)
                    current_line = []
                    current_length = 0
                    indent = self.subsequent_indent
                    indent_len = len(indent)

                # Skip whitespace at start of new line
                if chunk.strip() == '':
                    continue

                # Handle chunk that's too long for a single line
                if chunk_len > self.width - indent_len:
                    if self.break_long_words:
                        # Break the chunk
                        while chunk:
                            space = self.width - indent_len
                            if space <= 0:
                                space = 1
                            lines.append(indent + chunk[:space])
                            chunk = chunk[space:]
                            indent = self.subsequent_indent
                            indent_len = len(indent)
                    else:
                        # Put it on its own line even if too long
                        lines.append(indent + chunk)
                        indent = self.subsequent_indent
                        indent_len = len(indent)
                else:
                    current_line.append(chunk)
                    current_length = chunk_len

        # Handle remaining content
        if current_line:
            line_text = ''.join(current_line).rstrip()
            if line_text:
                lines.append(indent + line_text)

        return lines

    def wrap(self, text):
        """
        Wrap text and return a list of lines.
        """
        # Normalize whitespace: replace all whitespace sequences with single space
        text = text.strip()
        if not text:
            return []

        # Split into words
        words = text.split()

        if not words:
            return []

        lines = []
        indent = self.initial_indent
        indent_len = len(indent)
        current_line_words = []
        current_length = 0

        for word in words:
            word_len = len(word)
            available = self.width - indent_len

            if not current_line_words:
                # First word on the line
                if word_len <= available:
                    current_line_words.append(word)
                    current_length = word_len
                elif self.break_long_words:
                    # Break the word
                    while word:
                        space = available
                        if space <= 0:
                            space = 1
                        lines.append(indent + word[:space])
                        word = word[space:]
                        indent = self.subsequent_indent
                        indent_len = len(indent)
                        available = self.width - indent_len
                    # After breaking, current_line_words is still empty
                else:
                    # Word too long but don't break
                    lines.append(indent + word)
                    indent = self.subsequent_indent
                    indent_len = len(indent)
                    available = self.width - indent_len
            else:
                # Check if word fits with a space
                if current_length + 1 + word_len <= available:
                    current_line_words.append(word)
                    current_length += 1 + word_len
                else:
                    # Flush current line
                    lines.append(indent + ' '.join(current_line_words))
                    indent = self.subsequent_indent
                    indent_len = len(indent)
                    available = self.width - indent_len
                    current_line_words = []
                    current_length = 0

                    # Place word on new line
                    if word_len <= available:
                        current_line_words.append(word)
                        current_length = word_len
                    elif self.break_long_words:
                        while word:
                            space = available
                            if space <= 0:
                                space = 1
                            lines.append(indent + word[:space])
                            word = word[space:]
                            indent = self.subsequent_indent
                            indent_len = len(indent)
                            available = self.width - indent_len
                    else:
                        lines.append(indent + word)
                        indent = self.subsequent_indent
                        indent_len = len(indent)
                        available = self.width - indent_len

        if current_line_words:
            lines.append(indent + ' '.join(current_line_words))

        return lines

    def fill(self, text):
        """
        Wrap text and return a single string with newlines.
        """
        return '\n'.join(self.wrap(text))


def wrap(text, width=70, **kwargs):
    """
    Wrap text to the specified width and return a list of lines.
    """
    w = TextWrapper(width=width, **kwargs)
    return w.wrap(text)


def fill(text, width=70, **kwargs):
    """
    Wrap text to the specified width and return a single string.
    """
    w = TextWrapper(width=width, **kwargs)
    return w.fill(text)


def shorten(text, width, placeholder='...', **kwargs):
    """
    Collapse and truncate the given text to fit in the given width.
    Appends placeholder if text is truncated.
    """
    # Normalize whitespace
    text = ' '.join(text.split())

    if len(text) <= width:
        return text

    # Need to truncate
    # Find the maximum text we can fit with the placeholder
    max_len = width - len(placeholder)

    if max_len <= 0:
        # Can't even fit the placeholder properly
        return placeholder[:width]

    # Try to cut at a word boundary
    truncated = text[:max_len]

    # Find last space to avoid cutting mid-word
    last_space = truncated.rfind(' ')
    if last_space > 0:
        truncated = truncated[:last_space]
    else:
        # No space found, just cut at max_len
        truncated = truncated.rstrip()

    return truncated + placeholder


def indent(text, prefix, predicate=None):
    """
    Add prefix to the beginning of selected lines in text.
    
    If predicate is provided, prefix is only added to lines where
    predicate(line) is True. Otherwise, prefix is added to all
    non-empty lines (lines that are not just whitespace).
    """
    if predicate is None:
        def predicate(line):
            return line.strip()

    lines = text.splitlines(keepends=True)
    result = []
    for line in lines:
        if predicate(line):
            result.append(prefix + line)
        else:
            result.append(line)

    # Handle case where text doesn't end with newline
    # splitlines with keepends handles this correctly
    return ''.join(result)


def dedent(text):
    """
    Remove any common leading whitespace from all lines in text.
    """
    lines = text.splitlines()

    # Find common leading whitespace
    # Only consider non-empty lines
    non_empty = [line for line in lines if line.strip()]

    if not non_empty:
        return text

    # Find common prefix of whitespace
    def leading_whitespace(s):
        stripped = s.lstrip()
        return s[:len(s) - len(stripped)]

    common = leading_whitespace(non_empty[0])
    for line in non_empty[1:]:
        lw = leading_whitespace(line)
        # Find common prefix
        i = 0
        while i < len(common) and i < len(lw) and common[i] == lw[i]:
            i += 1
        common = common[:i]
        if not common:
            break

    if not common:
        return text

    # Remove common prefix from all lines
    result = []
    for line in lines:
        if line.startswith(common):
            result.append(line[len(common):])
        else:
            result.append(line)

    # Reconstruct with original line endings
    # Check if original text ended with newline
    joined = '\n'.join(result)
    if text.endswith('\n'):
        joined += '\n'
    return joined


# Test functions as specified in the invariants

def textwrap2_wrap_width():
    """TextWrapper(width=10).wrap('hello world') == ['hello', 'world']"""
    return TextWrapper(width=10).wrap('hello world')


def textwrap2_shorten():
    """shorten('Hello world', width=8, placeholder='...') == 'Hello...'"""
    return shorten('Hello world', width=8, placeholder='...')


def textwrap2_indent():
    """indent('hello\nworld', '  ') == '  hello\n  world'"""
    return indent('hello\nworld', '  ')