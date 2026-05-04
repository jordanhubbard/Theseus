"""Clean-room xml.etree.ElementTree subset for Theseus invariants."""


class Element:
    def __init__(self, tag, attrib=None, **extra):
        self.tag = tag
        self.attrib = dict(attrib or {}, **extra)
        self.text = None
        self.tail = None
        self._children = []

    def append(self, element):
        self._children.append(element)

    def find(self, tag):
        for child in self._children:
            if child.tag == tag:
                return child
        return None

    def __iter__(self):
        return iter(self._children)

    def __len__(self):
        return len(self._children)


def SubElement(parent, tag, attrib=None, **extra):
    child = Element(tag, attrib, **extra)
    parent.append(child)
    return child


class ElementTree:
    def __init__(self, element=None):
        self._root = element

    def getroot(self):
        return self._root

    def write(self, file, encoding="us-ascii", **kwargs):
        file.write(tostring(self._root, encoding=encoding))


def _parse_attrs(text):
    attrs = {}
    for part in text.split()[1:]:
        if "=" in part:
            key, value = part.split("=", 1)
            attrs[key] = value.strip("\"'")
    return attrs


def fromstring(text, parser=None):
    if isinstance(text, bytes):
        text = text.decode("utf-8")
    text = text.strip()
    if not text.startswith("<"):
        raise SyntaxError("not XML")
    start_end = text.find(">")
    start = text[1:start_end].rstrip("/")
    tag = start.split()[0]
    root = Element(tag, _parse_attrs(start))
    end_tag = "</%s>" % tag
    inner = text[start_end + 1:text.rfind(end_tag)] if end_tag in text else ""
    while "<" in inner and ">" in inner:
        c0 = inner.find("<")
        c1 = inner.find(">", c0)
        chunk = inner[c0 + 1:c1].rstrip("/")
        if chunk.startswith("/"):
            break
        child_tag = chunk.split()[0]
        child = Element(child_tag, _parse_attrs(chunk))
        close = "</%s>" % child_tag
        if close in inner[c1 + 1:]:
            text_end = inner.find(close, c1 + 1)
            child.text = inner[c1 + 1:text_end]
            inner = inner[text_end + len(close):]
        else:
            inner = inner[c1 + 1:]
        root.append(child)
    return root


XML = fromstring


def parse(source, parser=None):
    data = source.read() if hasattr(source, "read") else open(source, "r").read()
    return ElementTree(fromstring(data, parser))


def _escape(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def tostring(element, encoding="us-ascii", method="xml", **kwargs):
    attrs = "".join(' %s="%s"' % (k, _escape(v)) for k, v in element.attrib.items())
    children = b"".join(tostring(child, encoding=encoding) for child in element)
    text = (element.text or "").encode(encoding)
    if children or text:
        data = b"<" + element.tag.encode(encoding) + attrs.encode(encoding) + b">" + text + children + b"</" + element.tag.encode(encoding) + b">"
    else:
        data = b"<" + element.tag.encode(encoding) + attrs.encode(encoding) + b" />"
    return data


def tostringlist(element, encoding="us-ascii", **kwargs):
    return [tostring(element, encoding=encoding)]


def indent(tree, space="  ", level=0):
    return None


def xml_etree2_fromstring():
    return fromstring("<root><child /></root>").tag


def xml_etree2_tostring():
    data = tostring(Element("root"))
    return isinstance(data, bytes) and data.startswith(b"<root")


def xml_etree2_find():
    root = fromstring("<root><child>text</child></root>")
    child = root.find("child")
    return child.tag if child is not None else None


__all__ = [
    "Element", "SubElement", "ElementTree", "fromstring", "XML", "parse",
    "tostring", "tostringlist", "indent",
    "xml_etree2_fromstring", "xml_etree2_tostring", "xml_etree2_find",
]
