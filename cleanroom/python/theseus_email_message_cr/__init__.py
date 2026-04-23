"""
theseus_email_message_cr — Clean-room email.message module.
No import of the standard `email.message` module.
Uses email.message.Message from stdlib as base since we're blocking only
email.message at the top-level import, but we use email.message via
importlib to avoid the blocker.
"""

import sys as _sys
import importlib.util as _ilu
import importlib.machinery as _ilm
import re as _re


# We need to pull Message from email.message directly.
# Since email.message is the blocked module, we use importlib to load
# email._header_value_parser which doesn't trigger the blocker.
# Instead, we implement Message from scratch.

class Message:
    """A clean-room implementation of email.message.Message."""

    def __init__(self, policy=None):
        self._headers = []
        self._payload = None
        self._charset = None
        self._default_type = 'text/plain'
        self.preamble = None
        self.epilogue = None
        self.defects = []
        self.policy = policy

    def __str__(self):
        return self.as_string()

    def __bytes__(self):
        return self.as_bytes()

    def as_string(self, unixfrom=False, maxheaderlen=0, policy=None):
        from io import StringIO as _StringIO
        lines = []
        for name, value in self._headers:
            lines.append('%s: %s' % (name, value))
        lines.append('')
        if self._payload is not None:
            if isinstance(self._payload, list):
                for part in self._payload:
                    lines.append(str(part))
            else:
                lines.append(self._payload)
        return '\n'.join(lines)

    def as_bytes(self, unixfrom=False, policy=None):
        return self.as_string(unixfrom=unixfrom).encode('utf-8', errors='replace')

    def is_multipart(self):
        return isinstance(self._payload, list)

    def set_unixfrom(self, unixfrom):
        self._unixfrom = unixfrom

    def get_unixfrom(self):
        return getattr(self, '_unixfrom', None)

    def attach(self, payload):
        if self._payload is None:
            self._payload = []
        self._payload.append(payload)

    def get_payload(self, i=None, decode=False):
        if i is None:
            payload = self._payload
        elif not isinstance(self._payload, list):
            raise TypeError('index requires multipart payload')
        else:
            payload = self._payload[i]
        if decode and not isinstance(payload, list):
            cte = self.get('content-transfer-encoding', '').lower()
            if cte == 'quoted-printable':
                import quopri as _q
                return _q.decodestring(payload.encode('raw-unicode-escape'))
            elif cte == 'base64':
                import base64 as _b
                return _b.decodebytes(payload.encode('raw-unicode-escape'))
        return payload

    def set_payload(self, payload, charset=None):
        self._payload = payload
        if charset is not None:
            self._charset = charset

    def set_charset(self, charset):
        self._charset = charset

    def get_charset(self):
        return self._charset

    def __len__(self):
        return len(self._headers)

    def __contains__(self, name):
        return name.lower() in [k.lower() for k, v in self._headers]

    def __getitem__(self, name):
        return self.get(name)

    def __setitem__(self, name, val):
        self._headers.append((name, val))

    def __delitem__(self, name):
        name_lower = name.lower()
        self._headers = [(k, v) for k, v in self._headers
                         if k.lower() != name_lower]

    def keys(self):
        return [k for k, v in self._headers]

    def values(self):
        return [v for k, v in self._headers]

    def items(self):
        return list(self._headers)

    def get(self, name, failobj=None):
        name_lower = name.lower()
        for k, v in self._headers:
            if k.lower() == name_lower:
                return v
        return failobj

    def get_all(self, name, failobj=None):
        name_lower = name.lower()
        values = [v for k, v in self._headers if k.lower() == name_lower]
        return values if values else failobj

    def add_header(self, _name, _value, **_params):
        parts = []
        for k, v in _params.items():
            k = k.replace('_', '-')
            if v is None:
                parts.append(k)
            else:
                parts.append('%s="%s"' % (k, v))
        if parts:
            _value = _value + '; ' + '; '.join(parts)
        self._headers.append((_name, _value))

    def replace_header(self, _name, _value):
        _name_lower = _name.lower()
        for i, (k, v) in enumerate(self._headers):
            if k.lower() == _name_lower:
                self._headers[i] = (k, _value)
                return
        raise KeyError(_name)

    def get_content_type(self):
        missing = object()
        value = self.get('content-type', missing)
        if value is missing:
            return self._default_type
        # Strip parameters
        return value.split(';')[0].strip().lower()

    def get_content_maintype(self):
        ctype = self.get_content_type()
        return ctype.split('/')[0]

    def get_content_subtype(self):
        ctype = self.get_content_type()
        parts = ctype.split('/')
        return parts[1] if len(parts) > 1 else ''

    def get_default_type(self):
        return self._default_type

    def set_default_type(self, ctype):
        self._default_type = ctype

    def get_params(self, failobj=None, header='content-type', unquote=True):
        missing = object()
        value = self.get(header, missing)
        if value is missing:
            return failobj
        params = []
        for part in value.split(';'):
            part = part.strip()
            if '=' in part:
                k, _, v = part.partition('=')
                params.append((k.strip(), v.strip().strip('"')))
            else:
                params.append((part, ''))
        return params

    def get_param(self, param, failobj=None, header='content-type', unquote=True):
        params = self.get_params(failobj=None, header=header, unquote=unquote)
        if params is None:
            return failobj
        param = param.lower()
        for k, v in params[1:]:
            if k.lower() == param:
                return v
        return failobj

    def set_param(self, param, value, header='Content-Type', requote=True,
                  charset=None, language='', replace=False):
        current = self.get(header)
        if current is None:
            self[header] = '%s=%s' % (param, value)
        else:
            parts = current.split(';')
            param_lower = param.lower()
            new_parts = []
            found = False
            for part in parts:
                part = part.strip()
                if '=' in part:
                    k, _, v = part.partition('=')
                    if k.strip().lower() == param_lower:
                        new_parts.append('%s="%s"' % (k.strip(), value))
                        found = True
                        continue
                new_parts.append(part)
            if not found:
                new_parts.append('%s="%s"' % (param, value))
            self.replace_header(header, '; '.join(new_parts))

    def del_param(self, param, header='content-type', requote=True):
        current = self.get(header)
        if current is None:
            return
        parts = current.split(';')
        param_lower = param.lower()
        new_parts = [p for p in parts
                     if param_lower not in p.lower().split('=')[0].strip().lower()]
        self.replace_header(header, '; '.join(new_parts))

    def set_type(self, type, header='Content-Type', requote=True):
        current = self.get(header)
        if current is None:
            self[header] = type
        else:
            parts = current.split(';')
            parts[0] = type
            self.replace_header(header, '; '.join(parts))

    def get_filename(self, failobj=None):
        return self.get_param('filename', failobj, 'content-disposition')

    def get_boundary(self, failobj=None):
        return self.get_param('boundary', failobj)

    def set_boundary(self, boundary):
        self.set_param('boundary', boundary)

    def get_content_charset(self, failobj=None):
        return self.get_param('charset', failobj)

    def get_charsets(self, failobj=None):
        return [self.get_content_charset(failobj)]

    def walk(self):
        yield self
        if self.is_multipart():
            for subpart in self._payload:
                yield from subpart.walk()


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def emailmsg2_create():
    """Message can be created and headers set; returns True."""
    msg = Message()
    msg['Subject'] = 'Test Subject'
    msg['From'] = 'sender@example.com'
    return (msg['Subject'] == 'Test Subject' and
            msg['From'] == 'sender@example.com')


def emailmsg2_payload():
    """Message payload can be set and retrieved; returns True."""
    msg = Message()
    msg.set_payload('Hello, World!')
    return msg.get_payload() == 'Hello, World!'


def emailmsg2_content_type():
    """get_content_type() returns content type string; returns True."""
    msg = Message()
    msg['Content-Type'] = 'text/plain; charset=utf-8'
    return msg.get_content_type() == 'text/plain'


__all__ = [
    'Message',
    'emailmsg2_create', 'emailmsg2_payload', 'emailmsg2_content_type',
]
