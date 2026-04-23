"""
theseus_urllib_parse_cr — Clean-room urllib.parse module.
No import of the standard `urllib.parse` module.
"""

import re as _re

_SCHEME_RE = _re.compile(r'^([a-zA-Z][a-zA-Z0-9+\-.]*):(.*)$', _re.DOTALL)
_AUTHORITY_RE = _re.compile(r'^//([^/?#]*)(.*)$', _re.DOTALL)
_USES_NETLOC = frozenset(['ftp', 'http', 'https', 'gopher', 'nntp', 'telnet', 'imap',
                           'wais', 'mms', 'svn', 'svn+ssh', 'sftp', 'nfs', 'git', 'git+ssh',
                           'ws', 'wss', 'thrift'])

_SAFE_CHARS = frozenset(
    'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    'abcdefghijklmnopqrstuvwxyz'
    '0123456789'
    '_.-~'
)
_SAFE_PATH = _SAFE_CHARS | frozenset('/:@!$&\'()*+,;=')


class ParseResult:
    __slots__ = ('scheme', 'netloc', 'path', 'params', 'query', 'fragment')

    def __init__(self, scheme, netloc, path, params, query, fragment):
        self.scheme = scheme
        self.netloc = netloc
        self.path = path
        self.params = params
        self.query = query
        self.fragment = fragment

    def geturl(self):
        return urlunparse((self.scheme, self.netloc, self.path,
                           self.params, self.query, self.fragment))

    def __repr__(self):
        return (f'ParseResult(scheme={self.scheme!r}, netloc={self.netloc!r}, '
                f'path={self.path!r}, params={self.params!r}, '
                f'query={self.query!r}, fragment={self.fragment!r})')


class SplitResult:
    __slots__ = ('scheme', 'netloc', 'path', 'query', 'fragment')

    def __init__(self, scheme, netloc, path, query, fragment):
        self.scheme = scheme
        self.netloc = netloc
        self.path = path
        self.query = query
        self.fragment = fragment

    def geturl(self):
        return urlunsplit((self.scheme, self.netloc, self.path,
                           self.query, self.fragment))


def urlsplit(urlstring, scheme='', allow_fragments=True):
    netloc = query = fragment = ''
    i = urlstring.find(':')
    if i > 0:
        rest = urlstring[i + 1:]
        s = urlstring[:i].lower()
        if s.isalpha() or (s[:1].isalpha() and all(c.isalnum() or c in '+.-' for c in s[1:])):
            scheme = s
            urlstring = rest

    if urlstring[:2] == '//':
        netloc, urlstring = _splitnetloc(urlstring, 2)

    if allow_fragments and '#' in urlstring:
        urlstring, fragment = urlstring.split('#', 1)

    if '?' in urlstring:
        urlstring, query = urlstring.split('?', 1)

    return SplitResult(scheme, netloc, urlstring, query, fragment)


def _splitnetloc(url, start=0):
    delim = len(url)
    for c in '/?#':
        wdelim = url.find(c, start)
        if wdelim >= 0:
            delim = min(delim, wdelim)
    return url[start:delim], url[delim:]


def urlparse(urlstring, scheme='', allow_fragments=True):
    splitresult = urlsplit(urlstring, scheme, allow_fragments)
    scheme, netloc, url, query, fragment = (splitresult.scheme, splitresult.netloc,
                                             splitresult.path, splitresult.query,
                                             splitresult.fragment)
    params = ''
    if ';' in url:
        url, params = url.split(';', 1)
    return ParseResult(scheme, netloc, url, params, query, fragment)


def urlunparse(components):
    scheme, netloc, url, params, query, fragment = components
    if params:
        url = f'{url};{params}'
    return urlunsplit((scheme, netloc, url, query, fragment))


def urlunsplit(components):
    scheme, netloc, url, query, fragment = components
    if netloc or (scheme and scheme in _USES_NETLOC and url[:2] != '//'):
        if url and url[:1] != '/':
            url = '/' + url
        url = '//' + (netloc or '') + url
    if scheme:
        url = scheme + ':' + url
    if query:
        url = url + '?' + query
    if fragment:
        url = url + '#' + fragment
    return url


def urljoin(base, url, allow_fragments=True):
    if not base:
        return url
    if not url:
        return base

    bscheme, bnetloc, bpath, bparams, bquery, bfragment = urlparse(base, '', allow_fragments)
    scheme, netloc, path, params, query, fragment = urlparse(url, bscheme, allow_fragments)

    if scheme != bscheme or scheme not in _USES_NETLOC:
        return urlunparse((scheme, netloc, path, params, query, fragment))
    if netloc:
        path = _resolve_dots(path)
        return urlunparse((scheme, netloc, path, params, query, fragment))
    netloc = bnetloc

    if not path:
        path = bpath
        if not params:
            params = bparams
        if not query:
            query = bquery
        return urlunparse((scheme, netloc, path, params, query, fragment))

    base_parts = bpath.split('/')
    if base_parts[-1]:
        del base_parts[-1]

    path_parts = base_parts + path.split('/')
    path = '/'.join(path_parts)
    path = _resolve_dots(path)
    return urlunparse((scheme, netloc, path, params, query, fragment))


def _resolve_dots(path):
    """Resolve . and .. in path."""
    parts = path.split('/')
    result = []
    for part in parts:
        if part == '..':
            if result and result[-1] != '':
                result.pop()
        elif part != '.':
            result.append(part)
    return '/'.join(result)


def quote(string, safe='/', encoding=None, errors=None):
    """Percent-encode a string."""
    if isinstance(string, str):
        if encoding is None:
            encoding = 'utf-8'
        string = string.encode(encoding, errors or 'strict')

    safe_set = _SAFE_CHARS | frozenset(safe.encode('ascii') if isinstance(safe, str) else safe)
    result = []
    for byte in string:
        c = chr(byte)
        if c in safe_set or byte in safe_set:
            result.append(c)
        else:
            result.append(f'%{byte:02X}')
    return ''.join(result)


def quote_plus(string, safe='', encoding=None, errors=None):
    """Like quote() but also replace spaces with '+'."""
    if ' ' in string:
        string = quote(string, safe + ' ', encoding, errors)
        return string.replace(' ', '+')
    return quote(string, safe, encoding, errors)


def unquote(string, encoding='utf-8', errors='replace'):
    """Replace percent-encoded sequences with their characters."""
    if '%' not in string:
        return string
    parts = string.split('%')
    result = [parts[0]]
    for item in parts[1:]:
        try:
            result.append(chr(int(item[:2], 16)))
            result.append(item[2:])
        except ValueError:
            result.append('%')
            result.append(item)
    return ''.join(result)


def unquote_plus(string, encoding='utf-8', errors='replace'):
    """Like unquote() but also replace '+' with spaces."""
    string = string.replace('+', ' ')
    return unquote(string, encoding, errors)


def urlencode(query, doseq=False, safe='', encoding=None, errors=None, quote_via=quote_plus):
    """Encode a dict or sequence of pairs as a URL query string."""
    if hasattr(query, 'items'):
        query = list(query.items())
    pairs = []
    for k, v in query:
        k_enc = quote_via(str(k), safe)
        if doseq and isinstance(v, (list, tuple)):
            for val in v:
                pairs.append(f'{k_enc}={quote_via(str(val), safe)}')
        else:
            pairs.append(f'{k_enc}={quote_via(str(v), safe)}')
    return '&'.join(pairs)


def parse_qs(qs, keep_blank_values=False, strict_parsing=False,
             encoding='utf-8', errors='replace', max_num_fields=None):
    """Parse query string, return dict with lists of values."""
    pairs = parse_qsl(qs, keep_blank_values, strict_parsing, encoding, errors, max_num_fields)
    result = {}
    for k, v in pairs:
        result.setdefault(k, []).append(v)
    return result


def parse_qsl(qs, keep_blank_values=False, strict_parsing=False,
              encoding='utf-8', errors='replace', max_num_fields=None):
    """Parse query string, return list of (key, value) pairs."""
    pairs = []
    for name_value in qs.split('&'):
        if not name_value and not strict_parsing:
            continue
        nv = name_value.split('=', 1)
        if len(nv) != 2:
            if strict_parsing:
                raise ValueError(f"bad query field: {name_value!r}")
            nv.append('')
        name = unquote_plus(nv[0], encoding, errors)
        value = unquote_plus(nv[1], encoding, errors)
        if keep_blank_values or value:
            pairs.append((name, value))
    return pairs


def urldefrag(url):
    """Remove fragment from URL, return (url_without_fragment, fragment)."""
    if '#' in url:
        s, n, p, pa, q, frag = urlparse(url)
        defrag = urlunparse((s, n, p, pa, q, ''))
        return defrag, frag
    return url, ''


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def urllib_parse2_urlparse():
    """urlparse extracts scheme, netloc, path; returns True."""
    r = urlparse('https://example.com/path/to/page?q=1#anchor')
    return r.scheme == 'https' and r.netloc == 'example.com' and r.path == '/path/to/page'


def urllib_parse2_urlencode():
    """urlencode produces valid query string; returns True."""
    result = urlencode({'key': 'value', 'foo': 'bar'})
    return 'key=value' in result and 'foo=bar' in result


def urllib_parse2_quote():
    """quote('hello world') returns 'hello%20world'; returns 'hello%20world'."""
    return quote('hello world', safe='')


__all__ = [
    'urlparse', 'urlunparse', 'urlsplit', 'urlunsplit',
    'urljoin', 'urldefrag',
    'quote', 'quote_plus', 'unquote', 'unquote_plus',
    'urlencode', 'parse_qs', 'parse_qsl',
    'ParseResult', 'SplitResult',
    'urllib_parse2_urlparse', 'urllib_parse2_urlencode', 'urllib_parse2_quote',
]
