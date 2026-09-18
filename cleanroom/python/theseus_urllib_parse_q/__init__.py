"""
theseus_urllib_parse_q — Clean-room URL parse/join/quote (RFC 3986 subset).
Do NOT import urllib.parse.
"""

_UNRESERVED = frozenset(
    b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
)


class ParseResult(object):
    __slots__ = ("scheme", "netloc", "path", "params", "query", "fragment")

    def __init__(self, scheme, netloc, path, params, query, fragment):
        self.scheme = scheme
        self.netloc = netloc
        self.path = path
        self.params = params
        self.query = query
        self.fragment = fragment

    def __getitem__(self, idx):
        return (self.scheme, self.netloc, self.path, self.params, self.query, self.fragment)[idx]

    @property
    def username(self):
        if "@" not in self.netloc:
            return None
        userinfo = self.netloc.rsplit("@", 1)[0]
        return userinfo.split(":")[0] or None

    @property
    def password(self):
        if "@" not in self.netloc:
            return None
        userinfo = self.netloc.rsplit("@", 1)[0]
        if ":" not in userinfo:
            return None
        return userinfo.split(":", 1)[1]

    @property
    def hostname(self):
        host = self.netloc
        if "@" in host:
            host = host.rsplit("@", 1)[1]
        if host.startswith("["):
            end = host.find("]")
            if end != -1:
                return host[1:end].lower()
        if ":" in host:
            host = host.rsplit(":", 1)[0]
        return host.lower() if host else None

    @property
    def port(self):
        host = self.netloc
        if "@" in host:
            host = host.rsplit("@", 1)[1]
        if host.startswith("["):
            end = host.find("]")
            rest = host[end + 1:]
            if rest.startswith(":"):
                return int(rest[1:])
            return None
        if ":" in host:
            return int(host.rsplit(":", 1)[1])
        return None


def urlparse(url, scheme="", allow_fragments=True):
    fragment = ""
    query = ""
    params = ""
    if allow_fragments and "#" in url:
        url, fragment = url.split("#", 1)
    if "?" in url:
        url, query = url.split("?", 1)
    netloc = ""
    if "://" in url:
        scheme, rest = url.split("://", 1)
        if "/" in rest:
            netloc, path = rest.split("/", 1)
            path = "/" + path
        elif "?" in rest or not rest:
            netloc, path = rest, ""
        else:
            netloc, path = rest, ""
    elif url.startswith("//"):
        rest = url[2:]
        if "/" in rest:
            netloc, path = rest.split("/", 1)
            path = "/" + path
        else:
            netloc, path = rest, ""
    else:
        path = url
    if ";" in path:
        path, params = path.split(";", 1)
    return ParseResult(scheme, netloc, path, params, query, fragment)


def urlunparse(parts):
    scheme, netloc, path, params, query, fragment = parts
    result = ""
    if scheme:
        result += scheme + ":"
    if netloc or scheme in ("http", "https", "ftp"):
        result += "//" + (netloc or "")
    if params:
        path = path + ";" + params
    result += path
    if query:
        result += "?" + query
    if fragment:
        result += "#" + fragment
    return result


def _collapse(path):
    parts = []
    for seg in path.split("/"):
        if seg == ".":
            continue
        if seg == "..":
            if parts and parts[-1] not in ("", ".."):
                parts.pop()
            continue
        parts.append(seg)
    collapsed = "/".join(parts)
    if path.startswith("/") and not collapsed.startswith("/"):
        collapsed = "/" + collapsed
    if path.endswith("/") and not collapsed.endswith("/"):
        collapsed += "/"
    return collapsed or ("/" if path.startswith("/") else "")


def urljoin(base, url, allow_fragments=True):
    b = urlparse(base, allow_fragments=allow_fragments)
    r = urlparse(url, allow_fragments=allow_fragments)
    if r.scheme:
        path = _collapse(r.path) if r.path else r.path
        return urlunparse((r.scheme, r.netloc, path, r.params, r.query, r.fragment))
    scheme = b.scheme
    if r.netloc:
        return urlunparse((scheme, r.netloc, _collapse(r.path), r.params, r.query, r.fragment))
    netloc = b.netloc
    if r.path.startswith("/"):
        path = _collapse(r.path)
        query = r.query
        params = r.params
    elif r.path or r.params:
        base_path = b.path
        if not base_path.endswith("/"):
            if "/" in base_path:
                base_path = base_path.rsplit("/", 1)[0] + "/"
            else:
                base_path = ""
        path = _collapse(base_path + r.path)
        query = r.query
        params = r.params
    else:
        path = b.path
        params = b.params
        query = r.query if r.query or (url and "?" in url) else b.query
        if r.query:
            query = r.query
        elif "?" in (url or ""):
            query = ""
        else:
            query = b.query
        if not r.path and not r.params and not r.query and not (url and "?" in url):
            query = b.query
    fragment = r.fragment
    return urlunparse((scheme, netloc, path, params, query, fragment))


def quote(string, safe="/", encoding="utf-8", errors="strict"):
    if isinstance(string, bytes):
        data = string
    else:
        data = string.encode(encoding, errors)
    safe_bytes = _UNRESERVED | frozenset(safe.encode("ascii") if isinstance(safe, str) else safe)
    out = []
    for byte in data:
        if byte in safe_bytes:
            out.append(chr(byte))
        else:
            out.append("%{:02X}".format(byte))
    return "".join(out)


def quote_plus(string, safe="", encoding="utf-8", errors="strict"):
    if isinstance(string, str):
        string = string.replace(" ", "+")
        return quote(string, safe=safe + "+", encoding=encoding, errors=errors)
    data = bytes(string).replace(b" ", b"+")
    return quote(data, safe=safe + "+", encoding=encoding, errors=errors)


def unquote(string, encoding="utf-8", errors="replace"):
    if isinstance(string, bytes):
        string = string.decode("ascii")
    out = bytearray()
    i = 0
    n = len(string)
    while i < n:
        ch = string[i]
        if ch == "%" and i + 2 < n:
            try:
                out.append(int(string[i + 1:i + 3], 16))
                i += 3
                continue
            except ValueError:
                pass
        out.extend(ch.encode("utf-8"))
        i += 1
    return out.decode(encoding, errors)


def unquote_plus(string, encoding="utf-8", errors="replace"):
    if isinstance(string, str):
        string = string.replace("+", " ")
    return unquote(string, encoding=encoding, errors=errors)


def urlencode(query, doseq=False, safe="", encoding=None, errors=None, quote_via=None):
    qv = quote_via or quote_plus
    if hasattr(query, "items"):
        items = list(query.items())
    else:
        items = list(query)
    parts = []
    for key, val in items:
        parts.append(qv(str(key)) + "=" + qv(str(val)))
    return "&".join(parts)


def parse_qs(qs, keep_blank_values=False, strict_parsing=False, encoding="utf-8", errors="replace", max_num_fields=None, separator="&"):
    result = {}
    if not qs:
        return result
    for part in qs.split(separator):
        if not part and not keep_blank_values:
            continue
        if "=" in part:
            key, val = part.split("=", 1)
        else:
            key, val = part, ""
        key = unquote_plus(key, encoding=encoding, errors=errors)
        val = unquote_plus(val, encoding=encoding, errors=errors)
        result.setdefault(key, []).append(val)
    return result


__all__ = [
    "urlparse",
    "urljoin",
    "quote",
    "unquote",
    "quote_plus",
    "unquote_plus",
    "urlencode",
    "parse_qs",
    "urlunparse",
    "ParseResult",
]
