"""
Clean-room implementation of urllib.parse utilities.
No import of urllib or urllib.parse allowed.
"""

# Characters that are safe and do not need percent-encoding
# Unreserved characters: ALPHA / DIGIT / "-" / "." / "_" / "~"
_UNRESERVED = frozenset(
    'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    'abcdefghijklmnopqrstuvwxyz'
    '0123456789'
    '-._~'
)

# Safe characters for query strings (also allow '=' and '&' to be encoded by caller)
_QUERY_SAFE = frozenset(
    'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    'abcdefghijklmnopqrstuvwxyz'
    '0123456789'
    '-._~'
)


def quote(string, safe='/', encoding=None, errors=None):
    """Percent-encode a string."""
    if encoding is None:
        encoding = 'utf-8'
    if errors is None:
        errors = 'strict'
    
    if isinstance(string, str):
        encoded = string.encode(encoding, errors)
    else:
        encoded = string
    
    safe_chars = frozenset(safe) | _UNRESERVED
    
    result = []
    for byte in encoded:
        char = chr(byte)
        if char in safe_chars:
            result.append(char)
        else:
            result.append('%{:02X}'.format(byte))
    
    return ''.join(result)


def unquote(string, encoding='utf-8', errors='replace'):
    """Replace %xx escapes with their single-character equivalent."""
    if '%' not in string:
        return string
    
    result = []
    i = 0
    while i < len(string):
        if string[i] == '%' and i + 2 < len(string):
            hex_str = string[i+1:i+3]
            try:
                byte_val = int(hex_str, 16)
                result.append(byte_val)
                i += 3
                continue
            except ValueError:
                pass
        char = string[i]
        if isinstance(char, str):
            for b in char.encode(encoding, errors):
                result.append(b)
        i += 1
    
    return bytes(result).decode(encoding, errors)


def quote_plus(string, safe='', encoding=None, errors=None):
    """Like quote(), but also replace spaces with plus signs."""
    if ' ' in string:
        string = quote(string, safe=safe + ' ', encoding=encoding, errors=errors)
        return string.replace(' ', '+')
    return quote(string, safe=safe, encoding=encoding, errors=errors)


def unquote_plus(string, encoding='utf-8', errors='replace'):
    """Like unquote(), but also replace plus signs with spaces."""
    string = string.replace('+', ' ')
    return unquote(string, encoding=encoding, errors=errors)


def urlencode(query, doseq=False, safe='', encoding=None, errors=None, quote_via=None):
    """
    Encode a mapping or sequence of (key, value) pairs to a query string.
    """
    if quote_via is None:
        quote_via = quote_plus
    
    if hasattr(query, 'items'):
        query = list(query.items())
    
    pairs = []
    for k, v in query:
        k_enc = quote_via(str(k), safe=safe, encoding=encoding, errors=errors)
        if doseq and isinstance(v, (list, tuple)):
            for item in v:
                v_enc = quote_via(str(item), safe=safe, encoding=encoding, errors=errors)
                pairs.append(k_enc + '=' + v_enc)
        else:
            v_enc = quote_via(str(v), safe=safe, encoding=encoding, errors=errors)
            pairs.append(k_enc + '=' + v_enc)
    
    return '&'.join(pairs)


def parse_qsl(qs, keep_blank_values=False, strict_parsing=False, encoding='utf-8', errors='replace', max_num_fields=None):
    """
    Parse a query string given as a string argument (data of type
    application/x-www-form-urlencoded). Data are returned as a list of
    name, value pairs.
    """
    pairs = []
    if not qs:
        return pairs
    
    # Split on & or ;
    fields = qs.split('&')
    
    if max_num_fields is not None and len(fields) > max_num_fields:
        raise ValueError('Max number of fields exceeded')
    
    for field in fields:
        if not field:
            continue
        if '=' in field:
            key, value = field.split('=', 1)
        else:
            if strict_parsing:
                raise ValueError('bad query field: {!r}'.format(field))
            key = field
            value = ''
        
        key = unquote_plus(key, encoding=encoding, errors=errors)
        value = unquote_plus(value, encoding=encoding, errors=errors)
        
        if not keep_blank_values and not value:
            continue
        
        pairs.append((key, value))
    
    return pairs


def parse_qs(qs, keep_blank_values=False, strict_parsing=False, encoding='utf-8', errors='replace', max_num_fields=None):
    """
    Parse a query string given as a string argument (data of type
    application/x-www-form-urlencoded). Data are returned as a dictionary.
    The dictionary keys are the unique query variable names and the values
    are lists of values for each name.
    """
    parsed = parse_qsl(
        qs,
        keep_blank_values=keep_blank_values,
        strict_parsing=strict_parsing,
        encoding=encoding,
        errors=errors,
        max_num_fields=max_num_fields
    )
    result = {}
    for key, value in parsed:
        if key in result:
            result[key].append(value)
        else:
            result[key] = [value]
    return result


class ParseResult:
    """Result of urlparse()."""
    
    __slots__ = ('scheme', 'netloc', 'path', 'params', 'query', 'fragment')
    
    def __init__(self, scheme, netloc, path, params, query, fragment):
        self.scheme = scheme
        self.netloc = netloc
        self.path = path
        self.params = params
        self.query = query
        self.fragment = fragment
    
    def __iter__(self):
        yield self.scheme
        yield self.netloc
        yield self.path
        yield self.params
        yield self.query
        yield self.fragment
    
    def __getitem__(self, index):
        return list(self)[index]
    
    def __repr__(self):
        return (
            'ParseResult(scheme={!r}, netloc={!r}, path={!r}, '
            'params={!r}, query={!r}, fragment={!r})'
        ).format(self.scheme, self.netloc, self.path,
                 self.params, self.query, self.fragment)
    
    def geturl(self):
        return urlunparse(self)


def urlparse(urlstring, scheme='', allow_fragments=True):
    """
    Parse a URL into six components:
    <scheme>://<netloc>/<path>;<params>?<query>#<fragment>
    """
    url = urlstring
    fragment = ''
    query = ''
    params = ''
    
    # Extract fragment
    if allow_fragments and '#' in url:
        url, fragment = url.split('#', 1)
    
    # Extract query
    if '?' in url:
        url, query = url.split('?', 1)
    
    # Extract scheme
    netloc = ''
    if '://' in url:
        scheme_part, rest = url.split('://', 1)
        # Validate scheme: must be alpha + alphanumeric/+/-/.
        if _is_valid_scheme(scheme_part):
            scheme = scheme_part.lower()
            url = rest
            # Extract netloc
            if '/' in url:
                netloc, url = url.split('/', 1)
                url = '/' + url
            else:
                netloc = url
                url = ''
    elif url.startswith('//'):
        rest = url[2:]
        if '/' in rest:
            netloc, url = rest.split('/', 1)
            url = '/' + url
        else:
            netloc = rest
            url = ''
    
    # Extract params (;params at end of path)
    if ';' in url:
        url, params = url.split(';', 1)
    
    path = url
    
    return ParseResult(scheme, netloc, path, params, query, fragment)


def _is_valid_scheme(s):
    """Check if s is a valid URL scheme."""
    if not s:
        return False
    if not s[0].isalpha():
        return False
    for c in s[1:]:
        if not (c.isalnum() or c in '+-. '):
            return False
    return True


def urlunparse(components):
    """
    Reconstruct a URL from a tuple (scheme, netloc, path, params, query, fragment).
    """
    scheme, netloc, path, params, query, fragment = components
    
    url = ''
    
    if scheme:
        url += scheme + ':'
    
    if netloc:
        url += '//' + netloc
    
    if path:
        url += path
    elif netloc:
        # If there's a netloc but no path, we need at least a /
        # only if query or params follow
        pass
    
    if params:
        url += ';' + params
    
    if query:
        # Ensure there's a path separator before query
        if not path and netloc:
            url += '/'
        url += '?' + query
    
    if fragment:
        url += '#' + fragment
    
    return url


def urlsplit(urlstring, scheme='', allow_fragments=True):
    """
    Similar to urlparse(), but does not split the params from the URL.
    Returns a 5-tuple: (scheme, netloc, path, query, fragment).
    """
    result = urlparse(urlstring, scheme=scheme, allow_fragments=allow_fragments)
    # Combine path and params back
    path = result.path
    if result.params:
        path = path + ';' + result.params
    
    class SplitResult:
        __slots__ = ('scheme', 'netloc', 'path', 'query', 'fragment')
        
        def __init__(self, scheme, netloc, path, query, fragment):
            self.scheme = scheme
            self.netloc = netloc
            self.path = path
            self.query = query
            self.fragment = fragment
        
        def __iter__(self):
            yield self.scheme
            yield self.netloc
            yield self.path
            yield self.query
            yield self.fragment
        
        def __getitem__(self, index):
            return list(self)[index]
        
        def geturl(self):
            return urlunsplit(self)
    
    return SplitResult(result.scheme, result.netloc, path, result.query, result.fragment)


def urlunsplit(components):
    """
    Combine the elements of a tuple as returned by urlsplit() into a complete URL.
    """
    scheme, netloc, path, query, fragment = components
    
    url = ''
    
    if scheme:
        url += scheme + ':'
    
    if netloc:
        url += '//' + netloc
    
    if path:
        url += path
    
    if query:
        if not path and netloc:
            url += '/'
        url += '?' + query
    
    if fragment:
        url += '#' + fragment
    
    return url


# ---- Invariant functions ----

def urlparse4_unparse():
    """urlunparse(('http','x.com','/','','a=1','')) == 'http://x.com/?a=1'"""
    return urlunparse(('http', 'x.com', '/', '', 'a=1', ''))


def urlparse4_parse_qs_list():
    """parse_qs('a=1&a=2')['a'] == ['1', '2']"""
    return parse_qs('a=1&a=2')['a']


def urlparse4_urlencode_list():
    """urlencode([('a','1'),('b','2')]) == 'a=1&b=2'"""
    return urlencode([('a', '1'), ('b', '2')])