"""
theseus_textwrap_cr — Clean-room textwrap module.

Pure Python implementation derived only from the public CPython
documentation at https://docs.python.org/3/library/textwrap.html.
The original `textwrap` standard-library source is NOT consulted
and NOT imported here.
"""


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def _expand_tabs(text, tabsize=8):
    """Expand tabs the way ``str.expandtabs`` would, without depending on it
    blindly — implemented column-by-column so behaviour is explicit."""
    out = []
    col = 0
    for ch in text:
        if ch == '\t':
            spaces = tabsize - (col % tabsize) if tabsize > 0 else 0
            out.append(' ' * spaces)
            col += spaces
        elif ch == '\n' or ch == '\r':
            out.append(ch)
            col = 0
        else:
            out.append(ch)
            col += 1
    return ''.join(out)


def _split_words(text):
    """Split *text* into whitespace-separated tokens, discarding the
    whitespace itself."""
    words = []
    buf = []
    for ch in text:
        if ch == ' ' or ch == '\t' or ch == '\n' or ch == '\r' or ch == '\f' or ch == '\v':
            if buf:
                words.append(''.join(buf))
                buf = []
        else:
            buf.append(ch)
    if buf:
        words.append(''.join(buf))
    return words


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def wrap(text, width=70, **kwargs):
    """Wrap *text* to *width*, returning a list of output lines.

    A simplified clean-room equivalent of ``textwrap.wrap``.  Words are
    separated by runs of whitespace; long single words that exceed
    *width* are placed on their own line (no breaking inside a word).
    """
    if width <= 0:
        raise ValueError("invalid width %r (must be > 0)" % (width,))

    expand_tabs = kwargs.get('expand_tabs', True)
    tabsize = kwargs.get('tabsize', 8)
    if expand_tabs:
        text = _expand_tabs(text, tabsize)

    words = _split_words(text)
    if not words:
        return []

    lines = []
    current = []
    current_len = 0
    for word in words:
        if not current:
            current.append(word)
            current_len = len(word)
            continue
        # +1 for the single space joining the previous word and this one.
        if current_len + 1 + len(word) > width:
            lines.append(' '.join(current))
            current = [word]
            current_len = len(word)
        else:
            current.append(word)
            current_len += 1 + len(word)
    if current:
        lines.append(' '.join(current))
    return lines


def fill(text, width=70, **kwargs):
    """Wrap *text* and join the resulting lines with newlines."""
    return '\n'.join(wrap(text, width, **kwargs))


def dedent(text):
    """Remove the longest common leading whitespace from every non-empty
    line in *text*.  Lines that consist solely of whitespace are
    normalised to a bare newline (matching the documented behaviour)."""
    lines = text.splitlines(True)
    if not lines:
        return text

    margin = None
    for line in lines:
        # Strip the trailing newline(s) for the "whitespace-only" check.
        bare = line
        while bare and bare[-1] in '\r\n':
            bare = bare[:-1]
        stripped = bare.lstrip(' \t')
        if not stripped:
            # Whitespace-only line — does not constrain the margin.
            continue
        leading = bare[:len(bare) - len(stripped)]
        if margin is None:
            margin = leading
        elif leading.startswith(margin):
            # current margin is still a prefix; keep it
            pass
        elif margin.startswith(leading):
            margin = leading
        else:
            # Find the common prefix character-by-character.
            common = []
            for a, b in zip(margin, leading):
                if a == b:
                    common.append(a)
                else:
                    break
            margin = ''.join(common)
            if not margin:
                break

    if not margin:
        # Still need to normalise whitespace-only lines per docs.
        out = []
        for line in lines:
            bare = line
            nl = ''
            while bare and bare[-1] in '\r\n':
                nl = bare[-1] + nl
                bare = bare[:-1]
            if bare and bare.strip(' \t') == '':
                out.append(nl)
            else:
                out.append(line)
        return ''.join(out)

    out = []
    n = len(margin)
    for line in lines:
        bare = line
        nl = ''
        while bare and bare[-1] in '\r\n':
            nl = bare[-1] + nl
            bare = bare[:-1]
        if bare.strip(' \t') == '':
            # Whitespace-only line — normalise to just the newline.
            out.append(nl)
        elif bare.startswith(margin):
            out.append(bare[n:] + nl)
        else:
            out.append(line)
    return ''.join(out)


def indent(text, prefix, predicate=None):
    """Add *prefix* to the beginning of each selected line in *text*.

    When *predicate* is ``None`` only lines that contain at least one
    non-whitespace character are prefixed (matching the documented
    default)."""
    if predicate is None:
        def predicate(line):
            return line.strip() != ''

    out = []
    for line in text.splitlines(True):
        if predicate(line):
            out.append(prefix + line)
        else:
            out.append(line)
    return ''.join(out)


def shorten(text, width, placeholder=' ...', **kwargs):
    """Collapse whitespace in *text* and truncate it to fit within
    *width* characters, appending *placeholder* if anything was
    removed."""
    if width <= 0:
        raise ValueError("invalid width %r (must be > 0)" % (width,))

    words = _split_words(text)
    joined = ' '.join(words)
    if len(joined) <= width:
        return joined

    target = width - len(placeholder)
    if target < 0:
        # No room for any text; just return a stripped placeholder.
        return placeholder.lstrip()

    accumulated = []
    cur_len = 0
    for word in words:
        extra = (1 if accumulated else 0) + len(word)
        if cur_len + extra > target:
            break
        accumulated.append(word)
        cur_len += extra

    if not accumulated:
        return placeholder.lstrip()
    return ' '.join(accumulated) + placeholder


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def textwrap2_wrap():
    """``wrap`` should split a long single-spaced sequence of words across
    multiple output lines."""
    lines = wrap('word ' * 20, width=20)
    if not isinstance(lines, list):
        return False
    if len(lines) <= 1:
        return False
    # Every line must respect the width cap.
    if any(len(line) > 20 for line in lines):
        return False
    # Joining lines back together must reconstruct the original words.
    rejoined = ' '.join(lines).split()
    return rejoined == ['word'] * 20


def textwrap2_dedent():
    """``dedent`` should remove common leading whitespace."""
    text = '    hello\n    world'
    if dedent(text) != 'hello\nworld':
        return False
    # Mixed margins: only the common portion is stripped.
    text2 = '    hello\n      world\n'
    if dedent(text2) != 'hello\n  world\n':
        return False
    # Whitespace-only lines do not constrain the margin.
    text3 = '   spam\n\n   eggs\n'
    if dedent(text3) != 'spam\n\neggs\n':
        return False
    return True


def textwrap2_indent():
    """``indent`` should add the prefix only to non-empty lines by default."""
    if indent('hello\nworld\n', '  ') != '  hello\n  world\n':
        return False
    # Empty lines should be left untouched by default.
    if indent('hello\n\nworld\n', '> ') != '> hello\n\n> world\n':
        return False
    # A custom predicate should be honoured.
    res = indent('a\nb\nc\n', '* ', predicate=lambda l: 'b' in l)
    if res != 'a\n* b\nc\n':
        return False
    return True


def textwrap2_fill():
    """``fill`` should join wrapped lines with newlines."""
    result = fill('word ' * 20, width=20)
    return isinstance(result, str) and '\n' in result


__all__ = [
    'wrap', 'fill', 'dedent', 'indent', 'shorten',
    'textwrap2_wrap', 'textwrap2_dedent', 'textwrap2_indent', 'textwrap2_fill',
]