# generation B regex unescape
"""Small clean-room implementation of HTML escaping and unescaping."""

import re


_NAMED = {
    "amp": "&",
    "apos": "'",
    "cent": "\u00a2",
    "copy": "\u00a9",
    "deg": "\u00b0",
    "divide": "\u00f7",
    "euro": "\u20ac",
    "frac12": "\u00bd",
    "frac14": "\u00bc",
    "frac34": "\u00be",
    "gt": ">",
    "hellip": "\u2026",
    "laquo": "\u00ab",
    "ldquo": "\u201c",
    "lsquo": "\u2018",
    "lt": "<",
    "mdash": "\u2014",
    "middot": "\u00b7",
    "nbsp": "\u00a0",
    "ndash": "\u2013",
    "para": "\u00b6",
    "plusmn": "\u00b1",
    "pound": "\u00a3",
    "quot": '"',
    "raquo": "\u00bb",
    "rdquo": "\u201d",
    "reg": "\u00ae",
    "rsquo": "\u2019",
    "sect": "\u00a7",
    "times": "\u00d7",
    "trade": "\u2122",
    "yen": "\u00a5",
}

_C1_REPLACEMENTS = {
    0x80: "\u20ac",
    0x82: "\u201a",
    0x83: "\u0192",
    0x84: "\u201e",
    0x85: "\u2026",
    0x86: "\u2020",
    0x87: "\u2021",
    0x88: "\u02c6",
    0x89: "\u2030",
    0x8A: "\u0160",
    0x8B: "\u2039",
    0x8C: "\u0152",
    0x8E: "\u017d",
    0x91: "\u2018",
    0x92: "\u2019",
    0x93: "\u201c",
    0x94: "\u201d",
    0x95: "\u2022",
    0x96: "\u2013",
    0x97: "\u2014",
    0x98: "\u02dc",
    0x99: "\u2122",
    0x9A: "\u0161",
    0x9B: "\u203a",
    0x9C: "\u0153",
    0x9E: "\u017e",
    0x9F: "\u0178",
}

_REMOVED_CODEPOINTS = {
    0x0B,
    0xFFFE,
    0xFFFF,
}

_REFERENCE_RE = re.compile(
    r"&(?:#[xX][0-9a-fA-F]+;?|#[0-9]+;?|[A-Za-z][A-Za-z0-9]+;?)"
)


def escape(s, quote=True):
    """Replace HTML-significant characters in *s* with safe references."""
    s = s.replace("&", "&amp;")
    s = s.replace("<", "&lt;")
    s = s.replace(">", "&gt;")
    if quote:
        s = s.replace('"', "&quot;")
        s = s.replace("'", "&#x27;")
    return s


def _numeric_reference(value):
    if value == 0 or value > 0x10FFFF or 0xD800 <= value <= 0xDFFF:
        return "\ufffd"
    replacement = _C1_REPLACEMENTS.get(value)
    if replacement is not None:
        return replacement
    if value in _REMOVED_CODEPOINTS:
        return ""
    return chr(value)


def _unescape_match(match):
    """Translate one numeric or named character reference."""
    token = match.group(0)[1:]
    if token.endswith(";"):
        token = token[:-1]

    if token.startswith(("#x", "#X")):
        return _numeric_reference(int(token[2:], 16))
    if token.startswith("#"):
        return _numeric_reference(int(token[1:], 10))

    replacement = _NAMED.get(token)
    if replacement is not None:
        return replacement

    # HTML permits a number of legacy named references without a semicolon.
    # Preserve any unmatched suffix after the longest known name.
    for end in range(len(token) - 1, 1, -1):
        replacement = _NAMED.get(token[:end])
        if replacement is not None:
            return replacement + token[end:]
    return match.group(0)


def unescape(s):
    """Replace named and numeric HTML character references in *s*."""
    if "&" not in s:
        return s
    return _REFERENCE_RE.sub(_unescape_match, s)
