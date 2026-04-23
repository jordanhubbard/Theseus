"""
theseus_urllib_parse_cr2 - Clean-room URL parsing utilities.
No import of urllib or urllib.parse allowed.
"""

import re


# ---------------------------------------------------------------------------
# Percent-encoding helpers
# ---------------------------------------------------------------------------

_SAFE_CHARS = (
    'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    'abcdefghijklmnopqrstuvwxyz'
    '0123456789'
    '_.-~'
)

_SAFE_SET = frozenset(_SAFE_CHARS)


def _quote(s, safe=''):
    """Percent-encode a string, leaving 'safe' characters unencoded."""
    if isinstance(s, str):
        encoded = s.encode('utf-8')
    else:
        encoded = bytes(s)

    safe_set = _SAFE_SET | frozenset(safe)
    result = []
    for byte in encoded:
        ch = chr(byte)
        if ch in safe_set:
            result.append(ch)
        else:
            result.append('%{:02X}'.format(byte))
    return ''.join(result)


def _unquote(s):
    """Decode percent-encoded characters in a string."""
    if '%' not in s:
        return s

    # Replace '+' with space (application/x-www-form-urlencoded)
    s = s.replace('+', ' ')

    parts = s.split('%')
    result = [parts[0]]
    for part in parts[1:]:
        if len(part) >= 2:
            hex_chars = part[:2]
            try:
                byte_val = int(hex_chars, 16)
                result.append(bytes([byte_val]).decode('latin-1'))
                result.append(part[2:])
            except ValueError:
                result.append('%')
                result.append(part)
        else:
            result.append('%')
            result.append(part)

    raw = ''.join(result)
    # Now handle multi-byte UTF-8 sequences
    # Re-encode as latin-1 bytes and decode as utf-8 where possible
    try:
        return raw.encode('latin-1').decode('utf-8')
    except (UnicodeDecodeError, UnicodeEncodeError):
        return raw


def _quote_plus(s, safe=''):
    """Like _quote but encodes spaces as '+'."""
    return _quote(s, safe=safe).replace('%20', '+')


def _unquote_plus(s):
    """Like _unquote but treats '+' as space."""
    return _unquote(s.replace('+', ' '))


# ---------------------------------------------------------------------------
# urlencode
# ---------------------------------------------------------------------------

def urlencode(query, doseq=False):
    """
    Encode a dict or sequence of two-element tuples into a URL query string.

    Parameters
    ----------
    query : dict or list of (key, value) pairs
    doseq : bool
        If True, individual sequences are encoded as multiple key=value pairs.

    Returns
    -------
    str
        URL-encoded query string, e.g. 'a=1&b=2'.
    """
    if isinstance(query, dict):
        pairs = list(query.items())
    else:
        pairs = list(query)

    parts = []
    for key, value in pairs:
        key_enc = _quote_plus(str(key))
        if doseq and isinstance(value, (list, tuple)):
            for v in value:
                parts.append('{}={}'.format(key_enc, _quote_plus(str(v))))
        else:
            parts.append('{}={}'.format(key_enc, _quote_plus(str(value))))

    return '&'.join(parts)


# ---------------------------------------------------------------------------
# parse_qsl
# ---------------------------------------------------------------------------

def parse_qsl(qs, keep_blank_values=False, strict_parsing=False):
    """
    Parse a query string into a list of (key, value) pairs.

    Parameters
    ----------
    qs : str
        Query string (without leading '?').
    keep_blank_values : bool
        If True, blank values are retained.
    strict_parsing : bool
        If True, raise ValueError on errors; otherwise silently ignore.

    Returns
    -------
    list of (str, str)
    """
    if not qs:
        return []

    pairs = []
    # Split on '&' or ';'
    for token in re.split(r'[&;]', qs):
        if not token:
            if strict_parsing:
                raise ValueError('bad query field: {!r}'.format(token))
            continue

        if '=' in token:
            key, _, value = token.partition('=')
        else:
            if strict_parsing:
                raise ValueError('bad query field: {!r}'.format(token))
            key = token
            value = ''

        key = _unquote_plus(key)
        value = _unquote_plus(value)

        if not keep_blank_values and not value and not key:
            continue

        pairs.append((key, value))

    return pairs


# ---------------------------------------------------------------------------
# parse_qs
# ---------------------------------------------------------------------------

def parse_qs(qs, keep_blank_values=False, strict_parsing=False):
    """
    Parse a query string into a dict mapping keys to lists of values.

    Parameters
    ----------
    qs : str
        Query string (without leading '?').
    keep_blank_values : bool
    strict_parsing : bool

    Returns
    -------
    dict mapping str -> list of str
    """
    result = {}
    for key, value in parse_qsl(qs, keep_blank_values=keep_blank_values,
                                  strict_parsing=strict_parsing):
        if key in result:
            result[key].append(value)
        else:
            result[key] = [value]
    return result


# ---------------------------------------------------------------------------
# URL splitting helpers
# ---------------------------------------------------------------------------

# RFC 3986 URI splitting regex
_URI_RE = re.compile(
    r'^(?:([a-zA-Z][a-zA-Z0-9+\-.]*):)?'   # scheme
    r'(//([^/?#]*))?'                         # authority (group 2 = //auth, group 3 = auth)
    r'([^?#]*)'                               # path
    r'(?:\?([^#]*))?'                         # query
    r'(?:#(.*))?$'                            # fragment
)


def _split_url(url):
    """
    Split a URL into (scheme, authority, path, query, fragment).
    All components are strings (empty string if absent, not None).
    """
    m = _URI_RE.match(url)
    if not m:
        return ('', '', url, '', '')
    scheme = m.group(1) or ''
    authority = m.group(3) or ''
    path = m.group(4) or ''
    query = m.group(5) if m.group(5) is not None else ''
    fragment = m.group(6) if m.group(6) is not None else ''
    return (scheme.lower(), authority, path, query, fragment)


def _has_authority(url):
    """Return True if the URL string contains an authority component (//)."""
    m = _URI_RE.match(url)
    return m is not None and m.group(2) is not None


def _unsplit_url(scheme, authority, path, query, fragment):
    """Reconstruct a URL from its components."""
    result = ''
    if scheme:
        result += scheme + ':'
    if authority:
        result += '//' + authority
    result += path
    if query:
        result += '?' + query
    if fragment:
        result += '#' + fragment
    return result


def _remove_dot_segments(path):
    """
    Remove '.' and '..' segments from a URL path per RFC 3986 Section 5.2.4.
    """
    # Input buffer
    inp = path
    out = []

    while inp:
        # A: If the input buffer begins with a prefix of "../" or "./"
        if inp.startswith('../'):
            inp = inp[3:]
        elif inp.startswith('./'):
            inp = inp[2:]
        # B: If the input buffer begins with a prefix of "/./" or "/."
        elif inp.startswith('/./'):
            inp = '/' + inp[3:]
        elif inp == '/.':
            inp = '/'
        # C: If the input buffer begins with a prefix of "/../" or "/.."
        elif inp.startswith('/../'):
            inp = '/' + inp[4:]
            if out:
                out.pop()
        elif inp == '/..':
            inp = '/'
            if out:
                out.pop()
        # D: if the input buffer consists only of "." or ".."
        elif inp in ('.', '..'):
            inp = ''
        # E: move the first path segment (including initial "/" if any) to output
        else:
            if inp.startswith('/'):
                seg_start = 0
                seg_end = inp.find('/', 1)
                if seg_end == -1:
                    seg_end = len(inp)
            else:
                seg_start = 0
                seg_end = inp.find('/')
                if seg_end == -1:
                    seg_end = len(inp)
            out.append(inp[seg_start:seg_end])
            inp = inp[seg_end:]

    return ''.join(out)


# ---------------------------------------------------------------------------
# urljoin
# ---------------------------------------------------------------------------

def urljoin(base, url):
    """
    Resolve a relative URL against a base URL.

    Parameters
    ----------
    base : str
        The base URL.
    url : str
        The URL to resolve (may be relative or absolute).

    Returns
    -------
    str
        The resolved absolute URL.
    """
    if not base:
        return url
    if not url:
        return base

    # Parse both URLs
    b_scheme, b_authority, b_path, b_query, b_fragment = _split_url(base)
    r_scheme, r_authority, r_path, r_query, r_fragment = _split_url(url)

    # Check if url has an explicit scheme
    # We need to detect if the original url string has a scheme
    # by checking the raw regex match
    m = _URI_RE.match(url)
    url_has_scheme = m is not None and m.group(1) is not None
    url_has_authority = m is not None and m.group(2) is not None

    if url_has_scheme:
        t_scheme = r_scheme
        t_authority = r_authority
        t_path = _remove_dot_segments(r_path)
        t_query = r_query
    else:
        if url_has_authority:
            t_authority = r_authority
            t_path = _remove_dot_segments(r_path)
            t_query = r_query
        else:
            if not r_path:
                t_path = b_path
                if r_query:
                    t_query = r_query
                else:
                    t_query = b_query
            else:
                if r_path.startswith('/'):
                    t_path = _remove_dot_segments(r_path)
                else:
                    # Merge paths
                    if b_authority and not b_path:
                        t_path = '/' + r_path
                    else:
                        # Replace everything after last '/' in base path
                        last_slash = b_path.rfind('/')
                        if last_slash >= 0:
                            t_path = b_path[:last_slash + 1] + r_path
                        else:
                            t_path = r_path
                    t_path = _remove_dot_segments(t_path)
                t_query = r_query
            t_authority = b_authority
        t_scheme = b_scheme

    t_fragment = r_fragment

    return _unsplit_url(t_scheme, t_authority, t_path, t_query, t_fragment)


# ---------------------------------------------------------------------------
# Self-test helpers referenced in the invariants
# ---------------------------------------------------------------------------

def urllib2_urlencode():
    """Return urlencode({'key': 'val'})."""
    return urlencode({'key': 'val'})


def urllib2_parse_qs():
    return parse_qs('a=1')


def urllib2_urljoin():
    return urljoin('http://x.com/a/', 'b')


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    'urlencode',
    'parse_qs',
    'parse_qsl',
    'urljoin',
    'urllib2_urlencode',
    'urllib2_parse_qs',
    'urllib2_urljoin',
]