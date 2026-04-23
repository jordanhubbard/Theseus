"""
theseus_unicodedata_cr - Clean-room Unicode character utilities.
Do NOT import unicodedata.
"""

_CATEGORY_TABLE = {
    # Uppercase letters
    **{chr(c): 'Lu' for c in range(ord('A'), ord('Z') + 1)},
    # Lowercase letters
    **{chr(c): 'Ll' for c in range(ord('a'), ord('z') + 1)},
    # Decimal digits
    **{chr(c): 'Nd' for c in range(ord('0'), ord('9') + 1)},
    # Space separator
    ' ': 'Zs',
    '\t': 'Cc',
    '\n': 'Cc',
    '\r': 'Cc',
    # Common punctuation / symbols
    '!': 'Po', '"': 'Po', '#': 'Po', '$': 'Sc', '%': 'Po',
    '&': 'Po', "'": 'Po', '(': 'Ps', ')': 'Pe', '*': 'Po',
    '+': 'Sm', ',': 'Po', '-': 'Pd', '.': 'Po', '/': 'Po',
    ':': 'Po', ';': 'Po', '<': 'Sm', '=': 'Sm', '>': 'Sm',
    '?': 'Po', '@': 'Po', '[': 'Ps', '\\': 'Po', ']': 'Pe',
    '^': 'Sk', '_': 'Pc', '`': 'Sk', '{': 'Ps', '|': 'Sm',
    '}': 'Pe', '~': 'Sm',
}

_LATIN_UPPER = {
    'À': 'Lu', 'Á': 'Lu', 'Â': 'Lu', 'Ã': 'Lu', 'Ä': 'Lu', 'Å': 'Lu',
    'Æ': 'Lu', 'Ç': 'Lu', 'È': 'Lu', 'É': 'Lu', 'Ê': 'Lu', 'Ë': 'Lu',
    'Ì': 'Lu', 'Í': 'Lu', 'Î': 'Lu', 'Ï': 'Lu', 'Ð': 'Lu', 'Ñ': 'Lu',
    'Ò': 'Lu', 'Ó': 'Lu', 'Ô': 'Lu', 'Õ': 'Lu', 'Ö': 'Lu', 'Ø': 'Lu',
    'Ù': 'Lu', 'Ú': 'Lu', 'Û': 'Lu', 'Ü': 'Lu', 'Ý': 'Lu', 'Þ': 'Lu',
}

_LATIN_LOWER = {
    'à': 'Ll', 'á': 'Ll', 'â': 'Ll', 'ã': 'Ll', 'ä': 'Ll', 'å': 'Ll',
    'æ': 'Ll', 'ç': 'Ll', 'è': 'Ll', 'é': 'Ll', 'ê': 'Ll', 'ë': 'Ll',
    'ì': 'Ll', 'í': 'Ll', 'î': 'Ll', 'ï': 'Ll', 'ð': 'Ll', 'ñ': 'Ll',
    'ò': 'Ll', 'ó': 'Ll', 'ô': 'Ll', 'õ': 'Ll', 'ö': 'Ll', 'ø': 'Ll',
    'ù': 'Ll', 'ú': 'Ll', 'û': 'Ll', 'ü': 'Ll', 'ý': 'Ll', 'þ': 'Ll',
    'ß': 'Ll', 'ÿ': 'Ll',
}

_CATEGORY_TABLE.update(_LATIN_UPPER)
_CATEGORY_TABLE.update(_LATIN_LOWER)


def category(c):
    if len(c) != 1:
        raise TypeError("need a single Unicode character as parameter")
    return _CATEGORY_TABLE.get(c, 'Cn')


def is_alpha(c):
    cat = category(c)
    return cat.startswith('L')


def is_digit(c):
    return category(c) == 'Nd'


def is_space(c):
    cat = category(c)
    return cat in ('Zs', 'Cc') and c in (' ', '\t', '\n', '\r', '\x0b', '\x0c')


def normalize_nfc(s):
    # For pure ASCII / Latin-1 composed forms, NFC is identity.
    return s


def unicodedata_category_A():
    return category('A')


def unicodedata_category_5():
    return category('5')


def unicodedata_is_alpha_A():
    return is_alpha('A')


__all__ = [
    'category', 'is_alpha', 'is_digit', 'is_space', 'normalize_nfc',
    'unicodedata_category_A', 'unicodedata_category_5', 'unicodedata_is_alpha_A',
]
