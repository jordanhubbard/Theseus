"""Clean-room implementation of HTML escape/unescape utilities.

This module provides HTML escaping and unescaping without depending on the
standard library's `html` module. Only Python built-ins are used.
"""

import re as _re


__all__ = [
    "escape",
    "unescape",
    "quote_attr",
    "html2_escape",
    "html2_unescape",
    "html2_quote_attr",
]


# ---------------------------------------------------------------------------
# escape
# ---------------------------------------------------------------------------

def escape(s="", quote=True):
    """Replace special characters "&", "<", ">", and (if quote is True) the
    quote characters '"' and "'" with HTML-safe sequences.
    """
    if not isinstance(s, str):
        s = str(s)
    s = s.replace("&", "&amp;")
    s = s.replace("<", "&lt;")
    s = s.replace(">", "&gt;")
    if quote:
        s = s.replace('"', "&quot;")
        s = s.replace("'", "&#x27;")
    return s


def quote_attr(s=""):
    """Return *s* formatted as a double-quoted HTML attribute value.

    The returned string includes the surrounding double quotes and is fully
    escaped so it is safe to drop into an HTML attribute context.
    """
    if not isinstance(s, str):
        s = str(s)
    return '"' + escape(s, quote=True) + '"'


# ---------------------------------------------------------------------------
# unescape
# ---------------------------------------------------------------------------

# A reasonably comprehensive table of HTML5 named character references.
# Keys are the entity names (without leading '&' or trailing ';').
_NAMED_ENTITIES = {
    # Core XML/HTML
    "amp": "&",
    "AMP": "&",
    "lt": "<",
    "LT": "<",
    "gt": ">",
    "GT": ">",
    "quot": '"',
    "QUOT": '"',
    "apos": "'",
    # Whitespace / latin-1 supplement
    "nbsp": "\u00a0",
    "iexcl": "\u00a1",
    "cent": "\u00a2",
    "pound": "\u00a3",
    "curren": "\u00a4",
    "yen": "\u00a5",
    "brvbar": "\u00a6",
    "sect": "\u00a7",
    "uml": "\u00a8",
    "copy": "\u00a9",
    "COPY": "\u00a9",
    "ordf": "\u00aa",
    "laquo": "\u00ab",
    "not": "\u00ac",
    "shy": "\u00ad",
    "reg": "\u00ae",
    "REG": "\u00ae",
    "macr": "\u00af",
    "deg": "\u00b0",
    "plusmn": "\u00b1",
    "sup2": "\u00b2",
    "sup3": "\u00b3",
    "acute": "\u00b4",
    "micro": "\u00b5",
    "para": "\u00b6",
    "middot": "\u00b7",
    "cedil": "\u00b8",
    "sup1": "\u00b9",
    "ordm": "\u00ba",
    "raquo": "\u00bb",
    "frac14": "\u00bc",
    "frac12": "\u00bd",
    "frac34": "\u00be",
    "iquest": "\u00bf",
    # Accented uppercase
    "Agrave": "\u00c0",
    "Aacute": "\u00c1",
    "Acirc": "\u00c2",
    "Atilde": "\u00c3",
    "Auml": "\u00c4",
    "Aring": "\u00c5",
    "AElig": "\u00c6",
    "Ccedil": "\u00c7",
    "Egrave": "\u00c8",
    "Eacute": "\u00c9",
    "Ecirc": "\u00ca",
    "Euml": "\u00cb",
    "Igrave": "\u00cc",
    "Iacute": "\u00cd",
    "Icirc": "\u00ce",
    "Iuml": "\u00cf",
    "ETH": "\u00d0",
    "Ntilde": "\u00d1",
    "Ograve": "\u00d2",
    "Oacute": "\u00d3",
    "Ocirc": "\u00d4",
    "Otilde": "\u00d5",
    "Ouml": "\u00d6",
    "times": "\u00d7",
    "Oslash": "\u00d8",
    "Ugrave": "\u00d9",
    "Uacute": "\u00da",
    "Ucirc": "\u00db",
    "Uuml": "\u00dc",
    "Yacute": "\u00dd",
    "THORN": "\u00de",
    "szlig": "\u00df",
    # Accented lowercase
    "agrave": "\u00e0",
    "aacute": "\u00e1",
    "acirc": "\u00e2",
    "atilde": "\u00e3",
    "auml": "\u00e4",
    "aring": "\u00e5",
    "aelig": "\u00e6",
    "ccedil": "\u00e7",
    "egrave": "\u00e8",
    "eacute": "\u00e9",
    "ecirc": "\u00ea",
    "euml": "\u00eb",
    "igrave": "\u00ec",
    "iacute": "\u00ed",
    "icirc": "\u00ee",
    "iuml": "\u00ef",
    "eth": "\u00f0",
    "ntilde": "\u00f1",
    "ograve": "\u00f2",
    "oacute": "\u00f3",
    "ocirc": "\u00f4",
    "otilde": "\u00f5",
    "ouml": "\u00f6",
    "divide": "\u00f7",
    "oslash": "\u00f8",
    "ugrave": "\u00f9",
    "uacute": "\u00fa",
    "ucirc": "\u00fb",
    "uuml": "\u00fc",
    "yacute": "\u00fd",
    "thorn": "\u00fe",
    "yuml": "\u00ff",
    # Latin Extended
    "OElig": "\u0152",
    "oelig": "\u0153",
    "Scaron": "\u0160",
    "scaron": "\u0161",
    "Yuml": "\u0178",
    "fnof": "\u0192",
    # Spacing modifier
    "circ": "\u02c6",
    "tilde": "\u02dc",
    # Greek
    "Alpha": "\u0391",
    "Beta": "\u0392",
    "Gamma": "\u0393",
    "Delta": "\u0394",
    "Epsilon": "\u0395",
    "Zeta": "\u0396",
    "Eta": "\u0397",
    "Theta": "\u0398",
    "Iota": "\u0399",
    "Kappa": "\u039a",
    "Lambda": "\u039b",
    "Mu": "\u039c",
    "Nu": "\u039d",
    "Xi": "\u039e",
    "Omicron": "\u039f",
    "Pi": "\u03a0",
    "Rho": "\u03a1",
    "Sigma": "\u03a3",
    "Tau": "\u03a4",
    "Upsilon": "\u03a5",
    "Phi": "\u03a6",
    "Chi": "\u03a7",
    "Psi": "\u03a8",
    "Omega": "\u03a9",
    "alpha": "\u03b1",
    "beta": "\u03b2",
    "gamma": "\u03b3",
    "delta": "\u03b4",
    "epsilon": "\u03b5",
    "zeta": "\u03b6",
    "eta": "\u03b7",
    "theta": "\u03b8",
    "iota": "\u03b9",
    "kappa": "\u03ba",
    "lambda": "\u03bb",
    "mu": "\u03bc",
    "nu": "\u03bd",
    "xi": "\u03be",
    "omicron": "\u03bf",
    "pi": "\u03c0",
    "rho": "\u03c1",
    "sigmaf": "\u03c2",
    "sigma": "\u03c3",
    "tau": "\u03c4",
    "upsilon": "\u03c5",
    "phi": "\u03c6",
    "chi": "\u03c7",
    "psi": "\u03c8",
    "omega": "\u03c9",
    "thetasym": "\u03d1",
    "upsih": "\u03d2",
    "piv": "\u03d6",
    # General punctuation
    "ensp": "\u2002",
    "emsp": "\u2003",
    "thinsp": "\u2009",
    "zwnj": "\u200c",
    "zwj": "\u200d",
    "lrm": "\u200e",
    "rlm": "\u200f",
    "ndash": "\u2013",
    "mdash": "\u2014",
    "lsquo": "\u2018",
    "rsquo": "\u2019",
    "sbquo": "\u201a",
    "ldquo": "\u201c",
    "rdquo": "\u201d",
    "bdquo": "\u201e",
    "dagger": "\u2020",
    "Dagger": "\u2021",
    "bull": "\u2022",
    "hellip": "\u2026",
    "permil": "\u2030",
    "prime": "\u2032",
    "Prime": "\u2033",
    "lsaquo": "\u2039",
    "rsaquo": "\u203a",
    "oline": "\u203e",
    "frasl": "\u2044",
    "euro": "\u20ac",
    # Letterlike / arrows / math
    "image": "\u2111",
    "weierp": "\u2118",
    "real": "\u211c",
    "trade": "\u2122",
    "TRADE": "\u2122",
    "alefsym": "\u2135",
    "larr": "\u2190",
    "uarr": "\u2191",
    "rarr": "\u2192",
    "darr": "\u2193",
    "harr": "\u2194",
    "crarr": "\u21b5",
    "lArr": "\u21d0",
    "uArr": "\u21d1",
    "rArr": "\u21d2",
    "dArr": "\u21d3",
    "hArr": "\u21d4",
    "forall": "\u2200",
    "part": "\u2202",
    "exist": "\u2203",
    "empty": "\u2205",
    "nabla": "\u2207",
    "isin": "\u2208",
    "notin": "\u2209",
    "ni": "\u220b",
    "prod": "\u220f",
    "sum": "\u2211",
    "minus": "\u2212",
    "lowast": "\u2217",
    "radic": "\u221a",
    "prop": "\u221d",
    "infin": "\u221e",
    "ang": "\u2220",
    "and": "\u2227",
    "or": "\u2228",
    "cap": "\u2229",
    "cup": "\u222a",
    "int": "\u222b",
    "there4": "\u2234",
    "sim": "\u223c",
    "cong": "\u2245",
    "asymp": "\u2248",
    "ne": "\u2260",
    "equiv": "\u2261",
    "le": "\u2264",
    "ge": "\u2265",
    "sub": "\u2282",
    "sup": "\u2283",
    "nsub": "\u2284",
    "sube": "\u2286",
    "supe": "\u2287",
    "oplus": "\u2295",
    "otimes": "\u2297",
    "perp": "\u22a5",
    "sdot": "\u22c5",
    "lceil": "\u2308",
    "rceil": "\u2309",
    "lfloor": "\u230a",
    "rfloor": "\u230b",
    "lang": "\u27e8",
    "rang": "\u27e9",
    "loz": "\u25ca",
    "spades": "\u2660",
    "clubs": "\u2663",
    "hearts": "\u2665",
    "diams": "\u2666",
}


# Numeric character reference replacement table for legacy code points
# (these are remapped per the HTML5 spec for compatibility with old documents).
_INVALID_CHARREFS = {
    0x00: "\ufffd",
    0x0d: "\r",
    0x80: "\u20ac",
    0x81: "\x81",
    0x82: "\u201a",
    0x83: "\u0192",
    0x84: "\u201e",
    0x85: "\u2026",
    0x86: "\u2020",
    0x87: "\u2021",
    0x88: "\u02c6",
    0x89: "\u2030",
    0x8a: "\u0160",
    0x8b: "\u2039",
    0x8c: "\u0152",
    0x8d: "\x8d",
    0x8e: "\u017d",
    0x8f: "\x8f",
    0x90: "\x90",
    0x91: "\u2018",
    0x92: "\u2019",
    0x93: "\u201c",
    0x94: "\u201d",
    0x95: "\u2022",
    0x96: "\u2013",
    0x97: "\u2014",
    0x98: "\u02dc",
    0x99: "\u2122",
    0x9a: "\u0161",
    0x9b: "\u203a",
    0x9c: "\u0153",
    0x9d: "\x9d",
    0x9e: "\u017e",
    0x9f: "\u0178",
}


_INVALID_CODEPOINT_RANGES = (
    (0x1, 0x8),
    (0xe, 0x1f),
    (0x7f, 0x9f),
    (0xfdd0, 0xfdef),
)
_INVALID_CODEPOINT_SET = {
    0xb, 0xfffe, 0xffff, 0x1fffe, 0x1ffff, 0x2fffe, 0x2ffff,
    0x3fffe, 0x3ffff, 0x4fffe, 0x4ffff, 0x5fffe, 0x5ffff,
    0x6fffe, 0x6ffff, 0x7fffe, 0x7ffff, 0x8fffe, 0x8ffff,
    0x9fffe, 0x9ffff, 0xafffe, 0xaffff, 0xbfffe, 0xbffff,
    0xcfffe, 0xcffff, 0xdfffe, 0xdffff, 0xefffe, 0xeffff,
    0xffffe, 0xfffff, 0x10fffe, 0x10ffff,
}


def _decode_numeric(num):
    """Decode a numeric character reference to a string, with HTML5 fix-ups."""
    if num in _INVALID_CHARREFS:
        return _INVALID_CHARREFS[num]
    # Surrogate or out-of-range -> replacement char
    if 0xD800 <= num <= 0xDFFF or num > 0x10FFFF:
        return "\ufffd"
    if num in _INVALID_CODEPOINT_SET:
        return "\ufffd"
    for lo, hi in _INVALID_CODEPOINT_RANGES:
        if lo <= num <= hi:
            return "\ufffd"
    try:
        return chr(num)
    except (ValueError, OverflowError):
        return "\ufffd"


# Pattern that matches both numeric (decimal/hex) and named character
# references. The trailing `;` is optional for compatibility with browsers
# (and with the standard library's html.unescape).
_CHARREF_RE = _re.compile(
    r"&(#[0-9]+;?"
    r"|#[xX][0-9a-fA-F]+;?"
    r"|[^\t\n\f <&#;]{1,32};?)"
)


def _replace_charref(match):
    s = match.group(1)
    if s[0] == "#":
        # Numeric character reference
        if s[-1] == ";":
            body = s[1:-1]
        else:
            body = s[1:]
        try:
            if body[:1] in ("x", "X"):
                num = int(body[1:], 16)
            else:
                num = int(body)
        except (ValueError, IndexError):
            return "&" + s
        return _decode_numeric(num)
    # Named entity. Try the longest prefix that resolves to a known entity.
    # The HTML5 spec allows some named entities to omit the trailing `;`,
    # so we try with and without it.
    if s in _NAMED_ENTITIES:
        return _NAMED_ENTITIES[s]
    if s.endswith(";") and s[:-1] in _NAMED_ENTITIES:
        return _NAMED_ENTITIES[s[:-1]]
    # Try shrinking from the right (legacy "&amplt" parsed as "&amp" + "lt")
    for end in range(len(s) - 1, 0, -1):
        cand = s[:end]
        if cand in _NAMED_ENTITIES:
            return _NAMED_ENTITIES[cand] + s[end:]
    return "&" + s


def unescape(s=""):
    """Convert HTML character references in *s* back to their character values.

    Supports decimal (&#NN;), hexadecimal (&#xHH;), and named (&name;)
    references. Unknown references are left untouched.
    """
    if not isinstance(s, str):
        s = str(s)
    if "&" not in s:
        return s
    return _CHARREF_RE.sub(_replace_charref, s)


# ---------------------------------------------------------------------------
# Zero-argument invariant wrappers expected by the clean-room harness.
# ---------------------------------------------------------------------------

def html2_escape():
    return escape("<b>hello & world</b>", quote=False)


def html2_unescape():
    return unescape("&lt;b&gt;hello &amp; world&lt;/b&gt;") == "<b>hello & world</b>"


def html2_quote_attr():
    return escape('"value"', quote=True) == "&quot;value&quot;"
