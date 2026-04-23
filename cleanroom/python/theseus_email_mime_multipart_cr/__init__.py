"""
theseus_email_mime_multipart_cr — Clean-room email.mime.multipart module.
No import of email.mime.multipart.
"""

import email.message as _message


class MIMEMultipart(_message.Message):
    def __init__(self, _subtype='mixed', boundary=None, _subparts=None,
                 *, policy=None, **_params):
        _message.Message.__init__(self)
        ctype = 'multipart/' + _subtype
        self['MIME-Version'] = '1.0'
        self['Content-Type'] = ctype
        if boundary is not None:
            self.set_param('boundary', boundary)
        if _subparts is not None:
            for p in _subparts:
                self.attach(p)
        for k, v in _params.items():
            self.set_param(k, v)

    def attach(self, payload):
        if self._payload is None:
            self._payload = []
        self._payload.append(payload)

    def as_string(self, unixfrom=False, maxheaderlen=0, policy=None):
        from email import generator as _gen
        import io as _io
        fp = _io.StringIO()
        g = _gen.Generator(fp, mangle_from_=False, maxheaderlen=maxheaderlen)
        g.flatten(self, unixfrom=unixfrom)
        return fp.getvalue()

    def __str__(self):
        return self.as_string()


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def mimemultipart2_create():
    """MIMEMultipart can be created; returns True."""
    msg = MIMEMultipart()
    return isinstance(msg, MIMEMultipart) and msg.get_content_type() == 'multipart/mixed'


def mimemultipart2_attach():
    """MIMEMultipart.attach() works; returns True."""
    from email.mime.text import MIMEText
    msg = MIMEMultipart()
    part = MIMEText('hello', 'plain')
    msg.attach(part)
    payload = msg.get_payload()
    return isinstance(payload, list) and len(payload) == 1


def mimemultipart2_as_string():
    """MIMEMultipart.as_string() returns a non-empty string; returns True."""
    msg = MIMEMultipart()
    s = msg.as_string()
    return isinstance(s, str) and 'multipart/mixed' in s


__all__ = [
    'MIMEMultipart',
    'mimemultipart2_create', 'mimemultipart2_attach', 'mimemultipart2_as_string',
]
