"""Clean-room implementation of an xml.sax-style API.

No imports from xml.sax (or any of its submodules). Pure standard-library
implementation built from scratch.
"""

import re as _re


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class SAXException(Exception):
    """Base class for SAX exceptions."""

    def __init__(self, msg, exception=None):
        Exception.__init__(self, msg)
        self._msg = msg
        self._exception = exception

    def getMessage(self):
        return self._msg

    def getException(self):
        return self._exception

    def __str__(self):
        return self._msg

    def __getitem__(self, ix):
        raise AttributeError("__getitem__")


class SAXParseException(SAXException):
    """Exception raised by a SAX parser at parse time."""

    def __init__(self, msg, exception, locator):
        SAXException.__init__(self, msg, exception)
        self._locator = locator
        if locator is not None:
            try:
                self._systemId = locator.getSystemId()
            except Exception:
                self._systemId = None
            try:
                self._colnum = locator.getColumnNumber()
            except Exception:
                self._colnum = None
            try:
                self._linenum = locator.getLineNumber()
            except Exception:
                self._linenum = None
        else:
            self._systemId = None
            self._colnum = None
            self._linenum = None

    def getColumnNumber(self):
        return self._colnum

    def getLineNumber(self):
        return self._linenum

    def getPublicId(self):
        if self._locator is None:
            return None
        try:
            return self._locator.getPublicId()
        except Exception:
            return None

    def getSystemId(self):
        return self._systemId

    def __str__(self):
        sid = self._systemId or "<unknown>"
        line = self._linenum if self._linenum is not None else "?"
        col = self._colnum if self._colnum is not None else "?"
        return "%s:%s:%s: %s" % (sid, line, col, self._msg)


class SAXNotRecognizedException(SAXException):
    """Raised by an XMLReader when given a feature/property it does not know."""


class SAXNotSupportedException(SAXException):
    """Raised by an XMLReader when given a feature/property it does not support."""


class SAXReaderNotAvailable(SAXNotSupportedException):
    """Raised when no XML parser is available."""


# ---------------------------------------------------------------------------
# Locator
# ---------------------------------------------------------------------------

class Locator:
    def getColumnNumber(self):
        return -1

    def getLineNumber(self):
        return -1

    def getPublicId(self):
        return None

    def getSystemId(self):
        return None


class _SimpleLocator(Locator):
    def __init__(self):
        self._line = 1
        self._col = 0
        self._systemId = None
        self._publicId = None

    def getColumnNumber(self):
        return self._col

    def getLineNumber(self):
        return self._line

    def getPublicId(self):
        return self._publicId

    def getSystemId(self):
        return self._systemId


# ---------------------------------------------------------------------------
# Attributes containers
# ---------------------------------------------------------------------------

class AttributesImpl:
    def __init__(self, attrs):
        # attrs: dict mapping qname -> value
        self._attrs = dict(attrs)

    def getLength(self):
        return len(self._attrs)

    def getType(self, name):
        return "CDATA"

    def getValue(self, name):
        return self._attrs[name]

    def getValueByQName(self, name):
        return self._attrs[name]

    def getNameByQName(self, name):
        if name not in self._attrs:
            raise KeyError(name)
        return name

    def getQNameByName(self, name):
        if name not in self._attrs:
            raise KeyError(name)
        return name

    def getNames(self):
        return list(self._attrs.keys())

    def getQNames(self):
        return list(self._attrs.keys())

    def __len__(self):
        return len(self._attrs)

    def __getitem__(self, name):
        return self._attrs[name]

    def __contains__(self, name):
        return name in self._attrs

    def keys(self):
        return list(self._attrs.keys())

    def has_key(self, name):
        return name in self._attrs

    def get(self, name, alternative=None):
        return self._attrs.get(name, alternative)

    def copy(self):
        return self.__class__(self._attrs)

    def items(self):
        return list(self._attrs.items())

    def values(self):
        return list(self._attrs.values())


class AttributesNSImpl(AttributesImpl):
    def __init__(self, attrs, qnames):
        AttributesImpl.__init__(self, attrs)
        self._qnames = dict(qnames)

    def getValueByQName(self, name):
        for ns_name, qname in self._qnames.items():
            if qname == name:
                return self._attrs[ns_name]
        raise KeyError(name)

    def getNameByQName(self, name):
        for ns_name, qname in self._qnames.items():
            if qname == name:
                return ns_name
        raise KeyError(name)

    def getQNameByName(self, name):
        return self._qnames[name]

    def getQNames(self):
        return list(self._qnames.values())

    def copy(self):
        return self.__class__(self._attrs, self._qnames)


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

class ContentHandler:
    """Default content handler — all methods are no-ops."""

    def __init__(self):
        self._locator = None

    def setDocumentLocator(self, locator):
        self._locator = locator

    def startDocument(self):
        pass

    def endDocument(self):
        pass

    def startPrefixMapping(self, prefix, uri):
        pass

    def endPrefixMapping(self, prefix):
        pass

    def startElement(self, name, attrs):
        pass

    def endElement(self, name):
        pass

    def startElementNS(self, name, qname, attrs):
        pass

    def endElementNS(self, name, qname):
        pass

    def characters(self, content):
        pass

    def ignorableWhitespace(self, whitespace):
        pass

    def processingInstruction(self, target, data):
        pass

    def skippedEntity(self, name):
        pass


class ErrorHandler:
    def error(self, exception):
        raise exception

    def fatalError(self, exception):
        raise exception

    def warning(self, exception):
        # Default: just print to stderr-ish (silently ignore for simplicity)
        pass


class DTDHandler:
    def notationDecl(self, name, publicId, systemId):
        pass

    def unparsedEntityDecl(self, name, publicId, systemId, ndata):
        pass


class EntityResolver:
    def resolveEntity(self, publicId, systemId):
        return systemId


# ---------------------------------------------------------------------------
# Input source
# ---------------------------------------------------------------------------

class InputSource:
    def __init__(self, system_id=None):
        self.__system_id = system_id
        self.__public_id = None
        self.__encoding = None
        self.__byte_stream = None
        self.__character_stream = None

    def setPublicId(self, public_id):
        self.__public_id = public_id

    def getPublicId(self):
        return self.__public_id

    def setSystemId(self, system_id):
        self.__system_id = system_id

    def getSystemId(self):
        return self.__system_id

    def setEncoding(self, encoding):
        self.__encoding = encoding

    def getEncoding(self):
        return self.__encoding

    def setByteStream(self, bytefile):
        self.__byte_stream = bytefile

    def getByteStream(self):
        return self.__byte_stream

    def setCharacterStream(self, charfile):
        self.__character_stream = charfile

    def getCharacterStream(self):
        return self.__character_stream


# ---------------------------------------------------------------------------
# Parser core
# ---------------------------------------------------------------------------

_BUILTIN_ENTITIES = {
    "lt": "<",
    "gt": ">",
    "amp": "&",
    "quot": '"',
    "apos": "'",
}

_ATTR_RE = _re.compile(
    r'([A-Za-z_:][\w:.\-]*)\s*=\s*(?:"([^"]*)"|\'([^\']*)\')'
)


def _resolve_entity(ref):
    """Resolve the body (without & and ;) of an entity reference."""
    if ref.startswith("#x") or ref.startswith("#X"):
        try:
            return chr(int(ref[2:], 16))
        except (ValueError, OverflowError):
            return "&" + ref + ";"
    if ref.startswith("#"):
        try:
            return chr(int(ref[1:]))
        except (ValueError, OverflowError):
            return "&" + ref + ";"
    if ref in _BUILTIN_ENTITIES:
        return _BUILTIN_ENTITIES[ref]
    # Unknown entity — leave as-is
    return "&" + ref + ";"


def _unescape(s):
    if "&" not in s:
        return s
    out = []
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c == "&":
            j = s.find(";", i + 1)
            if j == -1:
                out.append(c)
                i += 1
                continue
            ref = s[i + 1:j]
            out.append(_resolve_entity(ref))
            i = j + 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def _parse_attrs(s):
    attrs = {}
    for m in _ATTR_RE.finditer(s):
        name = m.group(1)
        value = m.group(2) if m.group(2) is not None else m.group(3)
        attrs[name] = _unescape(value)
    return attrs


def _is_whitespace(s):
    for ch in s:
        if ch not in " \t\r\n":
            return False
    return True


def _parse(text, handler, error_handler=None, dtd_handler=None):
    if isinstance(text, bytes):
        # Try utf-8 by default
        try:
            text = text.decode("utf-8")
        except UnicodeDecodeError:
            text = text.decode("latin-1")

    if error_handler is None:
        error_handler = ErrorHandler()
    if dtd_handler is None:
        dtd_handler = DTDHandler()

    locator = _SimpleLocator()
    handler.setDocumentLocator(locator)
    handler.startDocument()

    n = len(text)
    i = 0
    stack = []

    def update_pos(start, end):
        # Track newlines for locator
        chunk = text[start:end]
        nl = chunk.count("\n")
        if nl:
            locator._line += nl
            last_nl = chunk.rfind("\n")
            locator._col = end - (start + last_nl + 1)
        else:
            locator._col += (end - start)

    while i < n:
        ch = text[i]
        if ch == "<":
            # Determine which markup construct
            if text.startswith("<!--", i):
                end = text.find("-->", i + 4)
                if end == -1:
                    exc = SAXParseException(
                        "Unterminated comment", None, locator)
                    error_handler.fatalError(exc)
                    return
                update_pos(i, end + 3)
                i = end + 3
            elif text.startswith("<![CDATA[", i):
                end = text.find("]]>", i + 9)
                if end == -1:
                    exc = SAXParseException(
                        "Unterminated CDATA section", None, locator)
                    error_handler.fatalError(exc)
                    return
                handler.characters(text[i + 9:end])
                update_pos(i, end + 3)
                i = end + 3
            elif text.startswith("<?", i):
                end = text.find("?>", i + 2)
                if end == -1:
                    exc = SAXParseException(
                        "Unterminated processing instruction", None, locator)
                    error_handler.fatalError(exc)
                    return
                content = text[i + 2:end]
                # Split target from data
                m = _re.match(r"(\S+)\s*(.*)", content, _re.DOTALL)
                if m:
                    target, data = m.group(1), m.group(2)
                else:
                    target, data = content, ""
                if target.lower() != "xml":
                    handler.processingInstruction(target, data)
                update_pos(i, end + 2)
                i = end + 2
            elif text.startswith("<!", i):
                # DOCTYPE / declaration — skip to matching '>',
                # respecting brackets for internal subset.
                j = i + 2
                depth = 0
                while j < n:
                    cc = text[j]
                    if cc == "[":
                        depth += 1
                    elif cc == "]":
                        if depth > 0:
                            depth -= 1
                    elif cc == ">" and depth == 0:
                        break
                    j += 1
                if j >= n:
                    exc = SAXParseException(
                        "Unterminated declaration", None, locator)
                    error_handler.fatalError(exc)
                    return
                update_pos(i, j + 1)
                i = j + 1
            elif text.startswith("</", i):
                end = text.find(">", i + 2)
                if end == -1:
                    exc = SAXParseException(
                        "Unterminated end tag", None, locator)
                    error_handler.fatalError(exc)
                    return
                name = text[i + 2:end].strip()
                if not stack:
                    exc = SAXParseException(
                        "Unmatched end tag: %s" % name, None, locator)
                    error_handler.fatalError(exc)
                    return
                expected = stack.pop()
                if expected != name:
                    exc = SAXParseException(
                        "Mismatched end tag: expected %s, got %s"
                        % (expected, name),
                        None, locator)
                    error_handler.fatalError(exc)
                    return
                handler.endElement(name)
                update_pos(i, end + 1)
                i = end + 1
            else:
                # Start tag (possibly self-closing).
                # Find the matching '>' that isn't inside quotes.
                j = i + 1
                in_quote = None
                while j < n:
                    cc = text[j]
                    if in_quote:
                        if cc == in_quote:
                            in_quote = None
                    else:
                        if cc == '"' or cc == "'":
                            in_quote = cc
                        elif cc == ">":
                            break
                    j += 1
                if j >= n:
                    exc = SAXParseException(
                        "Unterminated start tag", None, locator)
                    error_handler.fatalError(exc)
                    return
                content = text[i + 1:j]
                self_closing = False
                if content.endswith("/"):
                    self_closing = True
                    content = content[:-1]
                m = _re.match(r"(\S+)(?:\s+(.*))?$", content, _re.DOTALL)
                if not m:
                    exc = SAXParseException(
                        "Malformed start tag", None, locator)
                    error_handler.fatalError(exc)
                    return
                name = m.group(1)
                attrs_str = m.group(2) or ""
                attrs = _parse_attrs(attrs_str)
                handler.startElement(name, AttributesImpl(attrs))
                if self_closing:
                    handler.endElement(name)
                else:
                    stack.append(name)
                update_pos(i, j + 1)
                i = j + 1
        else:
            # Character data up to next '<'
            end = text.find("<", i)
            if end == -1:
                end = n
            chunk = text[i:end]
            if chunk:
                decoded = _unescape(chunk)
                if _is_whitespace(decoded) and not stack:
                    # Whitespace outside the root — ignore
                    pass
                else:
                    handler.characters(decoded)
            update_pos(i, end)
            i = end

    if stack:
        exc = SAXParseException(
            "Unclosed elements: %s" % ", ".join(stack), None, locator)
        error_handler.fatalError(exc)
        return

    handler.endDocument()


# ---------------------------------------------------------------------------
# Public top-level API
# ---------------------------------------------------------------------------

def parseString(string, handler, errorHandler=None):
    """Parse an XML document supplied as a string or bytes."""
    if errorHandler is None:
        errorHandler = ErrorHandler()
    _parse(string, handler, errorHandler)


def parse(source, handler, errorHandler=None):
    """Parse an XML document from a filename, file-like object, or InputSource."""
    if errorHandler is None:
        errorHandler = ErrorHandler()

    if isinstance(source, InputSource):
        cs = source.getCharacterStream()
        if cs is not None:
            data = cs.read()
        else:
            bs = source.getByteStream()
            if bs is not None:
                data = bs.read()
            else:
                sysid = source.getSystemId()
                if sysid is None:
                    raise SAXException("InputSource has no data source")
                with open(sysid, "rb") as f:
                    data = f.read()
    elif isinstance(source, str):
        with open(source, "rb") as f:
            data = f.read()
    elif isinstance(source, (bytes, bytearray)):
        data = bytes(source)
    elif hasattr(source, "read"):
        data = source.read()
    else:
        raise SAXException("Cannot parse source of type %r" % type(source))

    _parse(data, handler, errorHandler)


# ---------------------------------------------------------------------------
# XMLReader / make_parser
# ---------------------------------------------------------------------------

class XMLReader:
    def __init__(self):
        self._cont_handler = ContentHandler()
        self._dtd_handler = DTDHandler()
        self._ent_handler = EntityResolver()
        self._err_handler = ErrorHandler()

    def parse(self, source):
        parse(source, self._cont_handler, self._err_handler)

    def getContentHandler(self):
        return self._cont_handler

    def setContentHandler(self, handler):
        self._cont_handler = handler

    def getDTDHandler(self):
        return self._dtd_handler

    def setDTDHandler(self, handler):
        self._dtd_handler = handler

    def getEntityResolver(self):
        return self._ent_handler

    def setEntityResolver(self, resolver):
        self._ent_handler = resolver

    def getErrorHandler(self):
        return self._err_handler

    def setErrorHandler(self, handler):
        self._err_handler = handler

    def setLocale(self, locale):
        pass

    def getFeature(self, name):
        raise SAXNotRecognizedException("Feature %r not recognized" % name)

    def setFeature(self, name, state):
        raise SAXNotRecognizedException("Feature %r not recognized" % name)

    def getProperty(self, name):
        raise SAXNotRecognizedException("Property %r not recognized" % name)

    def setProperty(self, name, value):
        raise SAXNotRecognizedException("Property %r not recognized" % name)


class IncrementalParser(XMLReader):
    def __init__(self, bufsize=2 ** 16):
        XMLReader.__init__(self)
        self._bufsize = bufsize
        self._buffer = ""
        self._parsing = False

    def feed(self, data):
        if isinstance(data, bytes):
            data = data.decode("utf-8", "replace")
        self._buffer += data

    def prepareParser(self, source):
        pass

    def close(self):
        if self._buffer:
            _parse(self._buffer, self._cont_handler, self._err_handler)
            self._buffer = ""

    def reset(self):
        self._buffer = ""
        self._parsing = False


def make_parser(parser_list=()):
    """Return an XMLReader. The parser_list argument is accepted for
    API compatibility but ignored — only the built-in reader is supported."""
    return XMLReader()


# Common feature/property name constants (compatibility)
feature_namespaces = "http://xml.org/sax/features/namespaces"
feature_namespace_prefixes = "http://xml.org/sax/features/namespace-prefixes"
feature_string_interning = "http://xml.org/sax/features/string-interning"
feature_validation = "http://xml.org/sax/features/validation"
feature_external_ges = "http://xml.org/sax/features/external-general-entities"
feature_external_pes = "http://xml.org/sax/features/external-parameter-entities"
all_features = [
    feature_namespaces,
    feature_namespace_prefixes,
    feature_string_interning,
    feature_validation,
    feature_external_ges,
    feature_external_pes,
]

property_lexical_handler = "http://xml.org/sax/properties/lexical-handler"
property_declaration_handler = "http://xml.org/sax/properties/declaration-handler"
property_dom_node = "http://xml.org/sax/properties/dom-node"
property_xml_string = "http://xml.org/sax/properties/xml-string"
property_encoding = "http://www.python.org/sax/properties/encoding"
property_interning_dict = "http://www.python.org/sax/properties/interning-dict"
all_properties = [
    property_lexical_handler,
    property_declaration_handler,
    property_dom_node,
    property_xml_string,
    property_encoding,
    property_interning_dict,
]


# ---------------------------------------------------------------------------
# Invariant test functions
# ---------------------------------------------------------------------------

def xmlsax2_exceptions():
    """Verify the exception hierarchy and message-bearing behavior."""
    try:
        # Base exception carries a message and is an Exception.
        e1 = SAXException("base")
        if not isinstance(e1, Exception):
            return False
        if e1.getMessage() != "base":
            return False

        # SAXParseException is a SAXException with locator info.
        loc = _SimpleLocator()
        loc._line = 5
        loc._col = 9
        e2 = SAXParseException("parse failure", None, loc)
        if not isinstance(e2, SAXException):
            return False
        if e2.getLineNumber() != 5 or e2.getColumnNumber() != 9:
            return False

        # SAXNotRecognizedException / SAXNotSupportedException both inherit.
        e3 = SAXNotRecognizedException("nrx")
        e4 = SAXNotSupportedException("nsx")
        if not isinstance(e3, SAXException):
            return False
        if not isinstance(e4, SAXException):
            return False

        # They must actually be raisable and catchable as SAXException.
        try:
            raise SAXParseException("boom", None, None)
        except SAXException as ex:
            if ex.getMessage() != "boom":
                return False

        return True
    except Exception:
        return False


def xmlsax2_parsestring():
    """Verify parseString parses XML and dispatches handler events."""
    try:
        events = []

        class _H(ContentHandler):
            def startDocument(self):
                events.append(("sd",))

            def endDocument(self):
                events.append(("ed",))

            def startElement(self, name, attrs):
                events.append(("se", name, dict(attrs.items())))

            def endElement(self, name):
                events.append(("ee", name))

            def characters(self, content):
                events.append(("ch", content))

            def processingInstruction(self, target, data):
                events.append(("pi", target, data))

        h = _H()
        parseString(
            "<?xml version='1.0'?>"
            "<root attr='v&amp;1'>"
            "<child>hello&lt;world</child>"
            "<empty/>"
            "<!-- a comment -->"
            "<![CDATA[<raw>]]>"
            "<?php do() ?>"
            "</root>",
            h,
        )

        # First and last events must be document-bracketing.
        if not events or events[0] != ("sd",) or events[-1] != ("ed",):
            return False

        # Must see start/end for root with the unescaped attribute.
        saw_root_start = False
        saw_root_end = False
        saw_child_chars = False
        saw_empty_self_close = False
        saw_cdata = False
        saw_pi = False
        for ev in events:
            if ev[0] == "se" and ev[1] == "root":
                if ev[2].get("attr") == "v&1":
                    saw_root_start = True
            if ev[0] == "ee" and ev[1] == "root":
                saw_root_end = True
            if ev[0] == "ch" and "hello<world" in ev[1]:
                saw_child_chars = True
            if ev[0] == "ch" and "<raw>" in ev[1]:
                saw_cdata = True
            if ev[0] == "pi" and ev[1] == "php":
                saw_pi = True

        # Empty element must produce both se and ee for "empty"
        names = [(e[0], e[1]) for e in events if e[0] in ("se", "ee")]
        for k in range(len(names) - 1):
            if names[k] == ("se", "empty") and names[k + 1] == ("ee", "empty"):
                saw_empty_self_close = True
                break

        return all([
            saw_root_start, saw_root_end, saw_child_chars,
            saw_empty_self_close, saw_cdata, saw_pi,
        ])
    except Exception:
        return False


def xmlsax2_handler():
    """Verify the handler base classes have the expected interface."""
    try:
        # ContentHandler default methods must exist and be no-ops.
        ch = ContentHandler()
        ch.setDocumentLocator(_SimpleLocator())
        ch.startDocument()
        ch.startPrefixMapping("p", "urn:p")
        ch.startElement("e", AttributesImpl({"a": "1"}))
        ch.characters("text")
        ch.ignorableWhitespace("  ")
        ch.processingInstruction("t", "d")
        ch.skippedEntity("ent")
        ch.endElement("e")
        ch.endPrefixMapping("p")
        ch.endDocument()

        # AttributesImpl must support the expected protocol.
        a = AttributesImpl({"x": "1", "y": "2"})
        if a.getLength() != 2:
            return False
        if a.getValue("x") != "1":
            return False
        if "y" not in a:
            return False
        if a.getType("x") != "CDATA":
            return False
        if sorted(a.getNames()) != ["x", "y"]:
            return False

        # ErrorHandler.error / fatalError raise; warning is silent.
        eh = ErrorHandler()
        raised = False
        try:
            eh.error(SAXException("err"))
        except SAXException:
            raised = True
        if not raised:
            return False
        raised = False
        try:
            eh.fatalError(SAXException("fatal"))
        except SAXException:
            raised = True
        if not raised:
            return False
        eh.warning(SAXException("warn"))  # must not raise

        # DTDHandler / EntityResolver interfaces present.
        dh = DTDHandler()
        dh.notationDecl("n", "p", "s")
        dh.unparsedEntityDecl("n", "p", "s", "nd")

        er = EntityResolver()
        if er.resolveEntity("p", "sysid") != "sysid":
            return False

        # XMLReader wires the handlers correctly.
        rdr = make_parser()
        if not isinstance(rdr, XMLReader):
            return False
        new_ch = ContentHandler()
        rdr.setContentHandler(new_ch)
        if rdr.getContentHandler() is not new_ch:
            return False
        try:
            rdr.getFeature("nope")
            return False
        except SAXNotRecognizedException:
            pass

        return True
    except Exception:
        return False