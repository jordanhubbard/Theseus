"""
theseus_nturl2path_cr — Clean-room implementation of nturl2path.

Converts Windows (NT) pathnames to/from file URLs.

This module is implemented from scratch and does NOT import the standard
library ``nturl2path`` module. It uses only Python standard library
primitives for percent-encoding/decoding, and re-implements the core
mapping logic directly.
"""

# We deliberately do NOT import nturl2path. We may use urllib.parse for
# percent-encoding helpers, but to keep the implementation maximally
# self-contained we provide our own quote/unquote routines below.


_ASCII_LETTERS = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
)

# RFC 3986 "unreserved" characters; these are never percent-encoded.
_ALWAYS_SAFE = frozenset(
    _ASCII_LETTERS
    + "0123456789"
    + "_.-~"
)


def _quote(s, safe="/"):
    """Percent-encode *s* (a ``str``), preserving characters in *safe*."""
    if not isinstance(s, str):
        raise TypeError("quote expects a str")
    safe_set = _ALWAYS_SAFE | set(safe)
    out = []
    for ch in s:
        if ch in safe_set:
            out.append(ch)
            continue
        for byte in ch.encode("utf-8"):
            out.append("%%%02X" % byte)
    return "".join(out)


def _unquote(s):
    """Decode percent-escapes in *s* (a ``str``) into a ``str``."""
    if not isinstance(s, str):
        raise TypeError("unquote expects a str")
    if "%" not in s:
        return s
    result = []
    i = 0
    n = len(s)
    while i < n:
        ch = s[i]
        if ch != "%":
            result.append(ch)
            i += 1
            continue
        byte_run = bytearray()
        while i < n and s[i] == "%" and i + 2 < n:
            hex2 = s[i + 1 : i + 3]
            try:
                byte_run.append(int(hex2, 16))
            except ValueError:
                break
            i += 3
        if byte_run:
            result.append(byte_run.decode("utf-8", errors="replace"))
        else:
            result.append("%")
            i += 1
    return "".join(result)


def url2pathname(url):
    """Convert a 'file' scheme URL path to an NT (Windows) pathname."""
    url = url.replace(":", "|")

    if "|" not in url:
        if url[:4] == "////":
            url = url[2:]
        components = url.split("/")
        return _unquote("\\".join(components))

    comp = url.split("|")
    if len(comp) != 2 or not comp[0] or comp[0][-1] not in _ASCII_LETTERS:
        raise OSError("Bad URL: " + url)

    drive = comp[0][-1].upper()
    components = comp[1].split("/")
    path = drive + ":"
    for piece in components:
        if piece:
            path = path + "\\" + _unquote(piece)

    if path.endswith(":") and url.endswith("/"):
        path += "\\"
    return path


def pathname2url(p):
    """Convert an NT (Windows) pathname to a relative 'file' scheme URL."""
    if p[:4] == "\\\\?\\":
        p = p[4:]
        if p[:4].upper() == "UNC\\":
            p = "\\" + p[4:]
        elif p[1:2] != ":":
            raise OSError("Bad path: " + p)

    if ":" not in p:
        if p[:2] == "\\\\":
            p = "\\\\" + p
        components = p.split("\\")
        return _quote("/".join(components))

    comp = p.split(":", 2)
    if len(comp) != 2 or len(comp[0]) > 1:
        raise OSError("Bad path: " + p)

    drive = _quote(comp[0].upper())
    components = comp[1].split("\\")
    path = "///" + drive + ":"
    for piece in components:
        if piece:
            path = path + "/" + _quote(piece)
    return path


def nturl2_url2pathname():
    """Verify url2pathname() converts file URLs to NT pathnames correctly."""
    cases = [
        ("///C:/foo/bar/spam.foo", "C:\\foo\\bar\\spam.foo"),
        ("///C|/foo/bar/spam.foo", "C:\\foo\\bar\\spam.foo"),
        ("///C:/", "C:\\"),
        ("///C|/", "C:\\"),
        ("///C:", "C:"),
        ("///C|", "C:"),
        ("////host/share/dir", "\\\\host\\share\\dir"),
        ("/foo/bar", "\\foo\\bar"),
        ("///C:/a%20b/c", "C:\\a b\\c"),
    ]
    for url, expected in cases:
        try:
            got = url2pathname(url)
        except Exception:
            return False
        if got != expected:
            return False

    bad = ["foo|bar|baz"]
    for url in bad:
        try:
            url2pathname(url)
        except OSError:
            continue
        except Exception:
            return False
        return False
    return True


def nturl2_pathname2url():
    """Verify pathname2url() converts NT pathnames to file URLs correctly."""
    cases = [
        ("C:\\foo\\bar\\spam.foo", "///C:/foo/bar/spam.foo"),
        ("C:\\", "///C:"),
        ("C:", "///C:"),
        ("\\\\host\\share\\dir", "////host/share/dir"),
        ("\\foo\\bar", "/foo/bar"),
        ("C:\\a b\\c", "///C:/a%20b/c"),
        ("\\\\?\\C:\\foo", "///C:/foo"),
        ("\\\\?\\UNC\\host\\share", "/host/share"),
    ]
    for path, expected in cases:
        try:
            got = pathname2url(path)
        except Exception:
            return False
        if got != expected:
            return False

    bad = ["AB:\\foo"]
    for path in bad:
        try:
            pathname2url(path)
        except OSError:
            continue
        except Exception:
            return False
        return False
    return True


def nturl2_roundtrip():
    """Verify url2pathname(pathname2url(p)) == p for typical NT paths."""
    samples = [
        "C:\\foo\\bar\\spam.foo",
        "C:\\Program Files\\Test App\\file.txt",
        "D:\\data\\readme.md",
        "\\\\host\\share\\dir\\file",
        "\\foo\\bar",
        "C:\\a b\\c%d\\e+f",
    ]
    for path in samples:
        try:
            url = pathname2url(path)
            back = url2pathname(url)
        except Exception:
            return False
        if back != path:
            return False
    return True


__all__ = [
    "url2pathname",
    "pathname2url",
    "nturl2_url2pathname",
    "nturl2_pathname2url",
    "nturl2_roundtrip",
]