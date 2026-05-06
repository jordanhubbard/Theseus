"""Clean-room implementation of a minimal pyexpat-like module.

This module provides a from-scratch XML parser facade. It does NOT import
the original ``pyexpat`` module or any third-party library. Only the Python
standard library is used.

The public surface required by the Theseus invariants:

* :func:`pyexp2_parser`  - returns ``True`` once an XML parser object can be
  constructed via :func:`ParserCreate`.
* :func:`pyexp2_version` - returns ``True`` once a version string is exposed.
* :func:`pyexp2_error`   - returns ``True`` once the :class:`ExpatError`
  exception type is available.
"""

# ---------------------------------------------------------------------------
# Module level metadata
# ---------------------------------------------------------------------------

__version__ = "1.0.0"
EXPAT_VERSION = "expat_2.5.0_cleanroom"
version_info = (2, 5, 0)
native_encoding = "UTF-8"
features = [
    ("sizeof(XML_Char)", 1),
    ("sizeof(XML_LChar)", 1),
    ("XML_DTD", 0),
    ("XML_NS", 0),
]


# ---------------------------------------------------------------------------
# Error model - mirrors the basic surface of pyexpat.ExpatError
# ---------------------------------------------------------------------------


class ExpatError(Exception):
    """Raised when the clean-room parser encounters malformed XML."""

    def __init__(self, message="", lineno=1, offset=0, code=0):
        super().__init__(message)
        self.lineno = lineno
        self.offset = offset
        self.code = code


# Alias used by the standard pyexpat module - kept here for compatibility.
error = ExpatError


# Numeric error codes, modelled loosely on libexpat's XML_Error enum.
class errors:
    XML_ERROR_NONE = 0
    XML_ERROR_NO_MEMORY = 1
    XML_ERROR_SYNTAX = 2
    XML_ERROR_NO_ELEMENTS = 3
    XML_ERROR_INVALID_TOKEN = 4
    XML_ERROR_UNCLOSED_TOKEN = 5
    XML_ERROR_PARTIAL_CHAR = 6
    XML_ERROR_TAG_MISMATCH = 7
    XML_ERROR_DUPLICATE_ATTRIBUTE = 8
    XML_ERROR_JUNK_AFTER_DOC_ELEMENT = 9
    XML_ERROR_UNDEFINED_ENTITY = 11

    _messages = {
        0: "no error",
        1: "out of memory",
        2: "syntax error",
        3: "no element found",
        4: "not well-formed (invalid token)",
        5: "unclosed token",
        6: "partial character",
        7: "mismatched tag",
        8: "duplicate attribute",
        9: "junk after document element",
        11: "undefined entity",
    }


def ErrorString(code):
    """Return the human readable message for an error code."""
    return errors._messages.get(code, "unknown error")


# ---------------------------------------------------------------------------
# Built-in XML entity table.
# ---------------------------------------------------------------------------

_ENTITIES = {
    "amp": "&",
    "lt": "<",
    "gt": ">",
    "apos": "'",
    "quot": '"',
}


def _decode_entities(text):
    """Replace XML entity references in ``text`` with their characters."""
    out = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "&":
            end = text.find(";", i + 1)
            if end == -1:
                raise ExpatError("unterminated entity reference",
                                 code=errors.XML_ERROR_INVALID_TOKEN)
            ref = text[i + 1:end]
            if ref.startswith("#"):
                try:
                    if ref.startswith("#x") or ref.startswith("#X"):
                        cp = int(ref[2:], 16)
                    else:
                        cp = int(ref[1:], 10)
                except ValueError:
                    raise ExpatError("invalid character reference",
                                     code=errors.XML_ERROR_INVALID_TOKEN)
                out.append(chr(cp))
            elif ref in _ENTITIES:
                out.append(_ENTITIES[ref])
            else:
                raise ExpatError("undefined entity %s" % ref,
                                 code=errors.XML_ERROR_UNDEFINED_ENTITY)
            i = end + 1
        else:
            out.append(ch)
            i += 1
    return "".join(out)


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------


_NAME_START = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_:"
)
_NAME_CHARS = _NAME_START + "0123456789-."


def _is_name_start(ch):
    return ch in _NAME_START


def _is_name_char(ch):
    return ch in _NAME_CHARS


def _skip_whitespace(text, i):
    n = len(text)
    while i < n and text[i] in " \t\r\n":
        i += 1
    return i


def _read_name(text, i):
    n = len(text)
    if i >= n or not _is_name_start(text[i]):
        raise ExpatError("expected name", code=errors.XML_ERROR_INVALID_TOKEN)
    start = i
    while i < n and _is_name_char(text[i]):
        i += 1
    return text[start:i], i


def _read_quoted(text, i):
    n = len(text)
    if i >= n or text[i] not in ("'", '"'):
        raise ExpatError("expected quoted value",
                         code=errors.XML_ERROR_INVALID_TOKEN)
    quote = text[i]
    i += 1
    start = i
    while i < n and text[i] != quote:
        i += 1
    if i >= n:
        raise ExpatError("unterminated quoted value",
                         code=errors.XML_ERROR_UNCLOSED_TOKEN)
    value = text[start:i]
    return value, i + 1


# ---------------------------------------------------------------------------
# Parser implementation
# ---------------------------------------------------------------------------


class _XMLParser(object):
    """Pure-Python streaming XML parser modelled on the pyexpat surface."""

    _CALLBACK_NAMES = (
        "StartElementHandler",
        "EndElementHandler",
        "CharacterDataHandler",
        "ProcessingInstructionHandler",
        "CommentHandler",
        "StartCdataSectionHandler",
        "EndCdataSectionHandler",
        "XmlDeclHandler",
        "DefaultHandler",
        "DefaultHandlerExpand",
    )

    def __init__(self, encoding=None, namespace_separator=None):
        self.encoding = encoding or "UTF-8"
        self.namespace_separator = namespace_separator
        for name in self._CALLBACK_NAMES:
            setattr(self, name, None)
        self._buffer = ""
        self._final = False
        self._pos = 0
        self._line = 1
        self._col = 0
        self._stack = []
        self.ErrorCode = errors.XML_ERROR_NONE
        self.ErrorLineNumber = 1
        self.ErrorColumnNumber = 0
        self.ErrorByteIndex = 0
        self.CurrentLineNumber = 1
        self.CurrentColumnNumber = 0
        self.CurrentByteIndex = 0
        self.buffer_text = False
        self.buffer_size = 8192
        self.buffer_used = 0
        self.ordered_attributes = False
        self.specified_attributes = False

    # -- input handling ------------------------------------------------------

    def Parse(self, data, isfinal=0):
        if isinstance(data, (bytes, bytearray)):
            try:
                data = data.decode(self.encoding)
            except (LookupError, UnicodeDecodeError) as exc:
                raise ExpatError(str(exc),
                                 code=errors.XML_ERROR_INVALID_TOKEN)
        self._buffer += data
        if isfinal:
            self._final = True
        try:
            self._drive()
        except ExpatError as exc:
            self.ErrorCode = exc.code
            self.ErrorLineNumber = exc.lineno
            self.ErrorColumnNumber = exc.offset
            raise
        if isfinal and not self._final_seen_root():
            raise ExpatError("no element found",
                             lineno=self._line, offset=self._col,
                             code=errors.XML_ERROR_NO_ELEMENTS)
        return 1

    def ParseFile(self, fileobj):
        while True:
            chunk = fileobj.read(self.buffer_size)
            if not chunk:
                return self.Parse(b"", 1)
            self.Parse(chunk, 0)

    def SetBase(self, base):
        self._base = base

    def GetBase(self):
        return getattr(self, "_base", None)

    def GetInputContext(self):
        return self._buffer

    def SetParamEntityParsing(self, flag):
        return 0

    def UseForeignDTD(self, flag=True):
        return None

    # -- internals -----------------------------------------------------------

    _saw_root = False

    def _final_seen_root(self):
        return self._saw_root and not self._stack

    def _emit_text(self, text):
        if not text:
            return
        try:
            decoded = _decode_entities(text)
        except ExpatError as exc:
            exc.lineno = self._line
            exc.offset = self._col
            raise
        if self.CharacterDataHandler is not None:
            self.CharacterDataHandler(decoded)
        elif self.DefaultHandlerExpand is not None:
            self.DefaultHandlerExpand(decoded)
        elif self.DefaultHandler is not None:
            self.DefaultHandler(text)

    def _advance(self, count):
        chunk = self._buffer[self._pos:self._pos + count]
        for ch in chunk:
            if ch == "\n":
                self._line += 1
                self._col = 0
            else:
                self._col += 1
        self._pos += count

    def _drive(self):
        buf = self._buffer
        n = len(buf)
        text_start = self._pos
        while self._pos < n:
            ch = buf[self._pos]
            if ch == "<":
                # flush any pending character data
                if text_start < self._pos:
                    self._emit_text(buf[text_start:self._pos])
                # decide which construct
                if buf.startswith("<!--", self._pos):
                    end = buf.find("-->", self._pos + 4)
                    if end == -1:
                        if self._final:
                            raise ExpatError("unterminated comment",
                                             lineno=self._line,
                                             offset=self._col,
                                             code=errors.XML_ERROR_UNCLOSED_TOKEN)
                        break
                    comment = buf[self._pos + 4:end]
                    if self.CommentHandler is not None:
                        self.CommentHandler(comment)
                    self._advance((end + 3) - self._pos)
                    text_start = self._pos
                elif buf.startswith("<![CDATA[", self._pos):
                    end = buf.find("]]>", self._pos + 9)
                    if end == -1:
                        if self._final:
                            raise ExpatError("unterminated CDATA",
                                             lineno=self._line,
                                             offset=self._col,
                                             code=errors.XML_ERROR_UNCLOSED_TOKEN)
                        break
                    cdata = buf[self._pos + 9:end]
                    if self.StartCdataSectionHandler is not None:
                        self.StartCdataSectionHandler()
                    if self.CharacterDataHandler is not None:
                        self.CharacterDataHandler(cdata)
                    if self.EndCdataSectionHandler is not None:
                        self.EndCdataSectionHandler()
                    self._advance((end + 3) - self._pos)
                    text_start = self._pos
                elif buf.startswith("<?", self._pos):
                    end = buf.find("?>", self._pos + 2)
                    if end == -1:
                        if self._final:
                            raise ExpatError("unterminated processing instruction",
                                             lineno=self._line,
                                             offset=self._col,
                                             code=errors.XML_ERROR_UNCLOSED_TOKEN)
                        break
                    body = buf[self._pos + 2:end]
                    target, _, rest = body.partition(" ")
                    if target.lower() == "xml":
                        if self.XmlDeclHandler is not None:
                            self.XmlDeclHandler(self.encoding, None, -1)
                    else:
                        if self.ProcessingInstructionHandler is not None:
                            self.ProcessingInstructionHandler(target, rest.lstrip())
                    self._advance((end + 2) - self._pos)
                    text_start = self._pos
                elif buf.startswith("</", self._pos):
                    end = buf.find(">", self._pos + 2)
                    if end == -1:
                        if self._final:
                            raise ExpatError("unterminated end tag",
                                             lineno=self._line,
                                             offset=self._col,
                                             code=errors.XML_ERROR_UNCLOSED_TOKEN)
                        break
                    name_part = buf[self._pos + 2:end].strip()
                    if not name_part:
                        raise ExpatError("empty end tag",
                                         lineno=self._line,
                                         offset=self._col,
                                         code=errors.XML_ERROR_INVALID_TOKEN)
                    if not self._stack or self._stack[-1] != name_part:
                        raise ExpatError("mismatched tag",
                                         lineno=self._line,
                                         offset=self._col,
                                         code=errors.XML_ERROR_TAG_MISMATCH)
                    self._stack.pop()
                    if self.EndElementHandler is not None:
                        self.EndElementHandler(name_part)
                    self._advance((end + 1) - self._pos)
                    text_start = self._pos
                elif buf.startswith("<!", self._pos):
                    # DOCTYPE / other declarations - skip until '>'
                    end = buf.find(">", self._pos + 2)
                    if end == -1:
                        if self._final:
                            raise ExpatError("unterminated declaration",
                                             lineno=self._line,
                                             offset=self._col,
                                             code=errors.XML_ERROR_UNCLOSED_TOKEN)
                        break
                    self._advance((end + 1) - self._pos)
                    text_start = self._pos
                else:
                    # start tag (possibly self closing)
                    end = self._find_tag_end(buf, self._pos + 1)
                    if end == -1:
                        if self._final:
                            raise ExpatError("unterminated start tag",
                                             lineno=self._line,
                                             offset=self._col,
                                             code=errors.XML_ERROR_UNCLOSED_TOKEN)
                        break
                    inner = buf[self._pos + 1:end]
                    self_closing = inner.endswith("/")
                    if self_closing:
                        inner = inner[:-1]
                    name, attrs = self._parse_tag(inner)
                    self._saw_root = True
                    if self.StartElementHandler is not None:
                        self.StartElementHandler(name, attrs)
                    if self_closing:
                        if self.EndElementHandler is not None:
                            self.EndElementHandler(name)
                    else:
                        self._stack.append(name)
                    self._advance((end + 1) - self._pos)
                    text_start = self._pos
            else:
                self._advance(1)
        # flush trailing text on final
        if self._final and text_start < self._pos:
            self._emit_text(buf[text_start:self._pos])
            text_start = self._pos
        # Drop processed prefix to keep the buffer small.
        if text_start > 0:
            self._buffer = self._buffer[text_start:]
            self._pos -= text_start

    def _find_tag_end(self, buf, start):
        """Find the closing '>' of a start tag, respecting quoted attrs."""
        n = len(buf)
        i = start
        quote = None
        while i < n:
            ch = buf[i]
            if quote is not None:
                if ch == quote:
                    quote = None
            elif ch in ("'", '"'):
                quote = ch
            elif ch == ">":
                return i
            elif ch == "<":
                raise ExpatError("invalid '<' inside tag",
                                 lineno=self._line,
                                 offset=self._col,
                                 code=errors.XML_ERROR_INVALID_TOKEN)
            i += 1
        return -1

    def _parse_tag(self, body):
        body = body.strip()
        if not body:
            raise ExpatError("empty start tag",
                             code=errors.XML_ERROR_INVALID_TOKEN)
        i = 0
        name, i = _read_name(body, i)
        attrs = []
        seen = set()
        n = len(body)
        while i < n:
            i = _skip_whitespace(body, i)
            if i >= n:
                break
            attr_name, i = _read_name(body, i)
            i = _skip_whitespace(body, i)
            if i >= n or body[i] != "=":
                raise ExpatError("attribute missing '='",
                                 code=errors.XML_ERROR_INVALID_TOKEN)
            i += 1
            i = _skip_whitespace(body, i)
            value, i = _read_quoted(body, i)
            value = _decode_entities(value)
            if attr_name in seen:
                raise ExpatError("duplicate attribute",
                                 code=errors.XML_ERROR_DUPLICATE_ATTRIBUTE)
            seen.add(attr_name)
            attrs.append((attr_name, value))
        if self.ordered_attributes:
            flat = []
            for k, v in attrs:
                flat.append(k)
                flat.append(v)
            return name, flat
        return name, dict(attrs)


# ---------------------------------------------------------------------------
# Public factory
# ---------------------------------------------------------------------------


def ParserCreate(encoding=None, namespace_separator=None, intern=None):
    """Create and return a new clean-room XML parser instance."""
    return _XMLParser(encoding=encoding,
                      namespace_separator=namespace_separator)


# ---------------------------------------------------------------------------
# Invariant probes
# ---------------------------------------------------------------------------


def pyexp2_parser():
    """Confirm a parser object can be created with the public factory."""
    parser = ParserCreate()
    return isinstance(parser, _XMLParser)


def pyexp2_version():
    """Confirm the module exposes a non-empty version string."""
    return isinstance(EXPAT_VERSION, str) and len(EXPAT_VERSION) > 0


def pyexp2_error():
    """Confirm the ExpatError exception type is exported and usable."""
    try:
        raise ExpatError("probe", lineno=1, offset=0,
                         code=errors.XML_ERROR_NONE)
    except ExpatError:
        return issubclass(ExpatError, Exception) and error is ExpatError


__all__ = [
    "ParserCreate",
    "ExpatError",
    "error",
    "errors",
    "ErrorString",
    "EXPAT_VERSION",
    "version_info",
    "native_encoding",
    "features",
    "__version__",
    "pyexp2_parser",
    "pyexp2_version",
    "pyexp2_error",
]