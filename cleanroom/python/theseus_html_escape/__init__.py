"""
theseus_html_escape — Clean-room HTML entity escaping.
No import of html, html.parser, or any HTML library.
"""

_ESCAPE_MAP = {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#x27;"}
_UNESCAPE_MAP = {v: k for k, v in _ESCAPE_MAP.items()}
_UNESCAPE_MAP["&#39;"] = "'"


def escape(s: str) -> str:
    out = []
    for ch in s:
        out.append(_ESCAPE_MAP.get(ch, ch))
    return "".join(out)


def unescape(s: str) -> str:
    for entity, char in _UNESCAPE_MAP.items():
        s = s.replace(entity, char)
    return s


def html_escape_lt_gt() -> str:
    return escape("<script>")


def html_escape_amp() -> str:
    return escape("a & b")


def html_unescape_lt() -> str:
    return unescape("&lt;b&gt;")
