"""
theseus_email_mime_text_cr — Clean-room email.mime.text module.
No import of email.mime.text.
Uses email.message (a different module) for the base class.
"""

import email.message as _email_message
import email.charset as _email_charset
import email.encoders as _email_encoders


class MIMEText(_email_message.Message):
    """Create a MIME text/* type message."""

    def __init__(self, _text, _subtype='plain', _charset=None, *, policy=None):
        if policy is None:
            from email import policy as _email_policy
            policy = _email_policy.compat32

        super().__init__(policy=policy)

        if _charset is None:
            if _subtype == 'plain':
                _charset = 'us-ascii'
            else:
                _charset = 'utf-8'

        if isinstance(_charset, str):
            _charset = _email_charset.Charset(_charset)

        self['MIME-Version'] = '1.0'
        self['Content-Type'] = f'text/{_subtype}'
        self.set_type(f'text/{_subtype}')

        if isinstance(_text, str):
            charset = _charset.get_output_charset() if hasattr(_charset, 'get_output_charset') else str(_charset)
            self.set_payload(_text, _charset)
        else:
            self.set_payload(_text)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def mimetext2_create():
    """MIMEText('hello') creates a text/plain MIME message; returns True."""
    msg = MIMEText('Hello World')
    return msg.get_content_type() == 'text/plain'


def mimetext2_html():
    """MIMEText('<p>hi</p>', 'html') has content-type text/html; returns True."""
    msg = MIMEText('<p>hi</p>', 'html')
    return msg.get_content_type() == 'text/html'


def mimetext2_as_string():
    """as_string() returns a properly formatted MIME message; returns True."""
    msg = MIMEText('Test message', 'plain')
    msg['From'] = 'test@example.com'
    msg['To'] = 'recv@example.com'
    msg['Subject'] = 'Test'
    s = msg.as_string()
    return 'Content-Type: text/plain' in s and 'Test message' in s


__all__ = [
    'MIMEText',
    'mimetext2_create', 'mimetext2_html', 'mimetext2_as_string',
]
