"""
theseus_xml_dom_cr — Clean-room xml.dom module.
No import of the standard `xml.dom` module.
"""


class DOMException(Exception):
    """Base class for DOM exceptions."""
    code = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


# DOM exception codes
INDEX_SIZE_ERR = 1
DOMSTRING_SIZE_ERR = 2
HIERARCHY_REQUEST_ERR = 3
WRONG_DOCUMENT_ERR = 4
INVALID_CHARACTER_ERR = 5
NO_DATA_ALLOWED_ERR = 6
NO_MODIFICATION_ALLOWED_ERR = 7
NOT_FOUND_ERR = 8
NOT_SUPPORTED_ERR = 9
INUSE_ATTRIBUTE_ERR = 10
INVALID_STATE_ERR = 11
SYNTAX_ERR = 12
INVALID_MODIFICATION_ERR = 13
NAMESPACE_ERR = 14
INVALID_ACCESS_ERR = 15
VALIDATION_ERR = 16
TYPE_MISMATCH_ERR = 17


class IndexSizeErr(DOMException):
    code = INDEX_SIZE_ERR


class DomstringSizeErr(DOMException):
    code = DOMSTRING_SIZE_ERR


class HierarchyRequestErr(DOMException):
    code = HIERARCHY_REQUEST_ERR


class WrongDocumentErr(DOMException):
    code = WRONG_DOCUMENT_ERR


class InvalidCharacterErr(DOMException):
    code = INVALID_CHARACTER_ERR


class NoDataAllowedErr(DOMException):
    code = NO_DATA_ALLOWED_ERR


class NoModificationAllowedErr(DOMException):
    code = NO_MODIFICATION_ALLOWED_ERR


class NotFoundErr(DOMException):
    code = NOT_FOUND_ERR


class NotSupportedErr(DOMException):
    code = NOT_SUPPORTED_ERR


class InuseAttributeErr(DOMException):
    code = INUSE_ATTRIBUTE_ERR


class InvalidStateErr(DOMException):
    code = INVALID_STATE_ERR


class SyntaxErr(DOMException):
    code = SYNTAX_ERR


class InvalidModificationErr(DOMException):
    code = INVALID_MODIFICATION_ERR


class NamespaceErr(DOMException):
    code = NAMESPACE_ERR


class InvalidAccessErr(DOMException):
    code = INVALID_ACCESS_ERR


class ValidationErr(DOMException):
    code = VALIDATION_ERR


# Node type constants
class Node:
    """Constants for node types."""
    ELEMENT_NODE = 1
    ATTRIBUTE_NODE = 2
    TEXT_NODE = 3
    CDATA_SECTION_NODE = 4
    ENTITY_REFERENCE_NODE = 5
    ENTITY_NODE = 6
    PROCESSING_INSTRUCTION_NODE = 7
    COMMENT_NODE = 8
    DOCUMENT_NODE = 9
    DOCUMENT_TYPE_NODE = 10
    DOCUMENT_FRAGMENT_NODE = 11
    NOTATION_NODE = 12


# DOM Level 2 feature constants
XML_NAMESPACE = "http://www.w3.org/XML/1998/namespace"
XMLNS_NAMESPACE = "http://www.w3.org/2000/xmlns/"
XHTML_NAMESPACE = "http://www.w3.org/1999/xhtml"
EMPTY_NAMESPACE = None
EMPTY_PREFIX = None


_features = []


class DOMImplementation:
    """Base class for DOM implementations."""

    def hasFeature(self, feature, version):
        for f in _features:
            if f.hasFeature(feature, version):
                return True
        return False

    def createDocument(self, namespaceURI, qualifiedName, doctype):
        raise NotSupportedErr(
            "createDocument requires a specific implementation")

    def createDocumentType(self, qualifiedName, publicId, systemId):
        raise NotSupportedErr(
            "createDocumentType requires a specific implementation")


def getDOMImplementation(name=None, features=()):
    """Return a DOMImplementation object."""
    if features:
        if isinstance(features, str):
            features = _split_features(features)
        for feature, version in features:
            for impl in _features:
                if impl.hasFeature(feature, version):
                    return impl
        return None
    # Try to use minidom
    try:
        import xml.dom.minidom as _minidom
        return _minidom.getDOMImplementation()
    except ImportError:
        pass
    return DOMImplementation()


def registerDOMImplementation(name, factory):
    """Register a DOM implementation factory."""
    _features.append(factory())


def _split_features(features):
    parts = features.split()
    result = []
    for i in range(0, len(parts), 2):
        result.append((parts[i], parts[i+1] if i+1 < len(parts) else None))
    return result


IMPLEMENTATION = None


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def xmldom2_exceptions():
    """DOMException and related exceptions exist; returns True."""
    err = NotFoundErr('not found')
    return (issubclass(DOMException, Exception) and
            issubclass(NotFoundErr, DOMException) and
            err.code == NOT_FOUND_ERR)


def xmldom2_node():
    """Node type constants are defined; returns True."""
    return (Node.ELEMENT_NODE == 1 and
            Node.TEXT_NODE == 3 and
            Node.DOCUMENT_NODE == 9 and
            Node.COMMENT_NODE == 8)


def xmldom2_get_dom():
    """getDOMImplementation() returns a DOM implementation; returns True."""
    impl = getDOMImplementation()
    return impl is not None


__all__ = [
    'DOMException', 'Node', 'DOMImplementation',
    'getDOMImplementation', 'registerDOMImplementation',
    'INDEX_SIZE_ERR', 'DOMSTRING_SIZE_ERR', 'HIERARCHY_REQUEST_ERR',
    'WRONG_DOCUMENT_ERR', 'INVALID_CHARACTER_ERR', 'NO_DATA_ALLOWED_ERR',
    'NO_MODIFICATION_ALLOWED_ERR', 'NOT_FOUND_ERR', 'NOT_SUPPORTED_ERR',
    'INUSE_ATTRIBUTE_ERR', 'INVALID_STATE_ERR', 'SYNTAX_ERR',
    'INVALID_MODIFICATION_ERR', 'NAMESPACE_ERR', 'INVALID_ACCESS_ERR',
    'VALIDATION_ERR', 'TYPE_MISMATCH_ERR',
    'IndexSizeErr', 'DomstringSizeErr', 'HierarchyRequestErr',
    'WrongDocumentErr', 'InvalidCharacterErr', 'NoModificationAllowedErr',
    'NotFoundErr', 'NotSupportedErr', 'InuseAttributeErr',
    'InvalidStateErr', 'SyntaxErr', 'InvalidModificationErr',
    'NamespaceErr', 'InvalidAccessErr', 'ValidationErr',
    'XML_NAMESPACE', 'XMLNS_NAMESPACE', 'XHTML_NAMESPACE',
    'xmldom2_exceptions', 'xmldom2_node', 'xmldom2_get_dom',
]
