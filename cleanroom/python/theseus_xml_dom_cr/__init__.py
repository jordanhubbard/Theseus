"""
Clean-room reimplementation of xml.dom.

This module provides DOM Level 2/3 base classes, exception types, and
the DOM implementation registry, without importing or referring to the
original xml.dom package.
"""

# ---------------------------------------------------------------------------
# Exception code constants (DOM Level 3)
# ---------------------------------------------------------------------------

INDEX_SIZE_ERR                 = 1
DOMSTRING_SIZE_ERR             = 2
HIERARCHY_REQUEST_ERR          = 3
WRONG_DOCUMENT_ERR             = 4
INVALID_CHARACTER_ERR          = 5
NO_DATA_ALLOWED_ERR            = 6
NO_MODIFICATION_ALLOWED_ERR    = 7
NOT_FOUND_ERR                  = 8
NOT_SUPPORTED_ERR              = 9
INUSE_ATTRIBUTE_ERR            = 10
INVALID_STATE_ERR              = 11
SYNTAX_ERR                     = 12
INVALID_MODIFICATION_ERR       = 13
NAMESPACE_ERR                  = 14
INVALID_ACCESS_ERR             = 15
VALIDATION_ERR                 = 16


# ---------------------------------------------------------------------------
# DOM exception hierarchy
# ---------------------------------------------------------------------------

class DOMException(Exception):
    """Base class for DOM exceptions, per DOM Level 2 / 3 spec."""
    code = None  # subclasses override

    def __init__(self, *args, **kw):
        if self.__class__ is DOMException:
            raise RuntimeError(
                "DOMException should not be instantiated directly"
            )
        Exception.__init__(self, *args, **kw)

    def _get_code(self):
        return self.code


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


class UserDataHandler(object):
    """Constants for the use of node-data user handlers."""
    NODE_CLONED   = 1
    NODE_IMPORTED = 2
    NODE_DELETED  = 3
    NODE_RENAMED  = 4


# ---------------------------------------------------------------------------
# Node class (constants only — concrete impl lives in minidom-like modules)
# ---------------------------------------------------------------------------

class Node(object):
    """Base class for DOM nodes, holding nodeType constants."""

    ELEMENT_NODE                = 1
    ATTRIBUTE_NODE              = 2
    TEXT_NODE                   = 3
    CDATA_SECTION_NODE          = 4
    ENTITY_REFERENCE_NODE       = 5
    ENTITY_NODE                 = 6
    PROCESSING_INSTRUCTION_NODE = 7
    COMMENT_NODE                = 8
    DOCUMENT_NODE               = 9
    DOCUMENT_TYPE_NODE          = 10
    DOCUMENT_FRAGMENT_NODE      = 11
    NOTATION_NODE               = 12

    namespaceURI = None
    parentNode   = None
    ownerDocument = None
    nextSibling  = None
    previousSibling = None
    prefix       = None

    def __bool__(self):
        # Empty node lists / nodes are still truthy when they exist.
        return True

    __nonzero__ = __bool__  # py2 compat (not relied on, but harmless)


# ---------------------------------------------------------------------------
# Some XML namespace URIs used by DOM Level 2 / 3
# ---------------------------------------------------------------------------

XML_NAMESPACE   = "http://www.w3.org/XML/1998/namespace"
XMLNS_NAMESPACE = "http://www.w3.org/2000/xmlns/"
XHTML_NAMESPACE = "http://www.w3.org/1999/xhtml"
EMPTY_NAMESPACE = None
EMPTY_PREFIX    = None


# ---------------------------------------------------------------------------
# Minimal DOMImplementation registry
# ---------------------------------------------------------------------------

class _EmptyNodeList(tuple):
    """Empty NodeList that returns itself for + and += operations."""
    def __add__(self, other):
        NL = NodeList()
        NL.extend(other)
        return NL

    def __radd__(self, other):
        NL = NodeList()
        NL.extend(other)
        return NL


class NodeList(list):
    """A NodeList supports old-style DOM access via .item(i) and .length."""

    @property
    def length(self):
        return len(self)

    def item(self, index):
        if 0 <= index < len(self):
            return self[index]
        return None


EMPTY_NODE_LIST = _EmptyNodeList()


class _MinimalDOMImplementation(object):
    """Default DOMImplementation returned when no other is registered."""

    _features = {
        ("core", None): None,
        ("core", "1.0"): None,
        ("core", "2.0"): None,
        ("xml",  None): None,
        ("xml",  "1.0"): None,
        ("xml",  "2.0"): None,
    }

    def hasFeature(self, feature, version):
        key = (feature.lower(), version)
        if key in self._features:
            return True
        if (feature.lower(), None) in self._features:
            return True
        return False

    def createDocument(self, namespaceURI, qualifiedName, doctype):
        # The default implementation does not build a real document;
        # downstream code is expected to register a richer impl.
        if doctype is not None and getattr(doctype, "ownerDocument", None) is not None:
            raise WrongDocumentErr("doctype is already in use")
        return _MinimalDocument(namespaceURI, qualifiedName, doctype)

    def createDocumentType(self, qualifiedName, publicId, systemId):
        return _MinimalDocumentType(qualifiedName, publicId, systemId)


class _MinimalDocument(Node):
    nodeType = Node.DOCUMENT_NODE

    def __init__(self, namespaceURI, qualifiedName, doctype):
        self.namespaceURI = namespaceURI
        self.qualifiedName = qualifiedName
        self.doctype = doctype
        if doctype is not None:
            doctype.ownerDocument = self
        self.documentElement = None


class _MinimalDocumentType(Node):
    nodeType = Node.DOCUMENT_TYPE_NODE

    def __init__(self, qualifiedName, publicId, systemId):
        self.name = qualifiedName
        self.publicId = publicId
        self.systemId = systemId
        self.ownerDocument = None


# Internal registry of DOM implementation factories.
_registered = {}
_default_factory = lambda: _MinimalDOMImplementation()


def registerDOMImplementation(name, factory):
    """Register a DOM implementation factory callable under *name*."""
    _registered[name] = factory


def getDOMImplementation(name=None, features=()):
    """
    Return a suitable DOM implementation.

    If *name* is given, return that registered implementation (or None).
    Otherwise, scan registered implementations and return the first one
    that supports all requested features. Falls back to a built-in
    minimal implementation.
    """
    # Normalize features argument.  Accepts either a string of
    # "feature1 1.0 feature2 2.0" form or an iterable of (feature, ver) pairs.
    feats = _parse_feature_string(features) if isinstance(features, str) else list(features or ())

    if name is not None:
        factory = _registered.get(name)
        if factory is None:
            return None
        impl = factory()
        if _impl_supports(impl, feats):
            return impl
        return None

    for fact in _registered.values():
        impl = fact()
        if _impl_supports(impl, feats):
            return impl

    impl = _default_factory()
    if _impl_supports(impl, feats):
        return impl
    return None


def _impl_supports(impl, feats):
    for feat, ver in feats:
        if not impl.hasFeature(feat, ver):
            return False
    return True


def _parse_feature_string(s):
    """Parse a string like 'core 2.0 xml 1.0' into [('core','2.0'),('xml','1.0')]."""
    parts = s.split() if s else []
    out = []
    i = 0
    while i < len(parts):
        feat = parts[i]
        ver = None
        if i + 1 < len(parts):
            tok = parts[i + 1]
            # version is something starting with a digit
            if tok and tok[0].isdigit():
                ver = tok
                i += 2
            else:
                i += 1
        else:
            i += 1
        out.append((feat, ver))
    return out


# ---------------------------------------------------------------------------
# Invariant checks
# ---------------------------------------------------------------------------

def xmldom2_exceptions():
    """Verify the DOM exception hierarchy and code constants."""
    # All DOM-specific errors must subclass DOMException, which itself
    # inherits from Exception.
    if not issubclass(DOMException, Exception):
        return False

    pairs = [
        (IndexSizeErr,              INDEX_SIZE_ERR),
        (DomstringSizeErr,          DOMSTRING_SIZE_ERR),
        (HierarchyRequestErr,       HIERARCHY_REQUEST_ERR),
        (WrongDocumentErr,          WRONG_DOCUMENT_ERR),
        (InvalidCharacterErr,       INVALID_CHARACTER_ERR),
        (NoDataAllowedErr,          NO_DATA_ALLOWED_ERR),
        (NoModificationAllowedErr,  NO_MODIFICATION_ALLOWED_ERR),
        (NotFoundErr,               NOT_FOUND_ERR),
        (NotSupportedErr,           NOT_SUPPORTED_ERR),
        (InuseAttributeErr,         INUSE_ATTRIBUTE_ERR),
        (InvalidStateErr,           INVALID_STATE_ERR),
        (SyntaxErr,                 SYNTAX_ERR),
        (InvalidModificationErr,    INVALID_MODIFICATION_ERR),
        (NamespaceErr,              NAMESPACE_ERR),
        (InvalidAccessErr,          INVALID_ACCESS_ERR),
        (ValidationErr,             VALIDATION_ERR),
    ]
    seen = set()
    for cls, code in pairs:
        if not issubclass(cls, DOMException):
            return False
        if cls.code != code:
            return False
        try:
            inst = cls("msg")
        except Exception:
            return False
        if inst.code != code:
            return False
        if not isinstance(inst, DOMException):
            return False
        if not isinstance(inst, Exception):
            return False
        seen.add(code)

    # Direct DOMException instantiation must fail.
    try:
        DOMException("nope")
    except RuntimeError:
        pass
    else:
        return False

    # Codes must be unique and contiguous 1..16.
    if seen != set(range(1, 17)):
        return False

    return True


def xmldom2_node():
    """Verify the Node class constants and basic semantics."""
    expected = {
        "ELEMENT_NODE": 1,
        "ATTRIBUTE_NODE": 2,
        "TEXT_NODE": 3,
        "CDATA_SECTION_NODE": 4,
        "ENTITY_REFERENCE_NODE": 5,
        "ENTITY_NODE": 6,
        "PROCESSING_INSTRUCTION_NODE": 7,
        "COMMENT_NODE": 8,
        "DOCUMENT_NODE": 9,
        "DOCUMENT_TYPE_NODE": 10,
        "DOCUMENT_FRAGMENT_NODE": 11,
        "NOTATION_NODE": 12,
    }
    for attr, val in expected.items():
        if getattr(Node, attr, None) != val:
            return False

    # The 12 node-type values must all be distinct.
    if len(set(expected.values())) != 12:
        return False

    # Subclasses inherit the constants.
    class _Sub(Node):
        pass
    if _Sub.ELEMENT_NODE != 1 or _Sub.DOCUMENT_NODE != 9:
        return False

    # Default attributes exist on Node instances.
    n = Node()
    if n.parentNode is not None:
        return False
    if n.namespaceURI is not None:
        return False
    if not bool(n):
        return False

    return True


def xmldom2_get_dom():
    """Verify getDOMImplementation / registerDOMImplementation behavior."""
    # Default impl available.
    impl = getDOMImplementation()
    if impl is None:
        return False
    if not impl.hasFeature("core", "1.0"):
        return False
    if not impl.hasFeature("CORE", None):  # case-insensitive feature lookup
        return False
    if impl.hasFeature("nosuchfeature", "1.0"):
        return False

    # Unknown registered name returns None.
    if getDOMImplementation("__no_such_dom__") is not None:
        return False

    # Registering and looking up by name works.
    sentinel = _MinimalDOMImplementation()

    def _factory():
        return sentinel

    registerDOMImplementation("_test_impl_", _factory)
    try:
        got = getDOMImplementation("_test_impl_")
        if got is not sentinel:
            return False

        # Feature filtering: known feature succeeds.
        got2 = getDOMImplementation(features=[("core", "2.0")])
        if got2 is None:
            return False

        # Feature filtering: parsing a feature string also works.
        got3 = getDOMImplementation(features="core 2.0 xml 1.0")
        if got3 is None:
            return False

        # Unsupported feature → None.
        got4 = getDOMImplementation(features=[("bogus", "9.9")])
        if got4 is not None:
            return False
    finally:
        del _registered["_test_impl_"]

    # createDocument / createDocumentType produce nodes of the right type.
    dt = impl.createDocumentType("foo", None, None)
    if dt.nodeType != Node.DOCUMENT_TYPE_NODE:
        return False
    if dt.name != "foo":
        return False

    doc = impl.createDocument(None, "root", None)
    if doc.nodeType != Node.DOCUMENT_NODE:
        return False

    # A doctype already attached to a document cannot be reused.
    dt2 = impl.createDocumentType("bar", None, None)
    impl.createDocument(None, "x", dt2)
    try:
        impl.createDocument(None, "y", dt2)
    except WrongDocumentErr:
        pass
    else:
        return False

    return True