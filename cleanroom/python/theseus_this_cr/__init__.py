"""Clean-room reimplementation of the `this` module.

Provides the Zen of Python and the ROT13 helpers in a clean-room form
without importing the original `this` module.
"""

# The Zen of Python text, transcribed from public sources (Tim Peters, PEP 20).
_ZEN_TEXT = (
    "The Zen of Python, by Tim Peters\n"
    "\n"
    "Beautiful is better than ugly.\n"
    "Explicit is better than implicit.\n"
    "Simple is better than complex.\n"
    "Complex is better than complicated.\n"
    "Flat is better than nested.\n"
    "Sparse is better than dense.\n"
    "Readability counts.\n"
    "Special cases aren't special enough to break the rules.\n"
    "Although practicality beats purity.\n"
    "Errors should never pass silently.\n"
    "Unless explicitly silenced.\n"
    "In the face of ambiguity, refuse the temptation to guess.\n"
    "There should be one-- and preferably only one --obvious way to do it.\n"
    "Although that way may not be obvious at first unless you're Dutch.\n"
    "Now is better than never.\n"
    "Although never is often better than *right* now.\n"
    "If the implementation is hard to explain, it's a bad idea.\n"
    "If the implementation is easy to explain, it may be a good idea.\n"
    "Namespaces are one honking great idea -- let's do more of those!"
)


def _build_rot13_dict():
    """Build a dict mapping each ASCII letter to its ROT13 counterpart."""
    mapping = {}
    for base in (65, 97):  # 'A' and 'a'
        for i in range(26):
            mapping[chr(i + base)] = chr((i + 13) % 26 + base)
    return mapping


def _rot13(text):
    """Apply ROT13 to a string, leaving non-letters intact."""
    table = _build_rot13_dict()
    return "".join(table.get(ch, ch) for ch in text)


# The ROT13-encoded form of the Zen text — analogous to `this.s`.
_S = _rot13(_ZEN_TEXT)
s = _S
d = _build_rot13_dict()


def decode(text):
    if not isinstance(text, str):
        raise TypeError("decode expects a str")
    return _rot13(text)


def this2_d():
    """Verify the ROT13 mapping dictionary used by the module."""
    return d.get('N') == 'A' and d.get('a') == 'n'


def this2_decode():
    """Verify that the encoded Zen decodes to the expected text."""
    return "Beautiful is better than ugly." in decode(s)


def this2_zen():
    """Verify that the exported ``s`` value contains encoded Zen text."""
    return isinstance(s, str) and s != _ZEN_TEXT and "Ornhgvshy" in s


__all__ = ["s", "d", "decode", "this2_zen", "this2_decode", "this2_d"]
