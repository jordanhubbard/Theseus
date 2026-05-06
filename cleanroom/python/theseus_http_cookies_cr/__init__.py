"""
theseus_http_cookies_cr — Clean-room http.cookies module.
No import of http.cookies.
"""

import re as _re
import string as _string
import time as _time

_LegalKeyChars = r"\w\d!#%&'~_`><@,:/\$\*\+\-\.\^\|\)\(\?\}\{\="
_LegalValueChars = _LegalKeyChars + r'\[\]'
_CookiePattern = _re.compile(
    r'(?x)'                       # Verbose
    r'\s*'                        # Leading spaces
    r'(?P<key>'
    r'[' + _LegalKeyChars + r']+?'
    r')'
    r'\s*=\s*'                    # Equal sign
    r'(?P<val>'
    r'"(?:[^\\"]|\\.)*"'          # Double-quoted
    r'|'
    r'\w{3},\s[\w\d\s-]{9,11}\s[\d:]{8}\sGMT'  # Special case
    r'|'
    r'[' + _LegalValueChars + r']*'  # Unquoted
    r')'
    r'\s*;?',
    _re.ASCII
)

_RESERVED = frozenset({'expires', 'path', 'comment', 'domain', 'max-age',
                        'secure', 'httponly', 'version', 'samesite'})


class CookieError(Exception):
    pass


class Morsel(dict):
    _reserved = {
        'expires': 'expires',
        'path': 'path',
        'comment': 'comment',
        'domain': 'domain',
        'max-age': 'max-age',
        'secure': 'secure',
        'httponly': 'httponly',
        'version': 'version',
        'samesite': 'samesite',
    }
    _flags = frozenset({'secure', 'httponly'})

    def __init__(self):
        super().__init__()
        self._key = None
        self._value = None
        self._coded_value = None
        for key in self._reserved:
            super().__setitem__(key, '')

    @property
    def key(self):
        return self._key

    @property
    def value(self):
        return self._value

    @property
    def coded_value(self):
        return self._coded_value

    def set(self, key, val, coded_val):
        self._key = key
        self._value = val
        self._coded_value = coded_val

    def setdefault(self, key, val=None):
        key = key.lower()
        if key not in self._reserved:
            raise CookieError(f'Invalid attribute {key!r}')
        return super().setdefault(key, val)

    def __setitem__(self, key, val):
        key = key.lower()
        if key not in self._reserved:
            raise CookieError(f'Invalid attribute {key!r}')
        super().__setitem__(key, val)

    def isReservedKey(self, k):
        return k.lower() in self._reserved

    def output(self, attrs=None, header='Set-Cookie:'):
        return f'{header} {self.OutputString(attrs)}'

    def OutputString(self, attrs=None):
        result = []
        append = result.append
        append(f'{self.key}={self.coded_value}')
        if attrs is None:
            attrs = self._reserved
        for key in attrs:
            if key == 'expires' and self[key]:
                append(f'expires={self[key]}')
            elif key == 'max-age' and self[key] != '':
                append(f'max-age={self[key]}')
            elif key in self._flags:
                if self[key]:
                    append(str(key))
            elif self[key]:
                append(f'{key}={self[key]}')
        return '; '.join(result)

    def __repr__(self):
        return f'<Morsel: {self._key}={self._value!r}>'


class BaseCookie(dict):
    def value_decode(self, val):
        return val, val

    def value_encode(self, val):
        strval = str(val)
        return strval, strval

    def __init__(self, input=None):
        super().__init__()
        if input:
            self.load(input)

    def __set(self, key, real_value, coded_value):
        morsel = self.get(key, Morsel())
        morsel.set(key, real_value, coded_value)
        dict.__setitem__(self, key, morsel)

    def __setitem__(self, key, value):
        if isinstance(value, Morsel):
            dict.__setitem__(self, key, value)
        else:
            real_val, coded_val = self.value_encode(value)
            self.__set(key, real_val, coded_val)

    def load(self, rawdata):
        if isinstance(rawdata, str):
            self._load_string(rawdata)
        elif isinstance(rawdata, dict):
            for key, value in rawdata.items():
                self[key] = value

    def _load_string(self, rawdata):
        i = 0
        n = len(rawdata)
        morsel = None
        while i < n:
            m = _CookiePattern.match(rawdata, i)
            if m:
                key, val = m.group('key'), m.group('val')
                i = m.end(0)
                if key.lower() in _RESERVED:
                    if morsel:
                        try:
                            morsel[key.lower()] = _unquote(val)
                        except CookieError:
                            pass
                else:
                    real_val, coded_val = self.value_decode(_unquote(val))
                    morsel = Morsel()
                    morsel.set(key, real_val, coded_val)
                    dict.__setitem__(self, key, morsel)
            else:
                i += 1

    def output(self, attrs=None, header='Set-Cookie:', sep='\r\n'):
        result = []
        for key in sorted(self.keys()):
            result.append(self[key].output(attrs, header))
        return sep.join(result)

    def __repr__(self):
        L = []
        for key, val in sorted(self.items()):
            L.append(f'{key}={val.value!r}')
        return f'<{self.__class__.__name__}: {", ".join(L)}>'

    def js_output(self, attrs=None):
        result = []
        for key in sorted(self.keys()):
            result.append(f'document.cookie = "{self[key].OutputString(attrs)}";\n')
        return ''.join(result)


def _unquote(str):
    if str and str[0] == '"' and str[-1] == '"':
        str = str[1:-1]
        str = str.replace('\\\\', '\\').replace('\\"', '"')
    return str


def _quote(str):
    if not str:
        return str
    needs_quoting = False
    for c in str:
        if c not in _LegalValueChars or c in ' ,;':
            needs_quoting = True
            break
    if needs_quoting:
        return '"' + str.replace('\\', '\\\\').replace('"', '\\"') + '"'
    return str


class SimpleCookie(BaseCookie):
    def value_decode(self, val):
        return _unquote(val), val

    def value_encode(self, val):
        strval = str(val)
        return strval, _quote(strval)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def cookies2_simplecookie():
    """SimpleCookie can set and get a cookie; returns True."""
    c = SimpleCookie()
    c['session'] = 'abc123'
    c['user'] = 'alice'
    return c['session'].value == 'abc123' and c['user'].value == 'alice'


def cookies2_output():
    """SimpleCookie.output() produces Set-Cookie header; returns True."""
    c = SimpleCookie()
    c['token'] = 'xyz789'
    out = c.output()
    return 'Set-Cookie:' in out and 'token' in out


def cookies2_load():
    """SimpleCookie.load() parses a cookie string; returns True."""
    c = SimpleCookie()
    c.load('name=John; age=30')
    return 'name' in c and c['name'].value == 'John'


__all__ = [
    'CookieError', 'Morsel', 'BaseCookie', 'SimpleCookie',
    'cookies2_simplecookie', 'cookies2_output', 'cookies2_load',
]