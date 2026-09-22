# generation A namedtuple parse

from collections import namedtuple

__all__ = [
    "urlparse",
    "urlunparse",
    "urljoin",
    "quote",
    "quote_plus",
    "unquote",
    "urlencode",
    "parse_qs",
    "ParseResult",
]

_UNRESERVED = frozenset(
    b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
)
_HEX = "0123456789ABCDEF"


class ParseResult(
    namedtuple(
        "ParseResult",
        ["scheme", "netloc", "path", "params", "query", "fragment"],
    )
):
    __slots__ = ()

    @property
    def username(self):
        userinfo, _hostport = _split_userinfo(self.netloc)
        if userinfo is None:
            return None
        user, _password = _split_user_pass(userinfo)
        return user or None

    @property
    def password(self):
        userinfo, _hostport = _split_userinfo(self.netloc)
        if userinfo is None:
            return None
        _user, password = _split_user_pass(userinfo)
        return password

    @property
    def hostname(self):
        _userinfo, hostport = _split_userinfo(self.netloc)
        if not hostport:
            return None
        host, _port = _split_host_port(hostport)
        return host or None

    @property
    def port(self):
        _userinfo, hostport = _split_userinfo(self.netloc)
        if not hostport:
            return None
        _host, port = _split_host_port(hostport)
        return port


def _split_userinfo(netloc):
    if not netloc:
        return None, ""
    if "@" not in netloc:
        return None, netloc
    userinfo, hostport = netloc.rsplit("@", 1)
    return userinfo, hostport


def _split_user_pass(userinfo):
    if ":" in userinfo:
        user, password = userinfo.split(":", 1)
        return user, password
    return userinfo, None


def _split_host_port(hostport):
    if not hostport:
        return "", None
    if hostport.startswith("["):
        end = hostport.find("]")
        if end != -1:
            host = hostport[1:end]
            rest = hostport[end + 1 :]
            if rest.startswith(":"):
                port_str = rest[1:]
                return host, _parse_port(port_str)
            return host, None
    if ":" in hostport:
        host, port_str = hostport.rsplit(":", 1)
        if port_str.isdigit() and host:
            return host, _parse_port(port_str)
    return hostport, None


def _parse_port(port_str):
    if not port_str:
        return None
    try:
        port = int(port_str)
    except ValueError:
        return None
    if 0 <= port <= 65535:
        return port
    return None


def urlparse(url, scheme="", allow_fragments=True):
    url = str(url)
    fragment = ""
    if allow_fragments and "#" in url:
        url, fragment = url.split("#", 1)

    query = ""
    if "?" in url:
        url, query = url.split("?", 1)

    params = ""
    scheme_colon = url.find(":")
    if scheme_colon != -1:
        maybe_scheme = url[:scheme_colon]
        if _is_scheme(maybe_scheme):
            scheme = maybe_scheme
            url = url[scheme_colon + 1 :]
            if url.startswith("//"):
                url = url[2:]
                delim = len(url)
                for c in "/?;#":
                    idx = url.find(c)
                    if idx != -1 and idx < delim:
                        delim = idx
                netloc = url[:delim]
                url = url[delim:]
            else:
                netloc = ""
        else:
            netloc = ""
    else:
        netloc = ""

    if ";" in url:
        url, params = url.split(";", 1)
        if "?" in params:
            params, extra_query = params.split("?", 1)
            if not query:
                query = extra_query

    path = url

    return ParseResult(scheme, netloc, path, params, query, fragment)


def _is_scheme(s):
    if not s:
        return False
    first = s[0]
    if not (first.isalpha() or first in "+-"):
        return False
    for ch in s:
        if not (ch.isalnum() or ch in "+-."):
            return False
    return True


def urlunparse(components):
    scheme, netloc, path, params, query, fragment = components
    if params:
        path = path + ";" + params
    return _urlunsplit((scheme, netloc, path, query, fragment))


def _urlunsplit(components):
    scheme, netloc, path, query, fragment = components
    if path or scheme or netloc or query or fragment:
        url = ""
        if scheme:
            url = scheme + ":"
        if netloc:
            if url or path.startswith("//"):
                url += "//"
            url += netloc
        elif url:
            url += "//"
        url += path
        if query:
            url += "?" + query
        if fragment:
            url += "#" + fragment
    else:
        url = path
    return url


def urljoin(base, url, allow_fragments=True):
    if not base:
        return url
    base_parts = urlparse(base, allow_fragments=allow_fragments)
    url_parts = urlparse(url, allow_fragments=allow_fragments)

    if url_parts.scheme:
        return _normalize_joined(url_parts)

    scheme = base_parts.scheme
    netloc = base_parts.netloc
    query = url_parts.query
    fragment = url_parts.fragment if allow_fragments else ""

    if url_parts.netloc:
        netloc = url_parts.netloc
        path = url_parts.path
        params = url_parts.params
    else:
        params = url_parts.params
        if not url_parts.path:
            path = base_parts.path
            if not query:
                query = base_parts.query
        elif url_parts.path[:1] == "/":
            path = url_parts.path
        else:
            path = _merge_paths(base_parts.path, url_parts.path)

    joined = ParseResult(scheme, netloc, path, params, query, fragment)
    return _normalize_joined(joined)


def _normalize_joined(parts):
    return urlunparse(parts)


def _merge_paths(base_path, rel_path):
    if not base_path:
        base_path = "/"
    if not base_path.endswith("/"):
        if "/" in base_path:
            base_path = base_path.rsplit("/", 1)[0] + "/"
        else:
            base_path = base_path + "/"
    return _remove_dot_segments(base_path + rel_path)


def _remove_dot_segments(path):
    stack = []
    if path.startswith("/"):
        stack.append("")
    for part in path.split("/"):
        if part == "..":
            if len(stack) > 1:
                stack.pop()
            elif len(stack) == 1 and stack[0] != "":
                stack.pop()
        elif part == "." or part == "":
            continue
        else:
            stack.append(part)
    if stack and stack[0] == "":
        if len(stack) == 1:
            return "/"
        return "/" + "/".join(stack[1:])
    return "/".join(stack)


def quote(string, safe="/", encoding=None, errors=None):
    if isinstance(string, str):
        if encoding is None:
            encoding = "utf-8"
        if errors is None:
            errors = "strict"
        string = string.encode(encoding, errors)
    if not isinstance(string, (bytes, bytearray)):
        raise TypeError("quote() expects str or bytes")
    if not safe:
        safe_bytes = b""
    elif isinstance(safe, str):
        safe_bytes = safe.encode("ascii", "ignore")
    else:
        safe_bytes = bytes(safe)
    return _quote_from_bytes(bytes(string), safe_bytes)


def _quote_from_bytes(bs, safe):
    if not bs:
        return ""
    parts = []
    for byte in bs:
        if byte in _UNRESERVED or byte in safe:
            parts.append(chr(byte))
        else:
            parts.append("%" + _HEX[byte >> 4] + _HEX[byte & 0xF])
    return "".join(parts)


def quote_plus(string, safe="", encoding=None, errors=None):
    if isinstance(safe, str):
        safe = safe + " "
    else:
        safe = safe + b" "
    return quote(string, safe, encoding, errors).replace(" ", "+")


def unquote(string, encoding="utf-8", errors="replace"):
    if isinstance(string, bytes):
        string = string.decode(encoding, errors)
    bits = string.split("%")
    if len(bits) == 1:
        return string
    out = [bits[0]]
    for item in bits[1:]:
        if len(item) >= 2 and _is_hex(item[0]) and _is_hex(item[1]):
            out.append(chr(int(item[:2], 16)))
            out.append(item[2:])
        else:
            out.append("%")
            out.append(item)
    return "".join(out)


def _is_hex(ch):
    return ch in "0123456789abcdefABCDEF"


def urlencode(query, doseq=False):
    if hasattr(query, "items"):
        items = list(query.items())
    else:
        items = list(query)
    parts = []
    for key, value in items:
        key_str = quote_plus(str(key))
        if doseq and _is_sequence(value):
            for elt in value:
                parts.append(key_str + "=" + quote_plus(str(elt)))
        else:
            parts.append(key_str + "=" + quote_plus(str(value)))
    return "&".join(parts)


def _is_sequence(val):
    if isinstance(val, (str, bytes, bytearray)):
        return False
    return hasattr(val, "__iter__")


def parse_qs(qs, keep_blank_values=False, strict_parsing=False):
    if isinstance(qs, bytes):
        qs = qs.decode("ascii", "ignore")
    result = {}
    if not qs:
        return result
    pairs = qs.split("&")
    for pair in pairs:
        if not pair and not strict_parsing:
            continue
        if "=" in pair:
            key, value = pair.split("=", 1)
        else:
            if strict_parsing:
                raise ValueError("bad query field")
            key, value = pair, ""
        key = unquote_plus(key)
        value = unquote_plus(value)
        if value or keep_blank_values:
            result.setdefault(key, []).append(value)
    return result


def unquote_plus(string, encoding="utf-8", errors="replace"):
    if isinstance(string, bytes):
        string = string.decode(encoding, errors)
    string = string.replace("+", " ")
    return unquote(string, encoding, errors)
