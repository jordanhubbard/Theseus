"""Clean-room xml.dom subset for Theseus invariants."""

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


class DOMException(Exception):
    code = 0

    def __init__(self, msg=""):
        super().__init__(msg)
        self.code = self.__class__.code


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


class Node:
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


class DOMImplementation:
    def hasFeature(self, feature, version):
        return True


_registered = {}


def getDOMImplementation(name=None, features=()):
    if name and name in _registered:
        return _registered[name]()
    return DOMImplementation()


def registerDOMImplementation(name, factory):
    _registered[name] = factory


def xmldom2_exceptions():
    err = NotFoundErr("not found")
    return issubclass(DOMException, Exception) and issubclass(NotFoundErr, DOMException) and err.code == NOT_FOUND_ERR


def xmldom2_node():
    return Node.ELEMENT_NODE == 1 and Node.TEXT_NODE == 3 and Node.DOCUMENT_NODE == 9 and Node.COMMENT_NODE == 8


def xmldom2_get_dom():
    return getDOMImplementation() is not None


__all__ = [
    "DOMException", "IndexSizeErr", "DomstringSizeErr", "HierarchyRequestErr",
    "WrongDocumentErr", "InvalidCharacterErr", "NoDataAllowedErr",
    "NoModificationAllowedErr", "NotFoundErr", "NotSupportedErr",
    "InuseAttributeErr", "InvalidStateErr", "SyntaxErr",
    "InvalidModificationErr", "NamespaceErr", "InvalidAccessErr",
    "ValidationErr", "Node", "DOMImplementation", "getDOMImplementation",
    "registerDOMImplementation", "xmldom2_exceptions", "xmldom2_node",
    "xmldom2_get_dom",
]
