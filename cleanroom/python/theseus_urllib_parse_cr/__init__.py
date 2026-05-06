"""Clean-room implementation of a urllib.parse subset.

No imports from urllib.* or any third-party library. Uses only Python
built-ins.
"""

# ---------------------------------------------------------------------------
# Character classes
# ---------------------------------------------------------------------------

_ALWAYS_SAFE = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
    "0123456789"
    "_.-~"
)

_HEXDIG = "0123456789ABCDEF"

_SCHEME_CHARS = set(
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789"
    "+-."
)

# Schemes that have an authority (//host) component.
_USES_NETLOC = frozenset((
    "", "ftp", "http", "gopher", "nntp", "telnet", "imap", "wais",
    "file", "mms", "https", "shttp", "snews", "prospero", "rtsp",
    "rtspu", "rsync", "svn", "svn+ssh", "sftp", "nfs", "git",
    "git+ssh", "ws", "wss",
))

# Schemes for which relative-reference resolution applies.
_USES_RELATIVE = frozenset((
    "", "ftp", "http", "gopher", "nntp", "imap", "wais", "file",
    "https", "shttp", "mms", "prospero", "rtsp", "rtspu", "sftp",
    "svn", "svn+ssh", "ws", "wss",
))


def _is_hex(c):
    return ("0" <= c <= "9") or ("a" <= c <= "f") or ("A" <= c <= "F")


# ---------------------------------------------------------------------------
# ParseResult
# ---------------------------------------------------------------------------

class ParseResult(tuple):
    """Result of urlparse: (scheme, netloc, path, params, query, fragment)."""

    __slots__ = ()

    def __new__(cls, scheme="", netloc="", path="", params="",
                query="", fragment=""):
        return tuple.__new__(cls,
                             (scheme, netloc, path, params, query, fragment))

    @property
    def scheme(self):   return self[0]
    @property
    def netloc(self):   return self[1]
    @property
    def path(self):     return self[2]
    @property
    def params(self):   return self[3]
    @property
    def query(self):    return self[4]
    @property
    def fragment(self): return self[5]

    @property
    def username(self):
        netloc = self.netloc
        if "@" in netloc:
            userinfo = netloc.rsplit("@", 1)[0]
            if ":" in userinfo:
                return userinfo.split(":", 1)[0]
            return userinfo
        return None

    @property
    def password(self):
        netloc = self.netloc
        if "@" in netloc:
            userinfo = netloc.rsplit("@", 1)[0]
            if ":" in userinfo:
                return userinfo.split(":", 1)[1]
        return None

    @property
    def hostname(self):
        netloc = self.netloc
        if "@" in netloc:
            netloc = netloc.rsplit("@", 1)[1]
        if netloc.startswith("["):
            end = netloc.find("]")
            if end != -1:
                return netloc[1:end].lower()
        if ":" in netloc:
            netloc = netloc.split(":", 1)[0]
        return netloc.lower() if netloc else None

    @property
    def port(self):
        netloc = self.netloc
        if "@" in netloc:
            netloc = netloc.rsplit("@", 1)[1]
        if netloc.startswith("["):
            end = netloc.find("]")
            if end != -1:
                rest = netloc[end + 1:]
                if rest.startswith(":"):
                    try:
                        p = int(rest[1:])
                    except ValueError:
                        return None
                    if 0 <= p <= 65535:
                        return p
                return None
        if ":" in netloc:
            try:
                p = int(netloc.rsplit(":", 1)[1])
            except ValueError:
                return None
            if 0 <= p <= 65535:
                return p
        return None

    def geturl(self):
        return urlunparse(self)


# ---------------------------------------------------------------------------
# urlparse / urlunparse
# ---------------------------------------------------------------------------

def _split_scheme(url):
    """Return (scheme_lower, rest). Empty scheme on failure."""
    if not url:
        return "", url
    c = url[0]
    if not (("a" <= c <= "z") or ("A" <= c <= "Z")):
        return "", url
    n = len(url)
    i = 1
    while i < n:
        c = url[i]
        if c == ":":
            return url[:i].lower(), url[i + 1:]
        if c not in _SCHEME_CHARS:
            return "", url
        i += 1
    return "", url


def urlparse(urlstring="", scheme="", allow_fragments=True):
    """Parse a URL into 6 components."""
    if urlstring is None:
        urlstring = ""

    if isinstance(urlstring, (bytes, bytearray)):
        url = bytes(urlstring).decode("ascii")
        is_bytes = True
        if isinstance(scheme, (bytes, bytearray)):
            scheme = bytes(scheme).decode("ascii")
    else:
        url = urlstring
        is_bytes = False

    parsed_scheme, rest = _split_scheme(url)
    if parsed_scheme:
        url_scheme = parsed_scheme
        remainder = rest
    else:
        url_scheme = scheme
        remainder = url

    netloc = ""
    if remainder.startswith("//"):
        end = len(remainder)
        for i in range(2, len(remainder)):
            if remainder[i] in "/?#":
                end = i
                break
        netloc = remainder[2:end]
        remainder = remainder[end:]

    fragment = ""
    if allow_fragments and "#" in remainder:
        remainder, fragment = remainder.split("#", 1)

    query = ""
    if "?" in remainder:
        remainder, query = remainder.split("?", 1)

    params = ""
    path = remainder
    if ";" in path:
        path, params = path.split(";", 1)

    if is_bytes:
        return ParseResult(
            url_scheme.encode("ascii"),
            netloc.encode("ascii"),
            path.encode("ascii"),
            params.encode("ascii"),
            query.encode("ascii"),
            fragment.encode("ascii"),
        )
    return ParseResult(url_scheme, netloc, path, params, query, fragment)


def urlunparse(components=("", "", "", "", "", "")):
    """Reassemble a URL from 6 components."""
    scheme, netloc, path, params, query, fragment = components
    is_bytes = isinstance(scheme, (bytes, bytearray)) or \
        isinstance(netloc, (bytes, bytearray)) or \
        isinstance(path, (bytes, bytearray))

    if is_bytes:
        def _s(x):
            if isinstance(x, (bytes, bytearray)):
                return bytes(x).decode("ascii")
            return x or ""
        scheme = _s(scheme)
        netloc = _s(netloc)
        path = _s(path)
        params = _s(params)
        query = _s(query)
        fragment = _s(fragment)

    if params:
        path = path + ";" + params

    url = path
    if netloc or (scheme and scheme in _USES_NETLOC and url[:2] != "//"):
        if url and not url.startswith("/"):
            url = "/" + url
        url = "//" + (netloc or "") + url
    if scheme:
        url = scheme + ":" + url
    if query:
        url = url + "?" + query
    if fragment:
        url = url + "#" + fragment

    if is_bytes:
        return url.encode("ascii")
    return url


# ---------------------------------------------------------------------------
# quote / unquote
# ---------------------------------------------------------------------------

def quote(string="", safe="/", encoding=None, errors=None):
    """Percent-encode a string. Returns 'hello%20world' for 'hello world'."""
    if string is None or string == "":
        return ""

    if isinstance(string, (bytes, bytearray)):
        if encoding is not None:
            raise TypeError("quote() doesn't support 'encoding' for bytes")
        if errors is not None:
            raise TypeError("quote() doesn't support 'errors' for bytes")
        data = bytes(string)
    else:
        if encoding is None:
            encoding = "utf-8"
        if errors is None:
            errors = "strict"
        data = string.encode(encoding, errors)

    if isinstance(safe, (bytes, bytearray)):
        safe_str = bytes(safe).decode("ascii", "replace")
    else:
        safe_str = safe

    safe_set = set(_ALWAYS_SAFE) | set(safe_str)

    out = []
    for byte in data:
        c = chr(byte)
        if byte < 128 and c in safe_set:
            out.append(c)
        else:
            out.append("%" + _HEXDIG[byte >> 4] + _HEXDIG[byte & 0x0F])
    return "".join(out)


def quote_plus(string="", safe="", encoding=None, errors=None):
    """Like quote() but space → '+'."""
    if string is None or string == "" or string == b"":
        return ""
    if isinstance(string, str) and " " not in string:
        return quote(string, safe, encoding, errors)
    if isinstance(string, (bytes, bytearray)) and b" " not in bytes(string):
        return quote(string, safe, encoding, errors)

    if isinstance(safe, (bytes, bytearray)):
        safe = bytes(safe) + b" "
    else:
        safe = (safe or "") + " "
    return quote(string, safe, encoding, errors).replace(" ", "+")


def quote_from_bytes(bs=b"", safe="/"):
    if not isinstance(bs, (bytes, bytearray)):
        raise TypeError("quote_from_bytes() expected bytes")
    return quote(bytes(bs), safe)


def unquote_to_bytes(string=b""):
    """Decode a percent-encoded string to bytes."""
    if not string:
        return b""
    if isinstance(string, str):
        string = string.encode("utf-8", "surrogateescape")
    elif isinstance(string, bytearray):
        string = bytes(string)

    if b"%" not in string:
        return string

    out = bytearray()
    i = 0
    n = len(string)
    while i < n:
        b = string[i]
        if b == 0x25 and i + 2 < n:  # '%' and at least 2 hex chars
            h1 = string[i + 1]
            h2 = string[i + 2]
            try:
                ch1 = chr(h1) if h1 < 128 else "?"
                ch2 = chr(h2) if h2 < 128 else "?"
                if _is_hex(ch1) and _is_hex(ch2):
                    out.append(int(string[i + 1:i + 3], 16))
                    i += 3
                    continue
            except (ValueError, UnicodeDecodeError):
                pass
        out.append(b)
        i += 1
    return bytes(out)


def unquote(string="", encoding="utf-8", errors="replace"):
    """Decode percent-encoded sequences back to characters."""
    if string is None or string == "":
        return string if string is not None else ""
    if isinstance(string, (bytes, bytearray)):
        return unquote_to_bytes(string).decode(encoding, errors)
    if "%" not in string:
        return string
    if encoding is None:
        encoding = "utf-8"
    if errors is None:
        errors = "replace"

    parts = []
    i = 0
    n = len(string)
    while i < n:
        ch = string[i]
        if (ch == "%" and i + 2 < n
                and _is_hex(string[i + 1]) and _is_hex(string[i + 2])):
            # Collect run of consecutive %HH so multi-byte UTF-8 decodes
            # correctly across them.
            buf = bytearray()
            j = i
            while (j + 2 < n and string[j] == "%"
                   and _is_hex(string[j + 1]) and _is_hex(string[j + 2])):
                buf.append(int(string[j + 1:j + 3], 16))
                j += 3
            parts.append(buf.decode(encoding, errors))
            i = j
        else:
            parts.append(ch)
            i += 1
    return "".join(parts)


def unquote_plus(string="", encoding="utf-8", errors="replace"):
    """Like unquote() but '+' → ' '."""
    if string is None or string == "":
        return "" if string is not None else None
    if isinstance(string, (bytes, bytearray)):
        return unquote(bytes(string).replace(b"+", b" "), encoding, errors)
    return unquote(string.replace("+", " "), encoding, errors)


# ---------------------------------------------------------------------------
# urlencode / parse_qs / parse_qsl
# ---------------------------------------------------------------------------

def urlencode(query=None, doseq=False, safe="", encoding=None, errors=None,
              quote_via=quote_plus):
    """Encode a mapping or sequence of pairs as a URL query string."""
    if query is None:
        return ""
    if isinstance(query, (str, bytes)):
        # Strings are not valid query objects per CPython; mirror that.
        raise TypeError(
            "not a valid non-string sequence or mapping object")

    if hasattr(query, "items"):
        items = list(query.items())
    else:
        try:
            items = list(query)
        except TypeError:
            raise TypeError(
                "not a valid non-string sequence or mapping object")

    parts = []
    for item in items:
        try:
            k, v = item
        except (TypeError, ValueError):
            raise TypeError(
                "not a valid non-string sequence or mapping object")

        if isinstance(k, bytes):
            k_q = quote_via(k, safe)
        else:
            k_q = quote_via(str(k), safe, encoding, errors)

        if isinstance(v, bytes):
            v_q = quote_via(v, safe)
            parts.append(k_q + "=" + v_q)
        elif isinstance(v, str):
            v_q = quote_via(v, safe, encoding, errors)
            parts.append(k_q + "=" + v_q)
        elif doseq:
            try:
                seq = list(v)
            except TypeError:
                v_q = quote_via(str(v), safe, encoding, errors)
                parts.append(k_q + "=" + v_q)
            else:
                for elt in seq:
                    if isinstance(elt, bytes):
                        e_q = quote_via(elt, safe)
                    else:
                        e_q = quote_via(str(elt), safe, encoding, errors)
                    parts.append(k_q + "=" + e_q)
        else:
            v_q = quote_via(str(v), safe, encoding, errors)
            parts.append(k_q + "=" + v_q)

    return "&".join(parts)


def parse_qsl(qs="", keep_blank_values=False, strict_parsing=False,
              encoding="utf-8", errors="replace", max_num_fields=None,
              separator="&"):
    """Parse a query string into a list of (key, value) tuples."""
    if not qs:
        return []
    if isinstance(qs, (bytes, bytearray)):
        qs = bytes(qs).decode("ascii")
    if isinstance(separator, (bytes, bytearray)):
        separator = bytes(separator).decode("ascii")
    if not separator:
        raise ValueError("Separator must not be empty.")

    pairs = qs.split(separator)
    if max_num_fields is not None and len(pairs) > max_num_fields:
        raise ValueError("Max number of fields exceeded")

    result = []
    for pair in pairs:
        if not pair:
            if keep_blank_values:
                result.append(("", ""))
            elif strict_parsing:
                raise ValueError("blank parameter")
            continue
        if "=" in pair:
            k, _, v = pair.partition("=")
        else:
            if strict_parsing:
                raise ValueError("bad query field: %r" % (pair,))
            if keep_blank_values:
                k, v = pair, ""
            else:
                continue
        if v or keep_blank_values:
            k = unquote(k.replace("+", " "), encoding, errors)
            v = unquote(v.replace("+", " "), encoding, errors)
            result.append((k, v))
    return result


def parse_qs(qs="", keep_blank_values=False, strict_parsing=False,
             encoding="utf-8", errors="replace", max_num_fields=None,
             separator="&"):
    """Parse a query string into a dict of {key: [values]}."""
    parsed = parse_qsl(qs, keep_blank_values, strict_parsing, encoding,
                       errors, max_num_fields, separator)
    out = {}
    for k, v in parsed:
        out.setdefault(k, []).append(v)
    return out


# ---------------------------------------------------------------------------
# urljoin (RFC 3986 §5.2)
# ---------------------------------------------------------------------------

def _remove_dot_segments(path):
    """Apply RFC 3986 §5.2.4 dot-segment removal."""
    has_leading_slash = path.startswith("/")
    has_trailing_slash = path.endswith("/") or path.endswith("/.") \
        or path.endswith("/..")
    segments = []
    for part in path.split("/"):
        if part == "" or part == ".":
            continue
        if part == "..":
            if segments:
                segments.pop()
            continue
        segments.append(part)
    result = "/".join(segments)
    if has_leading_slash:
        result = "/" + result
    if has_trailing_slash and not result.endswith("/"):
        result = result + "/"
    return result


def urljoin(base="", url="", allow_fragments=True):
    """Resolve a possibly-relative *url* against *base*."""
    if not base:
        return url
    if not url:
        return base

    bscheme, bnetloc, bpath, bparams, bquery, bfragment = \
        urlparse(base, "", allow_fragments)
    scheme, netloc, path, params, query, fragment = \
        urlparse(url, bscheme, allow_fragments)

    if scheme != bscheme or scheme not in _USES_RELATIVE:
        return url

    if scheme in _USES_NETLOC:
        if netloc:
            return urlunparse(
                (scheme, netloc, path, params, query, fragment))
        netloc = bnetloc

    if not path and not params:
        path = bpath
        params = bparams
        if not query:
            query = bquery
        return urlunparse((scheme, netloc, path, params, query, fragment))

    if path.startswith("/"):
        return urlunparse(
            (scheme, netloc, _remove_dot_segments(path),
             params, query, fragment))

    # Merge with the base path.
    if bnetloc and not bpath:
        merged = "/" + path
    else:
        idx = bpath.rfind("/")
        if idx >= 0:
            merged = bpath[:idx + 1] + path
        else:
            merged = path

    return urlunparse(
        (scheme, netloc, _remove_dot_segments(merged),
         params, query, fragment))


def urldefrag(url=""):
    """Split *url* into (defragmented, fragment)."""
    if isinstance(url, (bytes, bytearray)):
        s = bytes(url).decode("ascii")
        defrag, frag = urldefrag(s)
        return defrag.encode("ascii"), frag.encode("ascii")
    if "#" in url:
        s, frag = url.split("#", 1)
        return s, frag
    return url, ""


# ---------------------------------------------------------------------------
# Invariant validators
# ---------------------------------------------------------------------------
# The Theseus harness calls these zero-argument hooks. Each must return the
# value declared in the spec.

def urllib_parse2_urlparse():
    r = urlparse("http://example.com/path;p?q=1#frag")
    return (
        r.scheme == "http"
        and r.netloc == "example.com"
        and r.path == "/path"
        and r.params == "p"
        and r.query == "q=1"
        and r.fragment == "frag"
    )


def urllib_parse2_urlunparse():
    return urlunparse(("http", "x.com", "/p", "", "q=1", "f")) == \
        "http://x.com/p?q=1#f"


def urllib_parse2_urlencode():
    return urlencode({"a": "1"}) == "a=1"


def urllib_parse2_urljoin():
    return urljoin("http://a/b/c/d", "e") == "http://a/b/c/e"


def urllib_parse2_quote():
    return quote("hello world")


def urllib_parse2_quote_plus():
    return quote_plus("hello world") == "hello+world"


def urllib_parse2_unquote():
    return unquote("hello%20world") == "hello world"


def urllib_parse2_unquote_plus():
    return unquote_plus("hello+world") == "hello world"


def urllib_parse2_parse_qs():
    return parse_qs("a=1&b=2") == {"a": ["1"], "b": ["2"]}


def urllib_parse2_parse_qsl():
    return parse_qsl("a=1&b=2") == [("a", "1"), ("b", "2")]


def urllib_parse2_quote_from_bytes():
    return quote_from_bytes(b"hello world") == "hello%20world"


def urllib_parse2_unquote_to_bytes():
    return unquote_to_bytes("hello%20world") == b"hello world"


def urllib_parse2_ParseResult():
    r = ParseResult("http", "x.com", "/p", "", "", "")
    return isinstance(r, tuple) and r.scheme == "http"


__all__ = [
    "ParseResult",
    "urlparse",
    "urlunparse",
    "urlencode",
    "urljoin",
    "urldefrag",
    "quote",
    "quote_plus",
    "quote_from_bytes",
    "unquote",
    "unquote_plus",
    "unquote_to_bytes",
    "parse_qs",
    "parse_qsl",
    "urllib_parse2_urlparse",
    "urllib_parse2_urlunparse",
    "urllib_parse2_urlencode",
    "urllib_parse2_urljoin",
    "urllib_parse2_quote",
    "urllib_parse2_quote_plus",
    "urllib_parse2_quote_from_bytes",
    "urllib_parse2_unquote",
    "urllib_parse2_unquote_plus",
    "urllib_parse2_unquote_to_bytes",
    "urllib_parse2_parse_qs",
    "urllib_parse2_parse_qsl",
    "urllib_parse2_ParseResult",
]
