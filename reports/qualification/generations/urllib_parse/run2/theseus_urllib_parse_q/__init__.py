# generation B split class

_HEX = "0123456789ABCDEFabcdef"
_ALWAYS_SAFE = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-~"


class SplitResult:
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

    def __len__(self):
        return 6

    def __getitem__(self, index):
        return tuple(self)[index]

    def __eq__(self, other):
        try:
            return tuple(self) == tuple(other)
        except (TypeError, ValueError):
            return False

    def __repr__(self):
        values = tuple(self)
        return (
            "SplitResult(scheme={!r}, netloc={!r}, path={!r}, params={!r}, "
            "query={!r}, fragment={!r})"
        ).format(*values)

    @property
    def _userinfo_hostport(self):
        if "@" in self.netloc:
            return self.netloc.rsplit("@", 1)
        return "", self.netloc

    @property
    def username(self):
        userinfo, unused = self._userinfo_hostport
        if not userinfo:
            return None
        return userinfo.split(":", 1)[0]

    @property
    def password(self):
        userinfo, unused = self._userinfo_hostport
        if ":" not in userinfo:
            return None
        return userinfo.split(":", 1)[1]

    @property
    def hostname(self):
        unused, hostport = self._userinfo_hostport
        if hostport.startswith("["):
            end = hostport.find("]")
            if end < 0:
                raise ValueError("Invalid IPv6 URL")
            return hostport[1:end].lower()
        return hostport.split(":", 1)[0].lower() or None

    @property
    def port(self):
        unused, hostport = self._userinfo_hostport
        text = None
        if hostport.startswith("["):
            end = hostport.find("]")
            if end < 0:
                raise ValueError("Invalid IPv6 URL")
            remainder = hostport[end + 1:]
            if remainder.startswith(":"):
                text = remainder[1:]
        elif ":" in hostport:
            text = hostport.rsplit(":", 1)[1]
        if text is None:
            return None
        if not text.isdigit():
            raise ValueError("Port could not be cast to integer value")
        value = int(text)
        if value > 65535:
            raise ValueError("Port out of range 0-65535")
        return value


def _valid_scheme(text):
    if not text or not text[0].isalpha():
        return False
    for char in text[1:]:
        if not (char.isalnum() or char in "+-."):
            return False
    return True


def urlparse(url, scheme="", allow_fragments=True):
    if not isinstance(url, str):
        raise TypeError("url must be a string")
    rest = url
    fragment = ""
    if allow_fragments and "#" in rest:
        rest, fragment = rest.split("#", 1)

    query = ""
    if "?" in rest:
        rest, query = rest.split("?", 1)

    parsed_scheme = scheme
    colon = rest.find(":")
    slash = rest.find("/")
    if colon >= 0 and (slash < 0 or colon < slash) and _valid_scheme(rest[:colon]):
        parsed_scheme = rest[:colon].lower()
        rest = rest[colon + 1:]

    netloc = ""
    if rest.startswith("//"):
        authority_path = rest[2:]
        end = len(authority_path)
        for marker in "/":
            position = authority_path.find(marker)
            if position >= 0:
                end = min(end, position)
        netloc = authority_path[:end]
        rest = authority_path[end:]
        if netloc.count("[") != netloc.count("]"):
            raise ValueError("Invalid IPv6 URL")

    params = ""
    last_slash = rest.rfind("/")
    semicolon = rest.find(";", last_slash + 1)
    if semicolon >= 0:
        rest, params = rest[:semicolon], rest[semicolon + 1:]

    return SplitResult(parsed_scheme, netloc, rest, params, query, fragment)


def urlunparse(parts):
    scheme, netloc, path, params, query, fragment = parts
    result = ""
    if scheme:
        result = str(scheme) + ":"
    if netloc:
        result += "//" + str(netloc)
        if path and not str(path).startswith("/"):
            result += "/"
    result += str(path)
    if params:
        result += ";" + str(params)
    if query:
        result += "?" + str(query)
    if fragment:
        result += "#" + str(fragment)
    return result


def _remove_dot_segments(path):
    absolute = path.startswith("/")
    trailing = path.endswith("/") or path.endswith("/.") or path.endswith("/..")
    output = []
    for segment in path.split("/"):
        if segment == "" or segment == ".":
            continue
        if segment == "..":
            if output:
                output.pop()
        else:
            output.append(segment)
    result = "/".join(output)
    if absolute:
        result = "/" + result
    if trailing and result and not result.endswith("/"):
        result += "/"
    if absolute and not result:
        return "/"
    return result


def urljoin(base, url, allow_fragments=True):
    if not base:
        return url
    if not url:
        return base

    b = urlparse(base, allow_fragments=allow_fragments)
    r = urlparse(url, scheme=b.scheme, allow_fragments=allow_fragments)

    reference_has_scheme = False
    colon = url.find(":")
    slash = url.find("/")
    if colon >= 0 and (slash < 0 or colon < slash):
        reference_has_scheme = _valid_scheme(url[:colon])
    if reference_has_scheme and r.scheme != b.scheme:
        return urlunparse(r)

    if reference_has_scheme:
        return urlunparse(
            (r.scheme, r.netloc, _remove_dot_segments(r.path),
             r.params, r.query, r.fragment)
        )

    if url.startswith("//"):
        return urlunparse(
            (b.scheme, r.netloc, _remove_dot_segments(r.path),
             r.params, r.query, r.fragment)
        )

    if not r.path:
        path = b.path
        params = r.params if r.params else b.params
        query = r.query if "?" in url else b.query
    else:
        params = r.params
        if r.path.startswith("/"):
            path = _remove_dot_segments(r.path)
        else:
            if b.netloc and not b.path:
                merged = "/" + r.path
            else:
                merged = b.path.rsplit("/", 1)[0] + "/" + r.path
            path = _remove_dot_segments(merged)
        query = r.query
    return urlunparse((b.scheme, b.netloc, path, params, query, r.fragment))


def quote(string, safe="/", encoding=None, errors=None):
    if isinstance(string, bytes):
        if encoding is not None or errors is not None:
            raise TypeError("encoding and errors must not be specified for bytes")
        data = string
    elif isinstance(string, str):
        data = string.encode(encoding or "utf-8", errors or "strict")
    else:
        raise TypeError("quote() expected string or bytes")

    if isinstance(safe, bytes):
        safe_bytes = set(safe)
    else:
        safe_bytes = set(str(safe).encode("ascii", "ignore"))
    safe_bytes.update(ord(char) for char in _ALWAYS_SAFE)

    result = []
    for value in data:
        if value in safe_bytes:
            result.append(chr(value))
        else:
            result.append("%" + format(value, "02X"))
    return "".join(result)


def quote_plus(string, safe="", encoding=None, errors=None):
    if isinstance(string, str):
        return quote(string, safe + " ", encoding, errors).replace(" ", "+")
    return quote(string, safe + " ", encoding, errors).replace(" ", "+")


def unquote(string, encoding="utf-8", errors="replace"):
    if isinstance(string, bytes):
        source = string.decode("ascii")
    elif isinstance(string, str):
        source = string
    else:
        raise TypeError("unquote() expected string or bytes")

    output = bytearray()
    index = 0
    while index < len(source):
        if (source[index] == "%" and index + 2 < len(source)
                and source[index + 1] in _HEX
                and source[index + 2] in _HEX):
            output.append(int(source[index + 1:index + 3], 16))
            index += 3
        else:
            output.extend(source[index].encode("utf-8"))
            index += 1
    return bytes(output).decode(encoding, errors)


def urlencode(query, doseq=False, safe="", encoding=None, errors=None):
    items = query.items() if hasattr(query, "items") else query
    fields = []
    for key, value in items:
        values = value if doseq and isinstance(value, (list, tuple)) else [value]
        for member in values:
            key_text = key if isinstance(key, (str, bytes)) else str(key)
            value_text = member if isinstance(member, (str, bytes)) else str(member)
            fields.append(
                quote_plus(key_text, safe, encoding, errors)
                + "="
                + quote_plus(value_text, safe, encoding, errors)
            )
    return "&".join(fields)


def parse_qs(qs, keep_blank_values=False, strict_parsing=False,
             encoding="utf-8", errors="replace", max_num_fields=None,
             separator="&"):
    if not isinstance(qs, (str, bytes)):
        raise TypeError("query string must be str or bytes")
    if not separator:
        raise ValueError("Separator must be of type string or bytes")
    if isinstance(qs, bytes):
        qs = qs.decode("ascii")
    if isinstance(separator, bytes):
        separator = separator.decode("ascii")
    fields = qs.split(separator) if qs else []
    if max_num_fields is not None and len(fields) > max_num_fields:
        raise ValueError("Max number of fields exceeded")
    result = {}
    for field in fields:
        if not field and not strict_parsing:
            continue
        if "=" in field:
            name, value = field.split("=", 1)
        else:
            if strict_parsing:
                raise ValueError("bad query field: {!r}".format(field))
            name, value = field, ""
        if value or keep_blank_values:
            name = unquote(name.replace("+", " "), encoding, errors)
            value = unquote(value.replace("+", " "), encoding, errors)
            result.setdefault(name, []).append(value)
    return result


__all__ = [
    "urlparse", "urljoin", "quote", "quote_plus", "unquote",
    "urlencode", "parse_qs", "urlunparse",
]
