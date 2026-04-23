"""
theseus_xmlrpc_client_cr — Clean-room xmlrpc.client module.
No import of the standard `xmlrpc.client` module.
"""

import datetime as _datetime
import re as _re


class Error(Exception):
    pass


class Fault(Error):
    """Indicates a XML-RPC fault package."""

    def __init__(self, faultCode, faultString, **extra):
        Error.__init__(self)
        self.faultCode = faultCode
        self.faultString = faultString

    def __repr__(self):
        return '<Fault %s: %r>' % (self.faultCode, self.faultString)

    def __str__(self):
        return str(self.faultCode)


class ProtocolError(Error):
    """Indicates an HTTP protocol error."""

    def __init__(self, url, errcode, errmsg, headers):
        Error.__init__(self)
        self.url = url
        self.errcode = errcode
        self.errmsg = errmsg
        self.headers = headers

    def __repr__(self):
        return '<ProtocolError for %s: %s %s>' % (self.url, self.errcode, self.errmsg)

    def __str__(self):
        return str(self.errcode)


class ResponseError(Error):
    pass


class DateTime:
    """DateTime wrapper for XML-RPC dateTime.iso8601 type."""

    def __init__(self, value=0):
        if isinstance(value, str):
            self.value = value
        elif isinstance(value, (int, float)):
            self.value = _datetime.datetime.utcfromtimestamp(value).strftime('%Y%m%dT%H:%M:%S')
        elif isinstance(value, _datetime.datetime):
            self.value = value.strftime('%Y%m%dT%H:%M:%S')
        elif isinstance(value, _datetime.date):
            self.value = value.strftime('%Y%m%dT00:00:00')
        else:
            self.value = str(value)

    def __repr__(self):
        return '<DateTime %s at %#x>' % (self.value, id(self))

    def __str__(self):
        return self.value

    def timetuple(self):
        return _datetime.datetime.strptime(self.value, '%Y%m%dT%H:%M:%S').timetuple()


class Binary:
    """Wrapper for binary data."""

    def __init__(self, data=None):
        if data is None:
            data = b''
        self.data = data

    def __str__(self):
        return str(self.data, 'latin-1')

    def __repr__(self):
        return '<Binary %r>' % self.data

    def decode(self, data):
        import base64
        self.data = base64.decodebytes(data)

    def encode(self, out):
        import base64
        import io
        encoded = base64.encodebytes(self.data)
        out.write(encoded.decode('ascii'))


class Boolean:
    """Boolean wrapper for XML-RPC."""

    def __init__(self, value=0):
        self.value = bool(value)

    def encode(self, out):
        out.write('<boolean>%d</boolean>' % int(self.value))

    def __bool__(self):
        return self.value

    def __repr__(self):
        return '<Boolean %s at %#x>' % (self.value, id(self))

    def __str__(self):
        return self.value and 'True' or 'False'

    def __int__(self):
        return int(self.value)

    def __eq__(self, other):
        if isinstance(other, Boolean):
            return self.value == other.value
        return self.value == other

    def __ne__(self, other):
        if isinstance(other, Boolean):
            return self.value != other.value
        return self.value != other


TRUE = Boolean(1)
FALSE = Boolean(0)

MAXINT = 2**31 - 1
MININT = -2**31


def _escape(s):
    s = s.replace('&', '&amp;')
    s = s.replace('<', '&lt;')
    s = s.replace('>', '&gt;')
    return s


def _serialize_value(value, out):
    if isinstance(value, bool):
        out.write('<value><boolean>%d</boolean></value>' % int(value))
    elif isinstance(value, int):
        out.write('<value><int>%d</int></value>' % value)
    elif isinstance(value, float):
        out.write('<value><double>%s</double></value>' % repr(value))
    elif isinstance(value, str):
        out.write('<value><string>%s</string></value>' % _escape(value))
    elif isinstance(value, bytes):
        import base64
        out.write('<value><base64>%s</base64></value>' % base64.encodebytes(value).decode('ascii').strip())
    elif isinstance(value, (list, tuple)):
        out.write('<value><array><data>')
        for v in value:
            _serialize_value(v, out)
        out.write('</data></array></value>')
    elif isinstance(value, dict):
        out.write('<value><struct>')
        for k, v in value.items():
            out.write('<member><name>%s</name>' % _escape(str(k)))
            _serialize_value(v, out)
            out.write('</member>')
        out.write('</struct></value>')
    elif value is None:
        out.write('<value><nil/></value>')
    elif isinstance(value, DateTime):
        out.write('<value><dateTime.iso8601>%s</dateTime.iso8601></value>' % value.value)
    elif isinstance(value, Binary):
        import base64
        out.write('<value><base64>%s</base64></value>' % base64.encodebytes(value.data).decode('ascii').strip())
    elif isinstance(value, Boolean):
        out.write('<value><boolean>%d</boolean></value>' % int(value.value))
    else:
        out.write('<value><string>%s</string></value>' % _escape(str(value)))


def dumps(params, methodname=None, methodresponse=None, encoding=None, allow_none=False):
    """Serialize params and methodname to XML-RPC."""
    import io
    out = io.StringIO()
    out.write("<?xml version='1.0'?>\n")
    if methodname:
        out.write('<methodCall>\n')
        out.write('<methodName>%s</methodName>\n' % _escape(methodname))
        out.write('<params>\n')
        for param in params:
            out.write('<param>')
            _serialize_value(param, out)
            out.write('</param>\n')
        out.write('</params>\n')
        out.write('</methodCall>\n')
    elif methodresponse:
        out.write('<methodResponse>\n')
        if isinstance(params, Fault):
            out.write('<fault><value><struct>')
            out.write('<member><name>faultCode</name><value><int>%d</int></value></member>' % params.faultCode)
            out.write('<member><name>faultString</name><value><string>%s</string></value></member>' % _escape(params.faultString))
            out.write('</struct></value></fault>\n')
        else:
            out.write('<params>\n')
            for param in params:
                out.write('<param>')
                _serialize_value(param, out)
                out.write('</param>\n')
            out.write('</params>\n')
        out.write('</methodResponse>\n')
    return out.getvalue()


def loads(data):
    """Parse XML-RPC response or method call."""
    import xml.etree.ElementTree as ET
    root = ET.fromstring(data)

    def _deserialize(node):
        tag = node.tag
        if tag == 'value':
            children = list(node)
            if not children:
                return node.text or ''
            return _deserialize(children[0])
        elif tag == 'int' or tag == 'i4' or tag == 'i8':
            return int(node.text or '0')
        elif tag == 'double':
            return float(node.text or '0.0')
        elif tag == 'boolean':
            return bool(int(node.text or '0'))
        elif tag == 'string':
            return node.text or ''
        elif tag == 'base64':
            import base64
            return Binary(base64.decodebytes((node.text or '').encode('ascii')))
        elif tag == 'dateTime.iso8601':
            return DateTime(node.text or '')
        elif tag == 'nil':
            return None
        elif tag == 'array':
            data_node = node.find('data')
            return [_deserialize(v) for v in (data_node or node).findall('value')]
        elif tag == 'struct':
            result = {}
            for member in node.findall('member'):
                name = member.find('name').text
                value = _deserialize(member.find('value'))
                result[name] = value
            return result
        return None

    method_name = None
    if root.tag == 'methodCall':
        method_node = root.find('methodName')
        if method_node is not None:
            method_name = method_node.text
    elif root.tag == 'methodResponse':
        fault = root.find('fault')
        if fault is not None:
            fault_val = _deserialize(fault.find('value'))
            raise Fault(fault_val['faultCode'], fault_val['faultString'])

    params = []
    params_node = root.find('params')
    if params_node is not None:
        for param in params_node.findall('param'):
            params.append(_deserialize(param.find('value')))

    return tuple(params), method_name


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def xmlrpc2_boolean():
    """Boolean values marshal correctly; returns True."""
    b = Boolean(True)
    import io
    out = io.StringIO()
    b.encode(out)
    return '<boolean>1</boolean>' in out.getvalue()


def xmlrpc2_fault():
    """Fault class stores faultCode and faultString; returns True."""
    f = Fault(42, 'Something went wrong')
    return f.faultCode == 42 and f.faultString == 'Something went wrong'


def xmlrpc2_dumps():
    """dumps produces valid XML-RPC method call XML; returns True."""
    xml = dumps(('hello', 42), methodname='test.method')
    return '<methodCall>' in xml and '<methodName>test.method</methodName>' in xml


__all__ = [
    'Error', 'Fault', 'ProtocolError', 'ResponseError',
    'DateTime', 'Binary', 'Boolean', 'TRUE', 'FALSE',
    'dumps', 'loads', 'MAXINT', 'MININT',
    'xmlrpc2_boolean', 'xmlrpc2_fault', 'xmlrpc2_dumps',
]
