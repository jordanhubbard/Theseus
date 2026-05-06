"""Clean-room re-implementation of a minidom-like XML DOM.

Implements parsing of a useful subset of XML into a node tree
(Document, Element, Text, Comment, Attr) and a pretty-printing
serializer. No xml.dom.minidom (or any third-party) imports.
"""

# ---------------------------------------------------------------------------
# Node type constants (mirroring DOM Level 2)
# ---------------------------------------------------------------------------
ELEMENT_NODE = 1
ATTRIBUTE_NODE = 2
TEXT_NODE = 3
CDATA_SECTION_NODE = 4
COMMENT_NODE = 8
DOCUMENT_NODE = 9


# ---------------------------------------------------------------------------
# Escaping helpers
# ---------------------------------------------------------------------------
def _escape_text(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _escape_attr(s):
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    s = s.replace('"', "&quot;").replace("\n", "&#10;").replace("\r", "&#13;")
    s = s.replace("\t", "&#9;")
    return s


def _unescape(s):
    # Simple entity decoding for the parser
    out = []
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c == "&":
            j = s.find(";", i)
            if j == -1:
                out.append(c)
                i += 1
                continue
            ent = s[i + 1:j]
            if ent == "amp":
                out.append("&")
            elif ent == "lt":
                out.append("<")
            elif ent == "gt":
                out.append(">")
            elif ent == "quot":
                out.append('"')
            elif ent == "apos":
                out.append("'")
            elif ent.startswith("#x") or ent.startswith("#X"):
                try:
                    out.append(chr(int(ent[2:], 16)))
                except ValueError:
                    out.append(s[i:j + 1])
            elif ent.startswith("#"):
                try:
                    out.append(chr(int(ent[1:])))
                except ValueError:
                    out.append(s[i:j + 1])
            else:
                out.append(s[i:j + 1])
            i = j + 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


# ---------------------------------------------------------------------------
# Node tree
# ---------------------------------------------------------------------------
class Node(object):
    nodeType = 0
    nodeName = ""

    def __init__(self):
        self.parentNode = None
        self.childNodes = []
        self.ownerDocument = None

    @property
    def firstChild(self):
        return self.childNodes[0] if self.childNodes else None

    @property
    def lastChild(self):
        return self.childNodes[-1] if self.childNodes else None

    def appendChild(self, child):
        if child.parentNode is not None:
            try:
                child.parentNode.childNodes.remove(child)
            except ValueError:
                pass
        child.parentNode = self
        self.childNodes.append(child)
        return child

    def hasChildNodes(self):
        return bool(self.childNodes)

    def toxml(self, encoding=None):
        return _serialize(self, indent="", newl="", addindent="")

    def toprettyxml(self, indent="\t", newl="\n", encoding=None):
        return _serialize(self, indent="", newl=newl, addindent=indent)


class Text(Node):
    nodeType = TEXT_NODE
    nodeName = "#text"

    def __init__(self, data=""):
        Node.__init__(self)
        self.data = data

    @property
    def nodeValue(self):
        return self.data


class Comment(Node):
    nodeType = COMMENT_NODE
    nodeName = "#comment"

    def __init__(self, data=""):
        Node.__init__(self)
        self.data = data

    @property
    def nodeValue(self):
        return self.data


class Attr(object):
    nodeType = ATTRIBUTE_NODE

    def __init__(self, name, value=""):
        self.name = name
        self.value = value
        self.nodeName = name
        self.nodeValue = value


class _AttrMap(object):
    """Lightweight NamedNodeMap-ish container for attributes."""

    def __init__(self):
        self._items = {}  # name -> Attr
        self._order = []

    def __len__(self):
        return len(self._order)

    def __contains__(self, name):
        return name in self._items

    def __iter__(self):
        return iter(self._order)

    def keys(self):
        return list(self._order)

    def items(self):
        return [(k, self._items[k].value) for k in self._order]

    def get(self, name, default=None):
        a = self._items.get(name)
        return a.value if a is not None else default

    def setNamedItem(self, attr):
        if attr.name not in self._items:
            self._order.append(attr.name)
        self._items[attr.name] = attr

    def getNamedItem(self, name):
        return self._items.get(name)


class Element(Node):
    nodeType = ELEMENT_NODE

    def __init__(self, tagName):
        Node.__init__(self)
        self.tagName = tagName
        self.nodeName = tagName
        self.attributes = _AttrMap()

    def setAttribute(self, name, value):
        self.attributes.setNamedItem(Attr(name, value))

    def getAttribute(self, name):
        return self.attributes.get(name, "")

    def hasAttribute(self, name):
        return name in self.attributes

    def getElementsByTagName(self, name):
        out = []
        for c in self.childNodes:
            if c.nodeType == ELEMENT_NODE:
                if name == "*" or c.tagName == name:
                    out.append(c)
                out.extend(c.getElementsByTagName(name))
        return out


class Document(Node):
    nodeType = DOCUMENT_NODE
    nodeName = "#document"

    def __init__(self):
        Node.__init__(self)
        self.ownerDocument = self

    @property
    def documentElement(self):
        for c in self.childNodes:
            if c.nodeType == ELEMENT_NODE:
                return c
        return None

    def createElement(self, tagName):
        el = Element(tagName)
        el.ownerDocument = self
        return el

    def createTextNode(self, data):
        t = Text(data)
        t.ownerDocument = self
        return t

    def createComment(self, data):
        c = Comment(data)
        c.ownerDocument = self
        return c

    def getElementsByTagName(self, name):
        root = self.documentElement
        if root is None:
            return []
        result = []
        if name == "*" or root.tagName == name:
            result.append(root)
        result.extend(root.getElementsByTagName(name))
        return result


# ---------------------------------------------------------------------------
# Serializer
# ---------------------------------------------------------------------------
def _serialize(node, indent, newl, addindent):
    parts = []
    _write_node(node, parts, indent, newl, addindent)
    return "".join(parts)


def _write_node(node, parts, indent, newl, addindent):
    if node.nodeType == DOCUMENT_NODE:
        if newl:
            parts.append('<?xml version="1.0" ?>' + newl)
        else:
            parts.append('<?xml version="1.0" ?>')
        for child in node.childNodes:
            _write_node(child, parts, indent, newl, addindent)
        return

    if node.nodeType == TEXT_NODE:
        text = node.data
        if not text:
            return
        if addindent or newl:
            stripped = text.strip()
            if not stripped:
                return
            parts.append(indent + _escape_text(stripped) + newl)
        else:
            parts.append(_escape_text(text))
        return

    if node.nodeType == COMMENT_NODE:
        parts.append(indent + "<!--" + node.data + "-->" + newl)
        return

    if node.nodeType == ELEMENT_NODE:
        parts.append(indent + "<" + node.tagName)
        for name in node.attributes.keys():
            value = node.attributes.get(name, "")
            parts.append(' %s="%s"' % (name, _escape_attr(value)))
        if not node.childNodes:
            parts.append("/>" + newl)
            return

        # Detect "simple text content" — single text child without
        # whitespace-only data — render inline so output is readable.
        if (len(node.childNodes) == 1
                and node.childNodes[0].nodeType == TEXT_NODE):
            txt = node.childNodes[0].data
            parts.append(">")
            parts.append(_escape_text(txt))
            parts.append("</" + node.tagName + ">" + newl)
            return

        parts.append(">" + newl)
        child_indent = indent + addindent
        for child in node.childNodes:
            _write_node(child, parts, child_indent, newl, addindent)
        parts.append(indent + "</" + node.tagName + ">" + newl)
        return


# ---------------------------------------------------------------------------
# Parser — small recursive-descent XML reader
# ---------------------------------------------------------------------------
class _ParseError(Exception):
    pass


class _Parser(object):
    def __init__(self, text):
        self.s = text
        self.i = 0
        self.n = len(text)

    def parse(self):
        doc = Document()
        self._skip_prolog()
        while self.i < self.n:
            self._skip_ws()
            if self.i >= self.n:
                break
            if self.s.startswith("<!--", self.i):
                doc.appendChild(self._parse_comment())
            elif self.s.startswith("<?", self.i):
                self._skip_pi()
            elif self.s.startswith("<!", self.i):
                self._skip_doctype()
            elif self.s[self.i] == "<":
                doc.appendChild(self._parse_element())
            else:
                # Stray text at document root — skip
                self.i += 1
        return doc

    def _skip_ws(self):
        while self.i < self.n and self.s[self.i] in " \t\r\n":
            self.i += 1

    def _skip_prolog(self):
        self._skip_ws()
        while self.i < self.n:
            self._skip_ws()
            if self.s.startswith("<?", self.i):
                self._skip_pi()
            elif self.s.startswith("<!--", self.i):
                # discard comments before root for simplicity
                self._parse_comment()
            elif self.s.startswith("<!", self.i):
                self._skip_doctype()
            else:
                break

    def _skip_pi(self):
        end = self.s.find("?>", self.i)
        if end == -1:
            raise _ParseError("Unterminated processing instruction")
        self.i = end + 2

    def _skip_doctype(self):
        # Naive: read until matching '>' (does not handle internal subset
        # with brackets perfectly, but adequate for the spec)
        depth = 0
        while self.i < self.n:
            c = self.s[self.i]
            if c == "[":
                depth += 1
            elif c == "]":
                depth -= 1
            elif c == ">" and depth <= 0:
                self.i += 1
                return
            self.i += 1

    def _parse_comment(self):
        # self.s[self.i:self.i+4] == '<!--'
        end = self.s.find("-->", self.i + 4)
        if end == -1:
            raise _ParseError("Unterminated comment")
        data = self.s[self.i + 4:end]
        self.i = end + 3
        return Comment(data)

    def _parse_name(self):
        start = self.i
        while self.i < self.n:
            c = self.s[self.i]
            if c.isalnum() or c in "_-:.":
                self.i += 1
            else:
                break
        if self.i == start:
            raise _ParseError("Expected name at %d" % self.i)
        return self.s[start:self.i]

    def _parse_attr_value(self):
        if self.i >= self.n or self.s[self.i] not in "\"'":
            raise _ParseError("Expected quote for attribute value")
        quote = self.s[self.i]
        self.i += 1
        start = self.i
        end = self.s.find(quote, self.i)
        if end == -1:
            raise _ParseError("Unterminated attribute value")
        raw = self.s[start:end]
        self.i = end + 1
        return _unescape(raw)

    def _parse_element(self):
        # consume '<'
        if self.s[self.i] != "<":
            raise _ParseError("Expected '<'")
        self.i += 1
        tag = self._parse_name()
        el = Element(tag)

        while True:
            self._skip_ws()
            if self.i >= self.n:
                raise _ParseError("Unexpected EOF in start tag")
            c = self.s[self.i]
            if c == "/":
                # self-closing
                if self.i + 1 < self.n and self.s[self.i + 1] == ">":
                    self.i += 2
                    return el
                raise _ParseError("Bad self-closing tag")
            if c == ">":
                self.i += 1
                break
            # attribute
            name = self._parse_name()
            self._skip_ws()
            if self.i < self.n and self.s[self.i] == "=":
                self.i += 1
                self._skip_ws()
                value = self._parse_attr_value()
            else:
                value = ""
            el.setAttribute(name, value)

        # Parse children until matching close tag
        while self.i < self.n:
            if self.s.startswith("</", self.i):
                self.i += 2
                close_name = self._parse_name()
                self._skip_ws()
                if self.i >= self.n or self.s[self.i] != ">":
                    raise _ParseError("Expected '>' in close tag")
                self.i += 1
                if close_name != tag:
                    raise _ParseError(
                        "Mismatched close tag: %r vs %r" % (close_name, tag))
                return el
            if self.s.startswith("<!--", self.i):
                el.appendChild(self._parse_comment())
                continue
            if self.s.startswith("<![CDATA[", self.i):
                end = self.s.find("]]>", self.i + 9)
                if end == -1:
                    raise _ParseError("Unterminated CDATA")
                el.appendChild(Text(self.s[self.i + 9:end]))
                self.i = end + 3
                continue
            if self.s.startswith("<?", self.i):
                self._skip_pi()
                continue
            if self.s[self.i] == "<":
                el.appendChild(self._parse_element())
                continue
            # Text content
            start = self.i
            while self.i < self.n and self.s[self.i] != "<":
                self.i += 1
            raw = self.s[start:self.i]
            if raw:
                el.appendChild(Text(_unescape(raw)))

        raise _ParseError("EOF before close of <%s>" % tag)


def parseString(text):
    if isinstance(text, bytes):
        text = text.decode("utf-8")
    return _Parser(text).parse()


def parse(source):
    if hasattr(source, "read"):
        data = source.read()
    elif isinstance(source, str):
        with open(source, "rb") as f:
            data = f.read()
    else:
        data = source
    if isinstance(data, bytes):
        data = data.decode("utf-8")
    return parseString(data)


# ---------------------------------------------------------------------------
# Invariant test functions — return True iff the round-trip behaves correctly
# ---------------------------------------------------------------------------
def minidom2_parse():
    """Parsing produces a Document with the right root element + attributes."""
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<library name="Central">'
        '  <book id="b1" lang="en">'
        '    <title>Hamlet</title>'
        '    <author>Shakespeare</author>'
        '  </book>'
        '  <book id="b2" lang="fr">'
        '    <title>Les Mis&#233;rables</title>'
        '    <author>Hugo</author>'
        '  </book>'
        '  <!-- end of catalog -->'
        '</library>'
    )
    doc = parseString(xml)
    if doc.nodeType != DOCUMENT_NODE:
        return False
    root = doc.documentElement
    if root is None or root.tagName != "library":
        return False
    if root.getAttribute("name") != "Central":
        return False
    if not root.hasAttribute("name") or root.hasAttribute("missing"):
        return False
    if root.getAttribute("missing") != "":
        return False
    # Round-trip a self-closing element
    doc2 = parseString("<a><b/><c x='1'/></a>")
    if doc2.documentElement.tagName != "a":
        return False
    kids = [c for c in doc2.documentElement.childNodes
            if c.nodeType == ELEMENT_NODE]
    if len(kids) != 2 or kids[0].tagName != "b" or kids[1].tagName != "c":
        return False
    if kids[1].getAttribute("x") != "1":
        return False
    return True


def minidom2_elements():
    """getElementsByTagName + child traversal work on a parsed tree."""
    xml = (
        "<root>"
        "<group><item id='1'>one</item><item id='2'>two</item></group>"
        "<group><item id='3'>three</item></group>"
        "</root>"
    )
    doc = parseString(xml)
    items = doc.getElementsByTagName("item")
    if len(items) != 3:
        return False
    ids = [it.getAttribute("id") for it in items]
    if ids != ["1", "2", "3"]:
        return False
    texts = []
    for it in items:
        if it.firstChild is None or it.firstChild.nodeType != TEXT_NODE:
            return False
        texts.append(it.firstChild.data)
    if texts != ["one", "two", "three"]:
        return False
    groups = doc.getElementsByTagName("group")
    if len(groups) != 2:
        return False
    # First group should contain exactly two <item> children
    first_group_items = groups[0].getElementsByTagName("item")
    if len(first_group_items) != 2:
        return False
    # Wildcard
    star = doc.getElementsByTagName("*")
    # root + 2 groups + 3 items = 6
    if len(star) != 6:
        return False
    # Build a tiny tree programmatically and verify
    d = Document()
    e = d.createElement("a")
    e.setAttribute("k", "v")
    d.appendChild(e)
    e.appendChild(d.createTextNode("hi"))
    if d.documentElement.tagName != "a":
        return False
    if d.documentElement.getAttribute("k") != "v":
        return False
    if d.documentElement.firstChild.data != "hi":
        return False
    return True


def minidom2_toprettyxml():
    """toprettyxml produces a well-formed indented serialization."""
    d = Document()
    root = d.createElement("root")
    d.appendChild(root)
    a = d.createElement("a")
    a.setAttribute("x", "1")
    a.appendChild(d.createTextNode("hello"))
    root.appendChild(a)
    b = d.createElement("b")
    root.appendChild(b)
    c = d.createElement("c")
    c.setAttribute("name", "q&r")
    b.appendChild(c)

    pretty = d.toprettyxml(indent="  ")
    # Must declare XML
    if not pretty.startswith('<?xml'):
        return False
    # Required structural pieces
    required = [
        "<root>",
        "<a x=\"1\">hello</a>",
        "<b>",
        "<c name=\"q&amp;r\"/>",
        "</b>",
        "</root>",
    ]
    for piece in required:
        if piece not in pretty:
            return False
    # Indentation: <a> should be indented under <root>
    if "  <a " not in pretty:
        return False
    # <c> should be indented two levels under <root>
    if "    <c " not in pretty:
        return False
    # Round-trip the serialized form back through the parser
    doc2 = parseString(pretty)
    if doc2.documentElement.tagName != "root":
        return False
    a2 = doc2.getElementsByTagName("a")
    if len(a2) != 1 or a2[0].getAttribute("x") != "1":
        return False
    if a2[0].firstChild.data != "hello":
        return False
    c2 = doc2.getElementsByTagName("c")
    if len(c2) != 1 or c2[0].getAttribute("name") != "q&r":
        return False
    # toxml produces compact output without indentation
    compact = d.toxml()
    if "\n" in compact:
        return False
    if "<a x=\"1\">hello</a>" not in compact:
        return False
    return True