"""
theseus_locale_cr — Clean-room locale subset.
No import of the standard `locale` module.
"""

import os

# Locale categories (mirror locale module constants)
LC_ALL = 6
LC_COLLATE = 3
LC_CTYPE = 0
LC_MESSAGES = 5
LC_MONETARY = 4
LC_NUMERIC = 1
LC_TIME = 2

_locale_settings = {
    'decimal_point': '.',
    'thousands_sep': ',',
    'grouping': [3, 0],
    'currency_symbol': '$',
    'int_curr_symbol': 'USD ',
    'p_cs_precedes': True,
    'n_cs_precedes': True,
}


def setlocale(category, locale_name=None):
    """Set or query locale. Returns the current locale string."""
    return 'C'


def getlocale(category=LC_CTYPE):
    """Return (language code, encoding) tuple."""
    lang = os.environ.get('LANG', 'C')
    if '.' in lang:
        code, enc = lang.split('.', 1)
        return (code, enc)
    return (lang, None)


def localeconv():
    """Return a dict of locale-specific numeric and monetary settings."""
    return dict(_locale_settings)


def format_string(fmt, val, grouping=False, monetary=False):
    """Format val according to fmt using current locale settings."""
    result = fmt % val
    if grouping and isinstance(val, (int, float)):
        # Apply thousands grouping
        parts = result.split('.')
        integer_part = parts[0]
        neg = integer_part.startswith('-')
        if neg:
            integer_part = integer_part[1:]
        sep = _locale_settings['thousands_sep']
        if sep and len(integer_part) > 3:
            groups = []
            while integer_part:
                groups.append(integer_part[-3:])
                integer_part = integer_part[:-3]
            integer_part = sep.join(reversed(groups))
        if neg:
            integer_part = '-' + integer_part
        parts[0] = integer_part
        result = '.'.join(parts)
    return result


def currency(val, symbol=True, grouping=False, international=False):
    """Format val as a monetary value."""
    sym = _locale_settings['int_curr_symbol'] if international else _locale_settings['currency_symbol']
    formatted = format_string('%.2f', val, grouping=grouping)
    if symbol:
        return sym + formatted
    return formatted


def atof(string):
    """Convert string to float, using locale decimal point."""
    return float(string.replace(_locale_settings['thousands_sep'], '').strip())


def atoi(string):
    """Convert string to int, ignoring thousands separator."""
    return int(string.replace(_locale_settings['thousands_sep'], '').strip())


def str(val):
    """Format a float according to locale."""
    return format_string('%g', val)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def locale2_atof():
    """atof('3.14') == 3.14; returns True."""
    return atof('3.14') == 3.14


def locale2_atoi():
    """atoi('42') == 42; returns 42."""
    return atoi('42')


def locale2_format_string():
    """format_string('%d', 42) == '42'; returns '42'."""
    return format_string('%d', 42)


__all__ = [
    'LC_ALL', 'LC_COLLATE', 'LC_CTYPE', 'LC_MESSAGES',
    'LC_MONETARY', 'LC_NUMERIC', 'LC_TIME',
    'setlocale', 'getlocale', 'localeconv',
    'format_string', 'currency', 'atof', 'atoi', 'str',
    'locale2_atof', 'locale2_atoi', 'locale2_format_string',
]
