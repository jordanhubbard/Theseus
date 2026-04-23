"""
theseus_urllib_parse - Clean-room URL parsing implementation.
No imports of urllib, urllib.parse, or any URL library.
"""

# Characters that do not need to be percent-encoded (unreserved characters)
_UNRESERVED = frozenset(
    'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    'abcdefghijklmnopqrstuvwxyz'
    '0123456789'
    '-._~'
)

# Safe characters for path components
_PATH_SAFE = frozenset(_UNRESERVED | set('/:@!$&\'()*+,;='))

# Safe characters for query components
_QUERY_SAFE = frozenset(_UNRESERVED | set('/:@!$&\'()*+,;=?'))


def quote(s, safe='/', encoding='utf-8', errors='strict'):
    """
    Percent-encode a string. Characters not in the safe set or unreserved
    characters are encoded as %XX.
    
    Args:
        s: The string to encode.
        safe: Characters that should not be encoded (default '/').
        encoding: The encoding to use (default 'utf-8').
        errors: Error handling for encoding (default 'strict').
    
    Returns:
        The percent-encoded string.
    """
    if isinstance(s, str):
        s_bytes = s.encode(encoding, errors)
    elif isinstance(s, bytes):
        s_bytes = s
    else:
        raise TypeError(f"quote() expected str or bytes, got {type(s).__name__}")
    
    safe_chars = frozenset(_UNRESERVED | set(safe))
    
    result = []
    for byte in s_bytes:
        char = chr(byte)
        if char in safe_chars:
            result.append(char)
        else:
            result.append(f'%{byte:02X}')
    
    return ''.join(result)


def quote_plus(s, safe='', encoding='utf-8', errors='strict'):
    """
    Like quote(), but also replaces spaces with plus signs.
    
    Args:
        s: The string to encode.
        safe: Characters that should not be encoded.
        encoding: The encoding to use.
        errors: Error handling for encoding.
    
    Returns:
        The percent-encoded string with spaces as '+'.
    """
    if ' ' in s:
        s = quote(s, safe=safe + ' ', encoding=encoding, errors=errors)
        return s.replace(' ', '+')
    return quote(s, safe=safe, encoding=encoding, errors=errors)


def unquote(s, encoding='utf-8', errors='replace'):
    """
    Replace %XX escapes with their single-character equivalent.
    
    Args:
        s: The string to decode.
        encoding: The encoding to use.
        errors: Error handling for decoding.
    
    Returns:
        The decoded string.
    """
    if '%' not in s:
        return s
    
    result = []
    i = 0
    while i < len(s):
        if s[i] == '%' and i + 2 < len(s):
            hex_str = s[i+1:i+3]
            try:
                byte_val = int(hex_str, 16)
                result.append(bytes([byte_val]))
                i += 3
            except ValueError:
                result.append(s[i].encode(encoding))
                i += 1
        else:
            result.append(s[i].encode(encoding))
            i += 1
    
    return b''.join(result).decode(encoding, errors)


def unquote_plus(s, encoding='utf-8', errors='replace'):
    """
    Like unquote(), but also replaces plus signs with spaces.
    
    Args:
        s: The string to decode.
        encoding: The encoding to use.
        errors: Error handling for decoding.
    
    Returns:
        The decoded string with '+' replaced by spaces.
    """
    return unquote(s.replace('+', ' '), encoding=encoding, errors=errors)


def urlparse(url):
    """
    Parse a URL into its components.
    
    Args:
        url: The URL string to parse.
    
    Returns:
        A dict with keys: scheme, netloc, path, query, fragment.
    """
    result = {
        'scheme': '',
        'netloc': '',
        'path': '',
        'query': '',
        'fragment': '',
    }
    
    if not url:
        return result
    
    # Extract fragment
    if '#' in url:
        url, result['fragment'] = url.split('#', 1)
    
    # Extract query
    if '?' in url:
        url, result['query'] = url.split('?', 1)
    
    # Extract scheme
    # A scheme is letters followed by '://'
    scheme = ''
    rest = url
    
    # Look for scheme: pattern (letters/digits/+/-/. followed by colon)
    colon_pos = url.find(':')
    if colon_pos > 0:
        potential_scheme = url[:colon_pos]
        # Scheme must start with a letter and contain only letters, digits, +, -, .
        valid_scheme = True
        for i, ch in enumerate(potential_scheme):
            if i == 0:
                if not ch.isalpha():
                    valid_scheme = False
                    break
            else:
                if not (ch.isalnum() or ch in '+-. '):
                    valid_scheme = False
                    break
        
        if valid_scheme and colon_pos > 0:
            scheme = potential_scheme.lower()
            rest = url[colon_pos + 1:]
            result['scheme'] = scheme
    
    # Extract netloc (authority) - present when URL starts with '//'
    if rest.startswith('//'):
        rest = rest[2:]
        # netloc ends at the next '/'
        slash_pos = rest.find('/')
        if slash_pos == -1:
            result['netloc'] = rest
            rest = ''
        else:
            result['netloc'] = rest[:slash_pos]
            rest = rest[slash_pos:]
    
    result['path'] = rest
    
    return result


def urlunparse(components):
    """
    Combine the components of a URL into a URL string.
    
    Args:
        components: A dict or tuple/list with URL components.
                    If dict: keys scheme, netloc, path, query, fragment.
                    If tuple/list: (scheme, netloc, path, params, query, fragment).
    
    Returns:
        The assembled URL string.
    """
    if isinstance(components, dict):
        scheme = components.get('scheme', '')
        netloc = components.get('netloc', '')
        path = components.get('path', '')
        query = components.get('query', '')
        fragment = components.get('fragment', '')
    else:
        # Assume tuple/list: (scheme, netloc, path, params, query, fragment)
        scheme = components[0] if len(components) > 0 else ''
        netloc = components[1] if len(components) > 1 else ''
        path = components[2] if len(components) > 2 else ''
        query = components[4] if len(components) > 4 else ''
        fragment = components[5] if len(components) > 5 else ''
    
    url = ''
    if scheme:
        url += scheme + ':'
    if netloc:
        url += '//' + netloc
    url += path
    if query:
        url += '?' + query
    if fragment:
        url += '#' + fragment
    
    return url


def urlencode(params, doseq=False, safe='', encoding='utf-8', errors='strict', quote_via=None):
    """
    Convert a dict or sequence of two-element tuples to a percent-encoded query string.
    
    Args:
        params: A dict or list of (key, value) pairs.
        doseq: If True, handle sequences as multiple values for the same key.
        safe: Characters that should not be encoded.
        encoding: The encoding to use.
        errors: Error handling for encoding.
        quote_via: Function to use for quoting (default: quote_plus).
    
    Returns:
        The URL-encoded query string.
    """
    if quote_via is None:
        quote_via = quote_plus
    
    if isinstance(params, dict):
        items = list(params.items())
    else:
        items = list(params)
    
    pairs = []
    for key, value in items:
        if isinstance(key, bytes):
            key = key.decode(encoding, errors)
        else:
            key = str(key)
        
        if doseq and isinstance(value, (list, tuple)):
            for v in value:
                if isinstance(v, bytes):
                    v = v.decode(encoding, errors)
                else:
                    v = str(v)
                pairs.append(
                    quote_via(key, safe=safe, encoding=encoding, errors=errors) +
                    '=' +
                    quote_via(v, safe=safe, encoding=encoding, errors=errors)
                )
        else:
            if isinstance(value, bytes):
                value = value.decode(encoding, errors)
            else:
                value = str(value)
            pairs.append(
                quote_via(key, safe=safe, encoding=encoding, errors=errors) +
                '=' +
                quote_via(value, safe=safe, encoding=encoding, errors=errors)
            )
    
    return '&'.join(pairs)


def parse_qs(qs, keep_blank_values=False, strict_parsing=False, encoding='utf-8', errors='replace'):
    """
    Parse a query string into a dict of lists.
    
    Args:
        qs: The query string to parse.
        keep_blank_values: If True, keep blank values.
        strict_parsing: If True, raise errors on bad syntax.
        encoding: The encoding to use.
        errors: Error handling for decoding.
    
    Returns:
        A dict mapping keys to lists of values.
    """
    result = {}
    pairs = parse_qsl(qs, keep_blank_values=keep_blank_values,
                      strict_parsing=strict_parsing,
                      encoding=encoding, errors=errors)
    for key, value in pairs:
        if key in result:
            result[key].append(value)
        else:
            result[key] = [value]
    return result


def parse_qsl(qs, keep_blank_values=False, strict_parsing=False, encoding='utf-8', errors='replace'):
    """
    Parse a query string into a list of (key, value) pairs.
    
    Args:
        qs: The query string to parse.
        keep_blank_values: If True, keep blank values.
        strict_parsing: If True, raise errors on bad syntax.
        encoding: The encoding to use.
        errors: Error handling for decoding.
    
    Returns:
        A list of (key, value) tuples.
    """
    pairs = []
    
    if not qs:
        return pairs
    
    # Split on & and ;
    tokens = []
    current = []
    for ch in qs:
        if ch in '&;':
            tokens.append(''.join(current))
            current = []
        else:
            current.append(ch)
    if current:
        tokens.append(''.join(current))
    
    for token in tokens:
        if not token:
            if strict_parsing:
                raise ValueError("bad query field: %r" % token)
            continue
        
        if '=' in token:
            key, value = token.split('=', 1)
        else:
            if strict_parsing:
                raise ValueError("bad query field: %r" % token)
            key = token
            value = ''
        
        key = unquote_plus(key, encoding=encoding, errors=errors)
        value = unquote_plus(value, encoding=encoding, errors=errors)
        
        if not value and not keep_blank_values:
            continue
        
        pairs.append((key, value))
    
    return pairs


def urljoin(base, url, allow_fragments=True):
    """
    Join a base URL and a possibly relative URL to form an absolute URL.
    
    Args:
        base: The base URL.
        url: The URL to join with the base.
        allow_fragments: If True, allow fragment identifiers.
    
    Returns:
        The joined URL.
    """
    if not base:
        return url
    if not url:
        return base
    
    base_parts = urlparse(base)
    url_parts = urlparse(url)
    
    # If url has a scheme, it's absolute
    if url_parts['scheme']:
        if not allow_fragments:
            url_parts['fragment'] = ''
        return urlunparse(url_parts)
    
    result = {
        'scheme': base_parts['scheme'],
        'netloc': '',
        'path': '',
        'query': '',
        'fragment': '',
    }
    
    # If url has netloc, use it
    if url_parts['netloc']:
        result['netloc'] = url_parts['netloc']
        result['path'] = url_parts['path']
        result['query'] = url_parts['query']
    else:
        result['netloc'] = base_parts['netloc']
        
        if url_parts['path']:
            if url_parts['path'].startswith('/'):
                # Absolute path
                result['path'] = url_parts['path']
            else:
                # Relative path - merge with base path
                base_path = base_parts['path']
                # Remove everything after the last '/' in base path
                last_slash = base_path.rfind('/')
                if last_slash >= 0:
                    base_dir = base_path[:last_slash + 1]
                else:
                    base_dir = ''
                result['path'] = base_dir + url_parts['path']
            
            # Resolve . and .. in path
            result['path'] = _resolve_path(result['path'])
            result['query'] = url_parts['query']
        else:
            result['path'] = base_parts['path']
            if url_parts['query']:
                result['query'] = url_parts['query']
            else:
                result['query'] = base_parts['query']
    
    if allow_fragments:
        result['fragment'] = url_parts['fragment']
    
    return urlunparse(result)


def _resolve_path(path):
    """
    Resolve . and .. components in a URL path.
    
    Args:
        path: The path to resolve.
    
    Returns:
        The resolved path.
    """
    if not path:
        return path
    
    # Split path into segments
    segments = path.split('/')
    resolved = []
    
    for segment in segments:
        if segment == '.':
            pass  # Skip current directory references
        elif segment == '..':
            if resolved and resolved[-1] != '':
                resolved.pop()
        else:
            resolved.append(segment)
    
    return '/'.join(resolved)


# --- Functions required by invariants ---

def urlparse_scheme():
    """
    Parse 'https://example.com/path?q=1' and return the scheme 'https'.
    
    Returns:
        The scheme 'https'.
    """
    result = urlparse('https://example.com/path?q=1')
    return result['scheme']


def urlencode_has_a1():
    """
    Check that urlencode({'a': '1', 'b': '2'}) contains 'a=1'.
    
    Returns:
        True if the encoded string contains 'a=1'.
    """
    encoded = urlencode({'a': '1', 'b': '2'})
    return 'a=1' in encoded


def quote_space_encoded():
    """
    Check that quote(' hello') encodes the space character.
    
    Returns:
        True if the space is encoded (either as %20 or +).
    """
    result = quote(' hello')
    return '%20' in result or '+' in result


__all__ = [
    'urlparse',
    'urlunparse',
    'urlencode',
    'quote',
    'quote_plus',
    'unquote',
    'unquote_plus',
    'parse_qs',
    'parse_qsl',
    'urljoin',
    'urlparse_scheme',
    'urlencode_has_a1',
    'quote_space_encoded',
]