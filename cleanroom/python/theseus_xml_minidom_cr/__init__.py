"""
theseus_xml_minidom_cr — Clean-room xml.dom.minidom module.
No import of xml.dom.minidom. Uses pyexpat C extension directly.
"""

import importlib.util as _importlib_util
import importlib.machinery as _importlib_machinery
import sysconfig as _sysconfig
import os as _os

_stdlib = _sysconfig.get_path('stdlib')
_ext_suffix = _sysconfig.get_config_var('EXT_SUFFIX') or '.cpython-314-darwin.so'
_pyexpat_so = _os.path.join(_stdlib, 'lib-dynload', 'pyexpat' + _ext_suffix)
if not _os.path.exists(_pyexpat_so):
    raise ImportError(f"Cannot find pyexpat C extension at {_pyexpat_so}")

_loader = _importlib_machinery.ExtensionFileLoader('pyexpat', _pyexpat_so)
_spec = _importlib_util.spec_from_file_location('pyexpat', _pyexpat_so, loader=_loader)
_pyexpat = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_pyexpat)


# ---------------------------------------------------------------------------
# Node types
# ---------------------------------------------------------------------------
ELEMENT_NODE = 1
ATTRIBUTE_NODE = 2
TEXT_NODE = 3
CDATA_SECTION_NODE = 4
COMMENT_NODE = 8
DOCUMENT_NODE = 9
DOCUMENT_FRAGMENT_NODE = 11


class DOMException(Exception):
    pass


class Node:
    nodeType = None
    nodeName = None
    nodeValue = None
    parentNode = None
    ownerDocument = None

    def __init__(self):
        self.childNodes = []
        self.attributes = None

    def appendChild(self, child):
        child.parentNode = self
        self.childNodes.append(child)
        return child

    def removeChild(self, child):
        self.childNodes.remove(child)
        child.parentNode = None
        return child

    def getElementsByTagName(self, tagName):
        result = []
        for child in self.childNodes:
            if hasattr(child, 'tagName') and (tagName == '*' or child.tagName == tagName):
                result.append(child)
            result.extend(child.getElementsByTagName(tagName))
        return result

    def hasChildNodes(self):
        return bool(self.childNodes)

    def toxml(self, encoding=None):
        parts = []
        self._toxml(parts)
        s = ''.join(parts)
        if encoding:
            return s.encode(encoding)
        return s

    def toprettyxml(self, indent='\t', newl='\n', encoding=None):
        parts = []
        self._toprettyxml(parts, 0, indent, newl)
        s = ''.join(parts)
        if encoding:
            return s.encode(encoding)
        return s

    def _toxml(self, parts):
        for child in self.childNodes:
            child._toxml(parts)

    def _toprettyxml(self, parts, level, indent, newl):
        for child in self.childNodes:
            child._toprettyxml(parts, level, indent, newl)

    def __bool__(self):
        return True


class Document(Node):
    nodeType = DOCUMENT_NODE
    nodeName = '#document'

    def __init__(self):
        super().__init__()
        self.documentElement = None

    def appendChild(self, child):
        super().appendChild(child)
        if child.nodeType == ELEMENT_NODE:
            self.documentElement = child
        return child

    def createElement(self, tagName):
        el = Element(tagName)
        el.ownerDocument = self
        return el

    def createTextNode(self, data):
        node = Text(data)
        node.ownerDocument = self
        return node

    def createComment(self, data):
        node = Comment(data)
        node.ownerDocument = self
        return node

    def createAttribute(self, name):
        attr = Attr(name)
        attr.ownerDocument = self
        return attr

    def getElementsByTagName(self, tagName):
        result = []
        for child in self.childNodes:
            result.extend(child.getElementsByTagName(tagName) if tagName != child.nodeName else [child])
            if hasattr(child, 'tagName') and (tagName == '*' or child.tagName == tagName):
                result.append(child)
        # Deduplicate but that's complex - just delegate
        if self.documentElement:
            return self.documentElement.getElementsByTagName_all(tagName)
        return []

    def _toxml(self, parts):
        parts.append('<?xml version="1.0" ?>')
        for child in self.childNodes:
            child._toxml(parts)

    def _toprettyxml(self, parts, level, indent, newl):
        parts.append('<?xml version="1.0" ?>' + newl)
        for child in self.childNodes:
            child._toprettyxml(parts, level, indent, newl)


class NamedNodeMap:
    def __init__(self):
        self._attrs = {}

    def __getitem__(self, name):
        return self._attrs[name]

    def __setitem__(self, name, value):
        self._attrs[name] = value

    def __contains__(self, name):
        return name in self._attrs

    def __len__(self):
        return len(self._attrs)

    def get(self, name, default=None):
        return self._attrs.get(name, default)

    def keys(self):
        return self._attrs.keys()

    def values(self):
        return self._attrs.values()

    def items(self):
        return self._attrs.items()


class Attr(Node):
    nodeType = ATTRIBUTE_NODE

    def __init__(self, name, value=''):
        super().__init__()
        self.name = name
        self.nodeName = name
        self.value = value
        self.nodeValue = value

    def _toxml(self, parts):
        v = self.value.replace('&', '&amp;').replace('"', '&quot;')
        parts.append(f' {self.name}="{v}"')


class Element(Node):
    nodeType = ELEMENT_NODE

    def __init__(self, tagName):
        super().__init__()
        self.tagName = tagName
        self.nodeName = tagName
        self.attributes = NamedNodeMap()

    def getAttribute(self, name):
        attr = self.attributes.get(name)
        return attr.value if attr else ''

    def setAttribute(self, name, value):
        attr = Attr(name, str(value))
        self.attributes[name] = attr

    def hasAttribute(self, name):
        return name in self.attributes

    def removeAttribute(self, name):
        if name in self.attributes:
            del self.attributes._attrs[name]

    def getElementsByTagName(self, tagName):
        return self.getElementsByTagName_all(tagName)

    def getElementsByTagName_all(self, tagName):
        result = []
        for child in self.childNodes:
            if hasattr(child, 'tagName') and (tagName == '*' or child.tagName == tagName):
                result.append(child)
            if hasattr(child, 'getElementsByTagName_all'):
                result.extend(child.getElementsByTagName_all(tagName))
        return result

    def _toxml(self, parts):
        parts.append(f'<{self.tagName}')
        for attr in self.attributes.values():
            attr._toxml(parts)
        if self.childNodes:
            parts.append('>')
            for child in self.childNodes:
                child._toxml(parts)
            parts.append(f'</{self.tagName}>')
        else:
            parts.append('/>')

    def _toprettyxml(self, parts, level, indent, newl):
        parts.append(indent * level)
        parts.append(f'<{self.tagName}')
        for attr in self.attributes.values():
            attr._toxml(parts)
        if self.childNodes:
            parts.append('>' + newl)
            for child in self.childNodes:
                child._toprettyxml(parts, level + 1, indent, newl)
            parts.append(indent * level + f'</{self.tagName}>' + newl)
        else:
            parts.append('/>' + newl)


class Text(Node):
    nodeType = TEXT_NODE
    nodeName = '#text'

    def __init__(self, data):
        super().__init__()
        self.data = data
        self.nodeValue = data

    def _toxml(self, parts):
        parts.append(self.data.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))

    def _toprettyxml(self, parts, level, indent, newl):
        parts.append(indent * level + self.data.strip())
        if self.data.strip():
            parts.append(newl)


class Comment(Node):
    nodeType = COMMENT_NODE
    nodeName = '#comment'

    def __init__(self, data):
        super().__init__()
        self.data = data
        self.nodeValue = data

    def _toxml(self, parts):
        parts.append(f'<!--{self.data}-->')

    def _toprettyxml(self, parts, level, indent, newl):
        parts.append(indent * level + f'<!--{self.data}-->' + newl)


def _parse(data):
    """Parse XML data and return a Document node."""
    doc = Document()
    stack = [doc]
    current = doc

    parser = _pyexpat.ParserCreate()

    def start_element(name, attrs):
        nonlocal current
        el = doc.createElement(name)
        for k, v in attrs.items():
            el.setAttribute(k, v)
        current.appendChild(el)
        stack.append(el)
        current = el

    def end_element(name):
        nonlocal current
        stack.pop()
        current = stack[-1] if stack else doc

    def char_data(data):
        if data.strip():
            text = doc.createTextNode(data)
            current.appendChild(text)

    parser.StartElementHandler = start_element
    parser.EndElementHandler = end_element
    parser.CharacterDataHandler = char_data

    if isinstance(data, str):
        data = data.encode('utf-8')
    parser.Parse(data, True)
    return doc


def parseString(string, parser=None):
    """Parse an XML string and return a Document."""
    if isinstance(string, str):
        string = string.encode('utf-8')
    return _parse(string)


def parse(file, parser=None):
    """Parse an XML file and return a Document."""
    if isinstance(file, str):
        with open(file, 'rb') as f:
            return _parse(f.read())
    return _parse(file.read())


def getDOMImplementation(features=None):
    return _DOMImplementation()


class _DOMImplementation:
    def createDocument(self, namespaceURI, qualifiedName, doctype):
        doc = Document()
        if qualifiedName:
            root = doc.createElement(qualifiedName)
            doc.appendChild(root)
        return doc

    def hasFeature(self, feature, version):
        return True


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def minidom2_parse():
    """parseString() returns a Document node; returns True."""
    doc = parseString('<root><child/></root>')
    return isinstance(doc, Document) and doc.nodeType == DOCUMENT_NODE


def minidom2_elements():
    """getElementsByTagName() returns elements; returns True."""
    doc = parseString('<root><a>1</a><b>2</b><a>3</a></root>')
    root = doc.documentElement
    elements = root.getElementsByTagName('a')
    return len(elements) == 2 and elements[0].tagName == 'a'


def minidom2_toprettyxml():
    """toprettyxml() returns a string; returns True."""
    doc = parseString('<root><child/></root>')
    xml = doc.toprettyxml()
    return isinstance(xml, str) and 'root' in xml and 'child' in xml


__all__ = [
    'Document', 'Element', 'Text', 'Comment', 'Attr', 'Node',
    'NamedNodeMap', 'DOMException',
    'ELEMENT_NODE', 'ATTRIBUTE_NODE', 'TEXT_NODE', 'CDATA_SECTION_NODE',
    'COMMENT_NODE', 'DOCUMENT_NODE', 'DOCUMENT_FRAGMENT_NODE',
    'parseString', 'parse', 'getDOMImplementation',
    'minidom2_parse', 'minidom2_elements', 'minidom2_toprettyxml',
]
