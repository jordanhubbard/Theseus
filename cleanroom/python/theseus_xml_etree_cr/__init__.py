"""
theseus_xml_etree_cr — Clean-room XML ElementTree-like module.

Implemented from scratch using only Python built-ins (re, io). Does NOT
import xml.etree.ElementTree, lxml, or any other XML library.
"""

import re as _re
import io as _io


# ---------------------------------------------------------------------------
# Element model
# ---------------------------------------------------------------------------

class Element(object):
    """A minimal XML element node."""

    def __init__(self, tag, attrib=None, **extra):
        self.tag = tag
        self.attrib = {} if attrib is None else dict(attrib)
        if extra:
            self.attrib.update(extra)
        self.text = None
        self.tail = None
        self._children = []

    # Container protocol -----------------------------------------------------
    def __len__(self):
        return len(self._children)

    def __iter__(self):
        return iter(self._children)

    def __getitem__(self, index):
        return self._children[index]

    def __setitem__(self, index, element):
        self._children[index] = element

    def __delitem__(self, index):
        del self._children[index]

    def __repr__(self):
        return "<Element %r at 0x%x>" % (self.tag, id(self))

    # Mutation ---------------------------------------------------------------
    def append(self, element):
        self._children.append(element)

    def extend(self, elements):
        self._children.extend(elements)

    def insert(self, index, element):
        self._children.insert(index, element)

    def remove(self, element):
        self._children.remove(element)

    # Attribute accessors ----------------------------------------------------
    def get(self, key, default=None):
        return self.attrib.get(key, default)

    def set(self, key, value):
        self.attrib[key] = value

    def keys(self):
        return self.attrib.keys()

    def items(self):
        return self.attrib.items()

    # Traversal --------------------------------------------------------------
    def iter(self, tag=None):
        if tag == "*":
            tag = None
        if tag is None or self.tag == tag:
            yield self
        for child in self._children:
            for sub in child.iter(tag):
                yield sub

    def itertext(self):
        if self.text:
            yield self.text
        for child in self._children:
            for t in child.itertext():
                yield t
            if child.tail:
                yield child.tail

    def findall(self, path):
        results = []
        if path == "." or path == "":
            return [self]
        # Strip a leading "./"
        if path.startswith("./"):
            path = path[2:]
        # Recursive descendant: ".//tag"
        if path.startswith(".//"):
            tag = path[3:]
            for el in self.iter(tag):
                if el is not self:
                    results.append(el)
            return results
        if path == "*":
            return list(self._children)
        # Simple direct-child match (possibly slash-separated)
        parts = path.split("/")
        current = [self]
        for part in parts:
            nxt = []
            if part == "*":
                for c in current:
                    nxt.extend(c._children)
            else:
                for c in current:
                    for child in c._children:
                        if child.tag == part:
                            nxt.append(child)
            current = nxt
        return current

    def find(self, path):
        matches = self.findall(path)
        return matches[0] if matches else None

    def findtext(self, path, default=None):
        el = self.find(path)
        if el is None:
            return default
        return el.text or ""


# ---------------------------------------------------------------------------
# Entity decoding
# ---------------------------------------------------------------------------

_ENTITY_RE = _re.compile(r"&(#x?[0-9A-Fa-f]+|[A-Za-z][A-Za-z0-9]*);")
_NAMED_ENTITIES = {
    "lt": "<",
    "gt": ">",
    "amp": "&",
    "quot": '"',
    "apos": "'",
}


def _decode_entities(text):
    if text is None or "&" not in text:
        return text

    def repl(m):
        ref = m.group(1)
        if ref.startswith("#x") or ref.startswith("#X"):
            try:
                return chr(int(ref[2:], 16))
            except ValueError:
                return m.group(0)
        if ref.startswith("#"):
            try:
                return chr(int(ref[1:]))
            except ValueError:
                return m.group(0)
        return _NAMED_ENTITIES.get(ref, m.group(0))

    return _ENTITY_RE.sub(repl, text)


# ---------------------------------------------------------------------------
# Hand-rolled XML tokenizer / parser
# ---------------------------------------------------------------------------

_ATTR_RE = _re.compile(
    r'([^\s=/>]+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\')'
)


def _parse_attrs(attr_str):
    out = {}
    for m in _ATTR_RE.finditer(attr_str):
        name = m.group(1)
        value = m.group(2) if m.group(2) is not None else m.group(3)
        out[name] = _decode_entities(value)
    return out


class ParseError(SyntaxError):
    """Raised on malformed XML input."""


def _parse_string(data):
    """Parse a complete XML document from ``data`` (str) into the root Element."""
    if isinstance(data, bytes):
        # Best-effort decode honoring an XML declaration's encoding hint.
        encoding = "utf-8"
        decl_match = _re.match(rb'\s*<\?xml[^>]*encoding\s*=\s*["\']([^"\']+)["\']', data)
        if decl_match:
            try:
                encoding = decl_match.group(1).decode("ascii")
            except Exception:
                encoding = "utf-8"
        data = data.decode(encoding)

    i = 0
    n = len(data)
    root = None
    stack = []
    last_child_of = {}  # id(parent) -> last appended child (for tail handling)
    last_closed = None

    while i < n:
        ch = data[i]
        if ch == "<":
            # Determine tag type
            if data.startswith("<!--", i):
                end = data.find("-->", i + 4)
                if end == -1:
                    raise ParseError("Unterminated comment")
                i = end + 3
                continue
            if data.startswith("<![CDATA[", i):
                end = data.find("]]>", i + 9)
                if end == -1:
                    raise ParseError("Unterminated CDATA")
                cdata = data[i + 9:end]
                if stack:
                    parent = stack[-1]
                    if parent._children:
                        last = parent._children[-1]
                        last.tail = (last.tail or "") + cdata
                    else:
                        parent.text = (parent.text or "") + cdata
                i = end + 3
                continue
            if data.startswith("<?", i):
                end = data.find("?>", i + 2)
                if end == -1:
                    raise ParseError("Unterminated processing instruction")
                i = end + 2
                continue
            if data.startswith("<!", i):
                # DOCTYPE or other declaration; skip until matching '>'
                # Naive: handle nested brackets for internal subset.
                depth = 0
                j = i + 2
                while j < n:
                    c = data[j]
                    if c == "[":
                        depth += 1
                    elif c == "]":
                        depth -= 1
                    elif c == ">" and depth <= 0:
                        break
                    j += 1
                if j >= n:
                    raise ParseError("Unterminated declaration")
                i = j + 1
                continue
            if data.startswith("</", i):
                end = data.find(">", i + 2)
                if end == -1:
                    raise ParseError("Unterminated end tag")
                tag = data[i + 2:end].strip()
                if not stack:
                    raise ParseError("Unexpected end tag: %s" % tag)
                top = stack.pop()
                if top.tag != tag:
                    raise ParseError("Mismatched end tag: %s vs %s" % (top.tag, tag))
                last_closed = top
                i = end + 1
                continue

            # Start tag (possibly self-closing)
            end = data.find(">", i + 1)
            if end == -1:
                raise ParseError("Unterminated start tag")
            inner = data[i + 1:end]
            self_closing = False
            if inner.endswith("/"):
                self_closing = True
                inner = inner[:-1]
            # Split tag name from attributes
            m = _re.match(r"\s*([^\s/>]+)\s*(.*)$", inner, _re.DOTALL)
            if not m:
                raise ParseError("Malformed start tag")
            tag = m.group(1)
            attr_str = m.group(2)
            attrs = _parse_attrs(attr_str) if attr_str.strip() else {}
            elem = Element(tag, attrs)
            if stack:
                stack[-1].append(elem)
            else:
                if root is not None:
                    raise ParseError("Multiple root elements")
                root = elem
            if not self_closing:
                stack.append(elem)
            else:
                last_closed = elem
            i = end + 1
            continue
        else:
            # Text content
            end = data.find("<", i)
            if end == -1:
                end = n
            text = data[i:end]
            if stack:
                parent = stack[-1]
                decoded = _decode_entities(text)
                if parent._children:
                    last = parent._children[-1]
                    last.tail = (last.tail or "") + decoded
                else:
                    parent.text = (parent.text or "") + decoded
            else:
                # Text outside any element — only whitespace tolerated
                if text.strip():
                    # Could be tail of root after close
                    if last_closed is not None:
                        last_closed.tail = (last_closed.tail or "") + _decode_entities(text)
            i = end

    if stack:
        raise ParseError("Unclosed element: %s" % stack[-1].tag)
    if root is None:
        raise ParseError("No root element")
    return root


# ---------------------------------------------------------------------------
# Public parse helpers
# ---------------------------------------------------------------------------

def fromstring(text):
    """Parse an XML document from a string and return the root Element."""
    return _parse_string(text)


def parse(source):
    """Parse an XML document from a file path or file-like object.

    Returns an ElementTree wrapping the root element.
    """
    if hasattr(source, "read"):
        data = source.read()
    else:
        with open(source, "rb") as fh:
            data = fh.read()
    root = _parse_string(data)
    return ElementTree(root)


class ElementTree(object):
    def __init__(self, element=None):
        self._root = element

    def getroot(self):
        return self._root

    def find(self, path):
        if self._root is None:
            return None
        return self._root.find(path)

    def findall(self, path):
        if self._root is None:
            return []
        return self._root.findall(path)

    def findtext(self, path, default=None):
        if self._root is None:
            return default
        return self._root.findtext(path, default)

    def iter(self, tag=None):
        if self._root is None:
            return iter(())
        return self._root.iter(tag)

    def write(self, file_or_path, encoding=None, xml_declaration=None):
        data = tostring(self._root, encoding=encoding or "us-ascii")
        if xml_declaration:
            decl = ('<?xml version="1.0" encoding="%s"?>\n'
                    % (encoding or "us-ascii")).encode("ascii")
            data = decl + data
        if hasattr(file_or_path, "write"):
            file_or_path.write(data)
        else:
            with open(file_or_path, "wb") as fh:
                fh.write(data)


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

def _escape_text(text):
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;"))


def _escape_attr(value):
    return (value.replace("&", "&amp;")
                 .replace("<", "&lt;")
                 .replace(">", "&gt;")
                 .replace('"', "&quot;")
                 .replace("\n", "&#10;")
                 .replace("\r", "&#13;")
                 .replace("\t", "&#9;"))


def _serialize(elem, out):
    out.write("<")
    out.write(elem.tag)
    for k, v in elem.attrib.items():
        out.write(' %s="%s"' % (k, _escape_attr(str(v))))
    if not elem._children and (elem.text is None or elem.text == ""):
        out.write(" />")
    else:
        out.write(">")
        if elem.text:
            out.write(_escape_text(elem.text))
        for child in elem._children:
            _serialize(child, out)
        out.write("</%s>" % elem.tag)
    if elem.tail:
        out.write(_escape_text(elem.tail))


def tostring(element, encoding=None, method=None):
    """Serialize ``element`` to XML.

    With no encoding (or "us-ascii"/"utf-8"), returns bytes. With
    encoding="unicode", returns str.
    """
    buf = _io.StringIO()
    _serialize(element, buf)
    text = buf.getvalue()
    if encoding is None:
        return text.encode("us-ascii", errors="xmlcharrefreplace")
    if encoding == "unicode":
        return text
    return text.encode(encoding, errors="xmlcharrefreplace")


# ---------------------------------------------------------------------------
# Convenience builders
# ---------------------------------------------------------------------------

def SubElement(parent, tag, attrib=None, **extra):
    el = Element(tag, attrib, **extra)
    parent.append(el)
    return el


# ---------------------------------------------------------------------------
# Invariant probes
# ---------------------------------------------------------------------------

_SAMPLE_XML = "<root><child>hello</child><child>world</child></root>"


def xml_etree2_fromstring():
    """Parse a sample document and return the root tag."""
    root = fromstring(_SAMPLE_XML)
    return root.tag


def xml_etree2_tostring():
    """Round-trip a sample document; return True if serialization works."""
    root = fromstring(_SAMPLE_XML)
    data = tostring(root)
    if not isinstance(data, (bytes, bytearray)):
        return False
    decoded = bytes(data).decode("us-ascii")
    return "<root>" in decoded and "</root>" in decoded and "child" in decoded


def xml_etree2_find():
    """Locate the first <child> descendant and return its tag."""
    root = fromstring(_SAMPLE_XML)
    found = root.find("child")
    if found is None:
        return None
    return found.tag


__all__ = [
    "Element",
    "ElementTree",
    "ParseError",
    "SubElement",
    "fromstring",
    "parse",
    "tostring",
    "xml_etree2_find",
    "xml_etree2_fromstring",
    "xml_etree2_tostring",
]