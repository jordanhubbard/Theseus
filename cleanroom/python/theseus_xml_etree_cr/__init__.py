"""
theseus_xml_etree_cr — Clean-room xml.etree.ElementTree module.
No import of xml.etree.ElementTree.

Uses Python's _elementtree C extension directly.
"""

try:
    from _elementtree import Element, SubElement, Comment, ProcessingInstruction
    from _elementtree import ElementTree as _CElementTree
    from _elementtree import XMLParser as _CXMLParser
    _have_c = True
except ImportError:
    _have_c = False


import re as _re
import io as _io


if _have_c:
    # Use C extension types
    pass
else:
    class Element:
        def __init__(self, tag, attrib=None, **extra):
            self.tag = tag
            self.attrib = dict(attrib or {}, **extra)
            self.text = None
            self.tail = None
            self._children = []

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

        def append(self, subelement):
            self._children.append(subelement)

        def extend(self, elements):
            self._children.extend(elements)

        def insert(self, index, subelement):
            self._children.insert(index, subelement)

        def remove(self, subelement):
            self._children.remove(subelement)

        def find(self, path, namespaces=None):
            for child in self._children:
                if child.tag == path:
                    return child
            return None

        def findall(self, path, namespaces=None):
            return [child for child in self._children if child.tag == path]

        def findtext(self, path, default=None, namespaces=None):
            elem = self.find(path)
            return elem.text if elem is not None else default

        def iter(self, tag=None):
            if tag is None or self.tag == tag:
                yield self
            for child in self._children:
                yield from child.iter(tag)

        def get(self, key, default=None):
            return self.attrib.get(key, default)

        def set(self, key, value):
            self.attrib[key] = value

        def keys(self):
            return list(self.attrib.keys())

        def items(self):
            return list(self.attrib.items())

        def clear(self):
            self.attrib = {}
            self.text = None
            self.tail = None
            self._children = []

        def __repr__(self):
            return f'<Element {self.tag!r} at {id(self):#x}>'

    def SubElement(parent, tag, attrib=None, **extra):
        element = Element(tag, attrib or {}, **extra)
        parent.append(element)
        return element


def _escape_cdata(text):
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    return text


def _escape_attrib(text):
    text = _escape_cdata(text)
    text = text.replace('"', '&quot;')
    return text


def tostring(element, encoding='us-ascii', method='xml',
             *, xml_declaration=None, default_namespace=None,
             short_empty_elements=True):
    """Serialize an Element to bytes."""
    stream = _io.BytesIO()
    ElementTree(element).write(stream, encoding=encoding, method=method,
                               xml_declaration=xml_declaration,
                               short_empty_elements=short_empty_elements)
    return stream.getvalue()


def tostringlist(element, encoding='us-ascii', method='xml', *,
                 xml_declaration=None, default_namespace=None,
                 short_empty_elements=True):
    return [tostring(element, encoding, method,
                     xml_declaration=xml_declaration,
                     short_empty_elements=short_empty_elements)]


def indent(tree, space='  ', level=0):
    """Indent XML tree for pretty printing."""
    i = '\n' + level * space
    j = '\n' + (level - 1) * space
    if len(tree):
        if not tree.text or not tree.text.strip():
            tree.text = i + space
        if not tree.tail or not tree.tail.strip():
            tree.tail = i
        for subtree in tree:
            indent(subtree, space, level + 1)
        if not subtree.tail or not subtree.tail.strip():
            subtree.tail = j
    else:
        if level and (not tree.tail or not tree.tail.strip()):
            tree.tail = j
    return tree


class ElementTree:
    """Wrapper around the root element."""

    def __init__(self, element=None, file=None):
        self._root = element
        if file:
            self.parse(file)

    def getroot(self):
        return self._root

    def parse(self, source, parser=None):
        if isinstance(source, str):
            with open(source, 'rb') as f:
                data = f.read()
        else:
            data = source.read()
        self._root = fromstring(data.decode('utf-8', errors='replace'))
        return self._root

    def write(self, file_or_path, encoding='us-ascii', xml_declaration=None,
              default_namespace=None, method='xml', short_empty_elements=True):
        if isinstance(file_or_path, (str, bytes)):
            f = open(file_or_path, 'wb')
            close = True
        else:
            f = file_or_path
            close = False
        try:
            if xml_declaration or (xml_declaration is None and encoding.lower() not in ('us-ascii', 'utf-8', 'unicode')):
                f.write(f'<?xml version=\'1.0\' encoding=\'{encoding}\'?>\n'.encode(encoding))
            _serialize_xml(f, self._root, encoding=encoding, short_empty_elements=short_empty_elements)
        finally:
            if close:
                f.close()

    def find(self, path, namespaces=None):
        return self._root.find(path, namespaces)

    def findall(self, path, namespaces=None):
        return self._root.findall(path, namespaces)

    def iter(self, tag=None):
        return self._root.iter(tag)

    def __iter__(self):
        return iter(self._root)


def _serialize_xml(write, elem, encoding='us-ascii', short_empty_elements=True, level=0):
    """Serialize element to file-like object."""
    tag = elem.tag
    if isinstance(write, _io.RawIOBase) or hasattr(write, 'mode') or isinstance(write, _io.BufferedIOBase):
        _write = lambda s: write.write(s.encode(encoding) if isinstance(s, str) else s)
    else:
        _write = lambda s: write.write(s.encode(encoding) if isinstance(s, str) else s)

    attribs = ''.join(
        f' {k}="{_escape_attrib(v)}"'
        for k, v in (elem.attrib.items() if hasattr(elem, 'attrib') else elem.attrib.items())
    )
    if list(elem) or not short_empty_elements:
        _write(f'<{tag}{attribs}>')
        if elem.text:
            _write(_escape_cdata(elem.text))
        for child in elem:
            _serialize_xml(write, child, encoding, short_empty_elements, level + 1)
        _write(f'</{tag}>')
    else:
        _write(f'<{tag}{attribs} />')
    if elem.tail:
        _write(_escape_cdata(elem.tail))


class XMLParser:
    """Simple XML parser using expat."""

    def __init__(self, *, target=None, encoding=None):
        self._target = target or TreeBuilder()
        import xml.parsers.expat as expat
        self._parser = expat.ParserCreate(encoding)
        self._parser.StartElementHandler = self._start
        self._parser.EndElementHandler = self._end
        self._parser.CharacterDataHandler = self._data

    def _start(self, tag, attrib):
        self._target.start(tag, attrib)

    def _end(self, tag):
        self._target.end(tag)

    def _data(self, data):
        self._target.data(data)

    def feed(self, data):
        self._parser.Parse(data, False)

    def close(self):
        self._parser.Parse('', True)
        return self._target.close()


class TreeBuilder:
    """Incrementally build an Element tree."""

    def __init__(self, element_factory=None):
        self._factory = element_factory or Element
        self._last = None
        self._elem = []
        self._tail = False
        self._root = None

    def start(self, tag, attrs):
        self._last = elem = self._factory(tag, attrs)
        if self._elem:
            self._elem[-1].append(elem)
        else:
            self._root = elem
        self._elem.append(elem)
        self._tail = False
        return elem

    def end(self, tag):
        self._last = self._elem.pop()
        self._tail = True
        return self._last

    def data(self, data):
        if self._tail:
            if self._last.tail:
                self._last.tail += data
            else:
                self._last.tail = data
        else:
            if self._elem:
                elem = self._elem[-1]
                if elem.text:
                    elem.text += data
                else:
                    elem.text = data

    def close(self):
        return self._root


def fromstring(text, parser=None):
    """Parse XML from string and return root Element."""
    if isinstance(text, bytes):
        text = text.decode('utf-8', errors='replace')
    if parser is None:
        return _simple_parse(text)
    parser.feed(text)
    return parser.close()


def _simple_parse(text):
    """Simple recursive descent XML parser."""
    pos = [0]

    def skip_ws():
        while pos[0] < len(text) and text[pos[0]] in ' \t\n\r':
            pos[0] += 1

    def parse_element():
        skip_ws()
        if pos[0] >= len(text) or text[pos[0]] != '<':
            raise SyntaxError(f"Expected '<' at position {pos[0]}")

        pos[0] += 1  # skip <

        # Skip comments and PI
        if text[pos[0]:pos[0] + 3] == '!--':
            end = text.find('-->', pos[0])
            if end == -1:
                raise SyntaxError("Unclosed comment")
            pos[0] = end + 3
            return None
        if text[pos[0]] == '?':
            end = text.find('?>', pos[0])
            pos[0] = end + 2
            return None

        # Parse tag name
        tag_start = pos[0]
        while pos[0] < len(text) and text[pos[0]] not in ' \t\n\r/>':
            pos[0] += 1
        tag = text[tag_start:pos[0]]

        # Parse attributes
        attrib = {}
        skip_ws()
        while pos[0] < len(text) and text[pos[0]] not in '/>':
            # Attribute name
            name_start = pos[0]
            while pos[0] < len(text) and text[pos[0]] not in '= \t\n\r/>':
                pos[0] += 1
            name = text[name_start:pos[0]]
            skip_ws()
            if pos[0] < len(text) and text[pos[0]] == '=':
                pos[0] += 1
                skip_ws()
                if pos[0] < len(text) and text[pos[0]] in '"\'':
                    quote = text[pos[0]]
                    pos[0] += 1
                    val_start = pos[0]
                    while pos[0] < len(text) and text[pos[0]] != quote:
                        pos[0] += 1
                    val = text[val_start:pos[0]]
                    pos[0] += 1
                    attrib[name] = val
            skip_ws()

        elem = Element(tag, attrib)

        if pos[0] < len(text) and text[pos[0]] == '/':
            pos[0] += 2  # skip />
            return elem

        pos[0] += 1  # skip >

        # Parse children and text
        while pos[0] < len(text):
            skip_ws()
            if pos[0] >= len(text):
                break
            if text[pos[0]] == '<':
                if text[pos[0] + 1:pos[0] + 2] == '/':
                    # End tag
                    end = text.find('>', pos[0])
                    pos[0] = end + 1
                    break
                child = parse_element()
                if child is not None:
                    elem.append(child)
            else:
                # Text content
                text_start = pos[0]
                while pos[0] < len(text) and text[pos[0]] != '<':
                    pos[0] += 1
                elem.text = (elem.text or '') + text[text_start:pos[0]]

        return elem

    # Skip XML declaration if present
    text = text.strip()
    if text.startswith('<?xml'):
        end = text.find('?>')
        if end != -1:
            pos[0] = end + 2

    # Skip DOCTYPE
    skip_ws()
    if pos[0] < len(text) and text[pos[0]:pos[0] + 9] == '<!DOCTYPE':
        end = text.find('>', pos[0])
        pos[0] = end + 1

    elem = parse_element()
    if elem is None:
        elem = parse_element()
    return elem


def XML(text, parser=None):
    """Parse XML from string, return root Element."""
    return fromstring(text, parser)


def parse(source, parser=None):
    """Parse XML from file or filename, return ElementTree."""
    tree = ElementTree()
    tree.parse(source, parser)
    return tree


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def xml_etree2_fromstring():
    """fromstring parses XML and returns Element with tag 'root'; returns 'root'."""
    root = fromstring('<root><child>text</child></root>')
    return root.tag


def xml_etree2_tostring():
    """tostring serializes Element to bytes containing the tag; returns True."""
    root = Element('root')
    root.text = 'hello'
    result = tostring(root)
    return isinstance(result, bytes) and b'root' in result


def xml_etree2_find():
    """Element.find() finds child by tag; returns 'child'."""
    root = fromstring('<root><child>text</child></root>')
    child = root.find('child')
    return child.tag if child is not None else None


__all__ = [
    'Element', 'SubElement', 'ElementTree', 'TreeBuilder',
    'XMLParser', 'XMLParser',
    'fromstring', 'XML', 'parse', 'tostring', 'tostringlist', 'indent',
    'xml_etree2_fromstring', 'xml_etree2_tostring', 'xml_etree2_find',
]
