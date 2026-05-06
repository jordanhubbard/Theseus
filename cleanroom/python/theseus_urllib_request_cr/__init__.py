"""Clean-room implementation of a minimal urllib.request-like module.

This module does NOT import urllib.request or any third-party libraries.
It provides a Request class, an add_header method, and pathname2url.
"""

import os as _os
import sys as _sys


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ALWAYS_SAFE = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
    "0123456789"
    "_.-~"
)


def _quote(string, safe="/"):
    """Percent-encode a string. Mirrors urllib.parse.quote behavior closely."""
    if string is None:
        return ""
    if isinstance(string, str):
        data = string.encode("utf-8", "strict")
    elif isinstance(string, (bytes, bytearray)):
        data = bytes(string)
    else:
        data = str(string).encode("utf-8", "strict")

    if isinstance(safe, str):
        safe_bytes = safe.encode("ascii", "ignore")
    else:
        safe_bytes = bytes(safe)
    safe_set = set(_ALWAYS_SAFE)
    for ch in safe_bytes:
        safe_set.add(chr(ch))

    out = []
    for byte in data:
        ch = chr(byte)
        if ch in safe_set:
            out.append(ch)
        else:
            out.append("%%%02X" % byte)
    return "".join(out)


def _splittype(url):
    """Split url into (scheme, rest)."""
    if not isinstance(url, str):
        return None, url
    i = url.find(":")
    if i > 0:
        scheme = url[:i]
        # Scheme must start with a letter and contain only letters/digits/+-./
        if scheme[0].isalpha():
            ok = True
            for c in scheme[1:]:
                if not (c.isalnum() or c in "+-."):
                    ok = False
                    break
            if ok:
                return scheme.lower(), url[i + 1:]
    return None, url


def _splithost(url):
    """If url begins with //, split off the authority."""
    if url[:2] == "//":
        rest = url[2:]
        # Find end of authority: first '/', '?' or '#'
        end = len(rest)
        for i, c in enumerate(rest):
            if c in "/?#":
                end = i
                break
        return rest[:end], rest[end:]
    return None, url


def _unwrap(url):
    """Remove < >, whitespace, and surrounding 'URL:'."""
    url = str(url).strip()
    if url[:1] == "<" and url[-1:] == ">":
        url = url[1:-1].strip()
    if url[:4].lower() == "url:":
        url = url[4:].strip()
    return url


# ---------------------------------------------------------------------------
# pathname2url
# ---------------------------------------------------------------------------

def pathname2url(pathname):
    """Convert a local pathname into a URL path component.

    On POSIX systems, this percent-encodes characters except for '/' and the
    unreserved set. On Windows-style paths (containing a drive letter or
    backslashes), it normalizes separators to '/' and prefixes '///' for
    absolute drive paths.
    """
    if pathname is None:
        return ""
    if not isinstance(pathname, str):
        pathname = str(pathname)

    # Detect Windows-style drive letter, e.g. "C:\foo" or "C:/foo"
    if (len(pathname) >= 2 and pathname[1] == ":" and
            ("A" <= pathname[0].upper() <= "Z")):
        drive = pathname[0]
        rest = pathname[2:].replace("\\", "/")
        # Absolute drive path -> ///C:/path
        if rest.startswith("/"):
            return "///" + drive + ":" + _quote(rest, safe="/")
        return drive + ":" + _quote(rest, safe="/")

    # UNC path \\server\share\file -> //server/share/file
    if pathname.startswith("\\\\"):
        normalized = pathname.replace("\\", "/")
        return _quote(normalized, safe="/")

    # Backslash path with no drive
    if "\\" in pathname:
        pathname = pathname.replace("\\", "/")

    return _quote(pathname, safe="/")


# ---------------------------------------------------------------------------
# Request class
# ---------------------------------------------------------------------------

class Request:
    """A clean-room minimal Request representation."""

    def __init__(self, url, data=None, headers=None, origin_req_host=None,
                 unverifiable=False, method=None):
        self.full_url = url
        self.data = data
        self.headers = {}
        self.unredirected_hdrs = {}
        self.origin_req_host = origin_req_host
        self.unverifiable = unverifiable
        self.method = method
        self._parse()
        if headers:
            try:
                items = headers.items()
            except AttributeError:
                items = list(headers)
            for key, value in items:
                self.add_header(key, value)

    # ---- URL handling --------------------------------------------------
    @property
    def full_url(self):
        if self.fragment:
            return "%s#%s" % (self._full_url, self.fragment)
        return self._full_url

    @full_url.setter
    def full_url(self, url):
        # Strip fragment
        url = _unwrap(url) if url is not None else ""
        if "#" in url:
            url, frag = url.split("#", 1)
            self.fragment = frag
        else:
            self.fragment = None
        self._full_url = url

    @full_url.deleter
    def full_url(self):
        self._full_url = None
        self.fragment = None
        self.selector = ""

    def _parse(self):
        self.type, rest = _splittype(self._full_url)
        if self.type is None:
            raise ValueError("unknown url type: %r" % self._full_url)
        self.host, self.selector = _splithost(rest)
        if self.host is None:
            self.host = ""
            self.selector = rest

    # ---- Method --------------------------------------------------------
    def get_method(self):
        if self.method is not None:
            return self.method
        if self.data is not None:
            return "POST"
        return "GET"

    # ---- Headers -------------------------------------------------------
    def add_header(self, key, val):
        """Add a header. The key is case-normalized to capitalize()."""
        self.headers[key.capitalize()] = val

    def add_unredirected_header(self, key, val):
        self.unredirected_hdrs[key.capitalize()] = val

    def has_header(self, header_name):
        name = header_name.capitalize()
        return name in self.headers or name in self.unredirected_hdrs

    def get_header(self, header_name, default=None):
        name = header_name.capitalize()
        if name in self.headers:
            return self.headers[name]
        if name in self.unredirected_hdrs:
            return self.unredirected_hdrs[name]
        return default

    def remove_header(self, header_name):
        name = header_name.capitalize()
        self.headers.pop(name, None)
        self.unredirected_hdrs.pop(name, None)

    def header_items(self):
        merged = {}
        merged.update(self.headers)
        merged.update(self.unredirected_hdrs)
        return list(merged.items())

    # ---- Misc accessors ------------------------------------------------
    def get_full_url(self):
        return self.full_url

    def get_type(self):
        return self.type

    def get_host(self):
        return self.host

    def get_selector(self):
        return self.selector

    def get_data(self):
        return self.data

    def has_data(self):
        return self.data is not None

    def is_unverifiable(self):
        return self.unverifiable

    def get_origin_req_host(self):
        if self.origin_req_host is not None:
            return self.origin_req_host
        return self.host


# ---------------------------------------------------------------------------
# Invariant probes
# ---------------------------------------------------------------------------

def urllib_request2_request():
    """Return True if Request construction and basic accessors work."""
    try:
        req = Request("http://example.com/path?x=1#frag",
                      data=b"payload",
                      headers={"User-Agent": "theseus/1.0"})
        if req.get_type() != "http":
            return False
        if req.get_host() != "example.com":
            return False
        if req.get_selector() != "/path?x=1":
            return False
        if req.fragment != "frag":
            return False
        if req.get_method() != "POST":
            return False
        if req.get_data() != b"payload":
            return False
        if not req.has_data():
            return False
        # default GET when no data
        req2 = Request("https://example.org/")
        if req2.get_method() != "GET":
            return False
        if req2.get_type() != "https":
            return False
        # Explicit method override
        req3 = Request("http://x/", method="DELETE")
        if req3.get_method() != "DELETE":
            return False
        # full_url round-trip with fragment
        if req.get_full_url() != "http://example.com/path?x=1#frag":
            return False
        return True
    except Exception:
        return False


def urllib_request2_add_header():
    """Return True if add_header / get_header / has_header work correctly."""
    try:
        req = Request("http://example.com/")
        req.add_header("Content-Type", "application/json")
        req.add_header("X-CUSTOM", "yes")
        # Keys are stored capitalized
        if not req.has_header("content-type"):
            return False
        if not req.has_header("Content-Type"):
            return False
        if req.get_header("CONTENT-TYPE") != "application/json":
            return False
        if req.get_header("X-Custom") != "yes":
            return False
        if req.get_header("Missing", "default-val") != "default-val":
            return False
        # Overwrite
        req.add_header("Content-Type", "text/plain")
        if req.get_header("Content-Type") != "text/plain":
            return False
        # Unredirected header
        req.add_unredirected_header("Host", "example.com")
        if not req.has_header("host"):
            return False
        # header_items contains both
        items = dict(req.header_items())
        if "Content-type" not in items or "Host" not in items:
            return False
        # Remove
        req.remove_header("Content-Type")
        if req.has_header("content-type"):
            return False
        return True
    except Exception:
        return False


def urllib_request2_pathname2url():
    """Return True if pathname2url percent-encodes correctly."""
    try:
        if pathname2url("/foo/bar") != "/foo/bar":
            return False
        if pathname2url("/foo bar/baz") != "/foo%20bar/baz":
            return False
        if pathname2url("/a/b%c") != "/a/b%25c":
            return False
        if pathname2url("relative/path") != "relative/path":
            return False
        # Reserved chars preserved? '/' kept, '?' encoded
        if pathname2url("/a?b") != "/a%3Fb":
            return False
        # Empty
        if pathname2url("") != "":
            return False
        # Backslashes converted to forward slashes
        if pathname2url("a\\b\\c") != "a/b/c":
            return False
        # Drive letter
        if pathname2url("C:\\Users\\me") != "///C:/Users/me":
            return False
        if pathname2url("C:/Users/me") != "///C:/Users/me":
            return False
        return True
    except Exception:
        return False


__all__ = [
    "Request",
    "pathname2url",
    "urllib_request2_request",
    "urllib_request2_add_header",
    "urllib_request2_pathname2url",
]