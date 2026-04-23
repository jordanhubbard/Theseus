"""
theseus_xml_sax_cr — Clean-room xml.sax module.
No import of xml.sax. Uses pyexpat C extension directly.
"""

import importlib.util as _importlib_util
import importlib.machinery as _importlib_machinery
import sysconfig as _sysconfig
import os as _os
import io as _io

# Load pyexpat C extension (the underlying engine for xml.sax)
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
# Exception classes
# ---------------------------------------------------------------------------

class SAXException(Exception):
    def __init__(self, msg, exception=None):
        self.msg = msg
        self._exception = exception
        super().__init__(msg)

    def getMessage(self):
        return self.msg

    def getException(self):
        return self._exception

    def __str__(self):
        return self.msg


class SAXParseException(SAXException):
    def __init__(self, msg, exception, locator):
        super().__init__(msg, exception)
        self._locator = locator

    def getColumnNumber(self):
        return self._locator.getColumnNumber() if self._locator else None

    def getLineNumber(self):
        return self._locator.getLineNumber() if self._locator else None

    def getPublicId(self):
        return self._locator.getPublicId() if self._locator else None

    def getSystemId(self):
        return self._locator.getSystemId() if self._locator else None


class SAXNotRecognizedException(SAXException):
    pass


class SAXNotSupportedException(SAXException):
    pass


# ---------------------------------------------------------------------------
# Locator
# ---------------------------------------------------------------------------

class Locator:
    def getColumnNumber(self):
        return None

    def getLineNumber(self):
        return None

    def getPublicId(self):
        return None

    def getSystemId(self):
        return None


class _ParserLocator(Locator):
    def __init__(self, parser):
        self._parser = parser

    def getColumnNumber(self):
        return self._parser.CurrentColumnNumber

    def getLineNumber(self):
        return self._parser.CurrentLineNumber

    def getPublicId(self):
        return None

    def getSystemId(self):
        return self._parser.SystemId


# ---------------------------------------------------------------------------
# Handler classes
# ---------------------------------------------------------------------------

class ContentHandler:
    def setDocumentLocator(self, locator):
        pass

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
    def warning(self, exception):
        pass

    def error(self, exception):
        raise exception

    def fatalError(self, exception):
        raise exception


class DTDHandler:
    def notationDecl(self, name, publicId, systemId):
        pass

    def unparsedEntityDecl(self, name, publicId, systemId, ndata):
        pass


class EntityResolver:
    def resolveEntity(self, publicId, systemId):
        return systemId


class LexicalHandler:
    def comment(self, content):
        pass

    def startDTD(self, name, public_id, system_id):
        pass

    def endDTD(self):
        pass

    def startEntity(self, name):
        pass

    def endEntity(self, name):
        pass

    def startCDATA(self):
        pass

    def endCDATA(self):
        pass


class AttributesImpl:
    def __init__(self, attrs):
        self._attrs = dict(attrs)

    def getLength(self):
        return len(self._attrs)

    def getType(self, name):
        return 'CDATA'

    def getValue(self, name):
        return self._attrs[name]

    def getNames(self):
        return list(self._attrs.keys())

    def getQNameByName(self, name):
        return name

    def __len__(self):
        return len(self._attrs)

    def __getitem__(self, name):
        return self._attrs[name]

    def __contains__(self, name):
        return name in self._attrs

    def get(self, name, default=None):
        return self._attrs.get(name, default)

    def keys(self):
        return self._attrs.keys()

    def values(self):
        return self._attrs.values()

    def items(self):
        return self._attrs.items()


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class ExpatParser:
    def __init__(self):
        self._handler = ContentHandler()
        self._error_handler = ErrorHandler()
        self._parser = None
        self._reset_parser()

    def _reset_parser(self):
        self._parser = _pyexpat.ParserCreate()
        self._parser.StartElementHandler = self._start_element
        self._parser.EndElementHandler = self._end_element
        self._parser.CharacterDataHandler = self._characters
        self._parser.StartDoctypeDeclHandler = None
        self._locator = _ParserLocator(self._parser)
        self._handler.setDocumentLocator(self._locator)

    def _start_element(self, name, attrs):
        self._handler.startElement(name, AttributesImpl(attrs))

    def _end_element(self, name):
        self._handler.endElement(name)

    def _characters(self, data):
        self._handler.characters(data)

    def setContentHandler(self, handler):
        self._handler = handler
        if hasattr(handler, 'setDocumentLocator'):
            handler.setDocumentLocator(self._locator)

    def getContentHandler(self):
        return self._handler

    def setErrorHandler(self, handler):
        self._error_handler = handler

    def getErrorHandler(self):
        return self._error_handler

    def setDTDHandler(self, handler):
        pass

    def setEntityResolver(self, resolver):
        pass

    def getFeature(self, name):
        return False

    def setFeature(self, name, state):
        pass

    def getProperty(self, name):
        raise SAXNotRecognizedException(f"Unknown property: {name}")

    def setProperty(self, name, value):
        pass

    def parse(self, source):
        if isinstance(source, str):
            with open(source, 'rb') as f:
                data = f.read()
        elif hasattr(source, 'read'):
            data = source.read()
            if isinstance(data, str):
                data = data.encode('utf-8')
        else:
            data = source

        try:
            self._handler.startDocument()
            self._parser.Parse(data, True)
            self._handler.endDocument()
        except _pyexpat.ExpatError as e:
            exc = SAXParseException(str(e), e, self._locator)
            self._error_handler.fatalError(exc)

    def parseString(self, data, handler=None):
        if handler is not None:
            self.setContentHandler(handler)
        if isinstance(data, str):
            data = data.encode('utf-8')
        try:
            self._handler.startDocument()
            self._parser.Parse(data, True)
            self._handler.endDocument()
        except _pyexpat.ExpatError as e:
            exc = SAXParseException(str(e), e, self._locator)
            self._error_handler.fatalError(exc)


def make_parser(parser_list=None):
    return ExpatParser()


def parse(source, handler=None, error_handler=ErrorHandler()):
    parser = make_parser()
    if handler is not None:
        parser.setContentHandler(handler)
    parser.setErrorHandler(error_handler)
    parser.parse(source)


def parseString(string, handler=None, error_handler=ErrorHandler()):
    parser = make_parser()
    if handler is not None:
        parser.setContentHandler(handler)
    parser.setErrorHandler(error_handler)
    parser.parseString(string)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def xmlsax2_exceptions():
    """SAXException and SAXParseException exist; returns True."""
    return (issubclass(SAXParseException, SAXException) and
            issubclass(SAXException, Exception))


def xmlsax2_parsestring():
    """parseString() parses a simple XML document; returns True."""
    class _Collector(ContentHandler):
        def __init__(self):
            self.elements = []
        def startElement(self, name, attrs):
            self.elements.append(name)

    collector = _Collector()
    parseString(b'<root><child/></root>', collector)
    return 'root' in collector.elements and 'child' in collector.elements


def xmlsax2_handler():
    """ContentHandler class is present with startElement; returns True."""
    return (hasattr(ContentHandler, 'startElement') and
            hasattr(ContentHandler, 'endElement') and
            hasattr(ContentHandler, 'characters'))


__all__ = [
    'SAXException', 'SAXParseException', 'SAXNotRecognizedException', 'SAXNotSupportedException',
    'ContentHandler', 'ErrorHandler', 'DTDHandler', 'EntityResolver', 'LexicalHandler',
    'AttributesImpl', 'Locator',
    'ExpatParser', 'make_parser', 'parse', 'parseString',
    'xmlsax2_exceptions', 'xmlsax2_parsestring', 'xmlsax2_handler',
]
