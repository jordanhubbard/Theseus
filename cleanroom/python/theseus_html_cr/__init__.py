"""
theseus_html_cr — Clean-room html module.
No import of the standard `html` module.
"""

_HTML_ESCAPE_TABLE = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
}

_HTML_ESCAPE_QUOTE_TABLE = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
}

_HTML_UNESCAPE_TABLE = {
    '&amp;': '&',
    '&lt;': '<',
    '&gt;': '>',
    '&quot;': '"',
    '&apos;': "'",
    '&nbsp;': '\xa0',
    '&copy;': '\xa9',
    '&reg;': '\xae',
    '&trade;': '\u2122',
    '&mdash;': '\u2014',
    '&ndash;': '\u2013',
    '&laquo;': '\xab',
    '&raquo;': '\xbb',
    '&ldquo;': '\u201c',
    '&rdquo;': '\u201d',
    '&lsquo;': '\u2018',
    '&rsquo;': '\u2019',
    '&hellip;': '\u2026',
    '&bull;': '\u2022',
    '&euro;': '\u20ac',
    '&pound;': '\xa3',
    '&yen;': '\xa5',
    '&cent;': '\xa2',
    '&deg;': '\xb0',
    '&plusmn;': '\xb1',
    '&times;': '\xd7',
    '&divide;': '\xf7',
    '&frac12;': '\xbd',
    '&frac14;': '\xbc',
    '&frac34;': '\xbe',
    '&hearts;': '\u2665',
    '&spades;': '\u2660',
    '&clubs;': '\u2663',
    '&diams;': '\u2666',
}


def escape(s, quote=True):
    """Replace special characters &, <, >, and optionally \" with HTML-safe sequences."""
    table = _HTML_ESCAPE_QUOTE_TABLE if quote else _HTML_ESCAPE_TABLE
    result = []
    for c in s:
        result.append(table.get(c, c))
    return ''.join(result)


def unescape(s):
    """Convert HTML entities and character references to the corresponding Unicode characters."""
    import re as _re

    def replace_entity(m):
        entity = m.group(0)
        # Numeric character references
        if entity.startswith('&#'):
            try:
                if entity[2:3].lower() == 'x':
                    return chr(int(entity[3:-1], 16))
                else:
                    return chr(int(entity[2:-1]))
            except (ValueError, OverflowError):
                return entity
        # Named character references
        return _HTML_UNESCAPE_TABLE.get(entity, entity)

    return _re.sub(r'&#?[a-zA-Z0-9]+;', replace_entity, s)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def html2_escape():
    """escape('<b>hello & world</b>') escapes < > &; returns escaped string."""
    return escape('<b>hello & world</b>')


def html2_unescape():
    """unescape reverses escape; returns True."""
    original = '<b>hello & world</b>'
    return unescape(escape(original)) == original


def html2_quote_attr():
    """escape with quote=True also escapes double quotes; returns True."""
    result = escape('"value"', quote=True)
    return '&quot;' in result


__all__ = [
    'escape', 'unescape',
    'html2_escape', 'html2_unescape', 'html2_quote_attr',
]
