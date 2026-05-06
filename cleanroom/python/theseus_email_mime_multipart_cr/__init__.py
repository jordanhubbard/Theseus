"""Clean-room implementation of email.mime.multipart-like functionality.

This module provides a minimal MIMEMultipart class without importing
email.mime.multipart or any other email submodule. Only Python standard
library built-ins are used (and only generic ones, not email.*).
"""

import re as _re


# ---------------------------------------------------------------------------
# Header utilities
# ---------------------------------------------------------------------------

def _format_param(name, value):
    """Format a single header parameter as name=value or name="value"."""
    if value is None:
        return name
    s = str(value)
    # Quote if it contains anything other than token characters.
    if _re.search(r'[^A-Za-z0-9!#$%&\'*+\-.^_`|~]', s):
        s = s.replace('\\', '\\\\').replace('"', '\\"')
        return '%s="%s"' % (name, s)
    return '%s=%s' % (name, s)


def _format_header(name, value, params=None):
    parts = [str(value)] if value is not None else []
    if params:
        for k, v in params:
            parts.append(_format_param(k, v))
    return '%s: %s' % (name, '; '.join(parts))


# ---------------------------------------------------------------------------
# Base MIME message
# ---------------------------------------------------------------------------

class _MIMEBase(object):
    """Minimal MIME message-like object."""

    def __init__(self, maintype='text', subtype='plain', **params):
        self._headers = []  # list of (name, value, params)
        self._payload = None  # str OR list of _MIMEBase
        self._maintype = maintype
        self._subtype = subtype
        self._content_params = list(params.items())
        # Default headers
        self._set_header('MIME-Version', '1.0')
        self._set_header(
            'Content-Type',
            '%s/%s' % (maintype, subtype),
            params=list(params.items()),
        )

    # -- header management ---------------------------------------------------

    def _set_header(self, name, value, params=None):
        # Replace if exists, else append
        for i, (n, _v, _p) in enumerate(self._headers):
            if n.lower() == name.lower():
                self._headers[i] = (name, value, list(params) if params else [])
                return
        self._headers.append((name, value, list(params) if params else []))

    def add_header(self, name, value, **params):
        plist = []
        for k, v in params.items():
            # email.message replaces underscores with dashes for param names
            plist.append((k.replace('_', '-'), v))
        self._headers.append((name, value, plist))

    def __setitem__(self, name, value):
        self._headers.append((name, value, []))

    def __getitem__(self, name):
        for n, v, p in self._headers:
            if n.lower() == name.lower():
                if p:
                    return '; '.join(
                        [str(v)] + [_format_param(k, pv) for k, pv in p]
                    )
                return v
        return None

    def __delitem__(self, name):
        self._headers = [
            (n, v, p) for (n, v, p) in self._headers
            if n.lower() != name.lower()
        ]

    def __contains__(self, name):
        return any(n.lower() == name.lower() for n, _v, _p in self._headers)

    def keys(self):
        return [n for n, _v, _p in self._headers]

    def items(self):
        return [(n, self[n]) for n, _v, _p in self._headers]

    def get(self, name, default=None):
        v = self[name]
        return default if v is None else v

    # -- payload management --------------------------------------------------

    def get_payload(self):
        return self._payload

    def set_payload(self, payload):
        self._payload = payload

    def attach(self, part):
        if not isinstance(self._payload, list):
            if self._payload is None:
                self._payload = []
            else:
                self._payload = [self._payload]
        self._payload.append(part)

    def is_multipart(self):
        return isinstance(self._payload, list)

    def get_content_type(self):
        return '%s/%s' % (self._maintype, self._subtype)

    def get_content_maintype(self):
        return self._maintype

    def get_content_subtype(self):
        return self._subtype

    # -- serialization -------------------------------------------------------

    def _headers_as_string(self):
        out = []
        for name, value, params in self._headers:
            out.append(_format_header(name, value, params))
        return '\n'.join(out)

    def as_string(self, unixfrom=False):
        header_str = self._headers_as_string()
        if self.is_multipart():
            boundary = self._get_boundary()
            if not boundary:
                boundary = self._make_boundary()
                self._set_boundary(boundary)
            body_parts = []
            for part in self._payload:
                body_parts.append(part.as_string())
            body = ''
            for p in body_parts:
                body += '--%s\n%s\n' % (boundary, p)
            body += '--%s--\n' % boundary
            preamble = '\nThis is a multi-part message in MIME format.\n'
            return header_str + '\n' + preamble + body
        else:
            payload = self._payload if self._payload is not None else ''
            return header_str + '\n\n' + str(payload)

    def __str__(self):
        return self.as_string()

    # -- boundary helpers ---------------------------------------------------

    def _get_boundary(self):
        for name, _value, params in self._headers:
            if name.lower() == 'content-type':
                for k, v in params:
                    if k.lower() == 'boundary':
                        return v
        return None

    def _set_boundary(self, boundary):
        for i, (name, value, params) in enumerate(self._headers):
            if name.lower() == 'content-type':
                new_params = [(k, v) for k, v in params if k.lower() != 'boundary']
                new_params.append(('boundary', boundary))
                self._headers[i] = (name, value, new_params)
                return
        # If no Content-Type yet, add one
        self._set_header(
            'Content-Type',
            '%s/%s' % (self._maintype, self._subtype),
            params=[('boundary', boundary)],
        )

    def set_boundary(self, boundary):
        self._set_boundary(boundary)

    def get_boundary(self, failobj=None):
        b = self._get_boundary()
        return failobj if b is None else b

    @staticmethod
    def _make_boundary():
        import time as _time
        import random as _random
        token = '%d.%d' % (int(_time.time() * 1000), _random.randint(0, 1 << 30))
        return '===============' + token + '=='


# ---------------------------------------------------------------------------
# MIMEMultipart
# ---------------------------------------------------------------------------

class MIMEMultipart(_MIMEBase):
    """Base class for MIME multipart/* type messages."""

    def __init__(self, _subtype='mixed', boundary=None, _subparts=None, **_params):
        params = dict(_params)
        if boundary is not None:
            params['boundary'] = boundary
        _MIMEBase.__init__(self, 'multipart', _subtype, **params)
        # Multipart messages always have a list payload.
        self._payload = []
        if boundary is None:
            # Generate a boundary and put it into Content-Type
            b = self._make_boundary()
            self._set_boundary(b)
        if _subparts is not None:
            for part in _subparts:
                self.attach(part)


# ---------------------------------------------------------------------------
# Invariant-check functions
# ---------------------------------------------------------------------------

def mimemultipart2_create():
    """Verify that MIMEMultipart can be constructed with sane defaults."""
    try:
        m = MIMEMultipart()
        if m.get_content_maintype() != 'multipart':
            return False
        if m.get_content_subtype() != 'mixed':
            return False
        if not m.is_multipart():
            return False
        if m.get_boundary() is None:
            return False
        if m['MIME-Version'] != '1.0':
            return False
        # Custom subtype
        m2 = MIMEMultipart('alternative')
        if m2.get_content_subtype() != 'alternative':
            return False
        # Custom boundary
        m3 = MIMEMultipart('related', boundary='BOUNDARY123')
        if m3.get_boundary() != 'BOUNDARY123':
            return False
        return True
    except Exception:
        return False


def mimemultipart2_attach():
    """Verify that parts can be attached to a MIMEMultipart."""
    try:
        m = MIMEMultipart()
        if m.get_payload() != []:
            return False
        part1 = _MIMEBase('text', 'plain')
        part1.set_payload('hello')
        m.attach(part1)
        part2 = _MIMEBase('text', 'html')
        part2.set_payload('<b>hello</b>')
        m.attach(part2)
        payload = m.get_payload()
        if not isinstance(payload, list):
            return False
        if len(payload) != 2:
            return False
        if payload[0] is not part1 or payload[1] is not part2:
            return False
        if not m.is_multipart():
            return False
        # Constructor with _subparts should also work
        m2 = MIMEMultipart('mixed', _subparts=[part1, part2])
        if len(m2.get_payload()) != 2:
            return False
        return True
    except Exception:
        return False


def mimemultipart2_as_string():
    """Verify that a MIMEMultipart serializes to a sensible string."""
    try:
        m = MIMEMultipart('alternative', boundary='BNDRY')
        m['Subject'] = 'Test'
        m['From'] = 'a@example.com'
        m['To'] = 'b@example.com'
        part1 = _MIMEBase('text', 'plain', charset='utf-8')
        part1.set_payload('plain text')
        part2 = _MIMEBase('text', 'html', charset='utf-8')
        part2.set_payload('<p>html text</p>')
        m.attach(part1)
        m.attach(part2)
        s = m.as_string()
        if not isinstance(s, str):
            return False
        # Required headers
        if 'MIME-Version: 1.0' not in s:
            return False
        if 'multipart/alternative' not in s:
            return False
        if 'boundary="BNDRY"' not in s and 'boundary=BNDRY' not in s:
            return False
        if 'Subject: Test' not in s:
            return False
        # Boundary markers
        if '--BNDRY' not in s:
            return False
        if '--BNDRY--' not in s:
            return False
        # Sub-part content types
        if 'text/plain' not in s:
            return False
        if 'text/html' not in s:
            return False
        # Sub-part bodies
        if 'plain text' not in s:
            return False
        if '<p>html text</p>' not in s:
            return False
        # Empty multipart still works
        empty = MIMEMultipart(boundary='X')
        es = empty.as_string()
        if '--X--' not in es:
            return False
        return True
    except Exception:
        return False