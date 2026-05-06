"""Clean-room implementation of email.mime.text functionality."""


class MIMEText:
    """A minimal clean-room MIMEText-style message."""

    def __init__(self, _text, _subtype='plain', _charset='us-ascii'):
        self._text = _text
        self._subtype = _subtype
        self._charset = _charset
        self._headers = []
        self._headers.append(('MIME-Version', '1.0'))
        self._headers.append(
            ('Content-Type', 'text/' + _subtype + '; charset="' + _charset + '"')
        )
        self._headers.append(('Content-Transfer-Encoding', '7bit'))

    def get_content_type(self):
        return 'text/' + self._subtype

    def get_content_subtype(self):
        return self._subtype

    def get_content_maintype(self):
        return 'text'

    def get_charset(self):
        return self._charset

    def get_payload(self, decode=False):
        if decode:
            return self._text.encode(self._charset, errors='replace')
        return self._text

    def set_payload(self, payload, charset=None):
        self._text = payload
        if charset is not None:
            self._charset = charset
            # Update Content-Type header
            for i, (k, v) in enumerate(self._headers):
                if k.lower() == 'content-type':
                    self._headers[i] = (
                        'Content-Type',
                        'text/' + self._subtype + '; charset="' + charset + '"',
                    )
                    break

    def __getitem__(self, name):
        lname = name.lower()
        for k, v in self._headers:
            if k.lower() == lname:
                return v
        return None

    def __setitem__(self, name, value):
        # Replace if exists, else append
        lname = name.lower()
        for i, (k, v) in enumerate(self._headers):
            if k.lower() == lname:
                self._headers[i] = (name, value)
                return
        self._headers.append((name, value))

    def __delitem__(self, name):
        lname = name.lower()
        self._headers = [(k, v) for (k, v) in self._headers if k.lower() != lname]

    def __contains__(self, name):
        lname = name.lower()
        for k, _v in self._headers:
            if k.lower() == lname:
                return True
        return False

    def keys(self):
        return [k for (k, _v) in self._headers]

    def values(self):
        return [v for (_k, v) in self._headers]

    def items(self):
        return list(self._headers)

    def add_header(self, name, value):
        self._headers.append((name, value))

    def replace_header(self, name, value):
        self[name] = value

    def as_string(self, unixfrom=False):
        parts = []
        for k, v in self._headers:
            parts.append(str(k) + ': ' + str(v))
        parts.append('')
        parts.append(self._text if self._text is not None else '')
        return '\n'.join(parts)

    def __str__(self):
        return self.as_string()


def mimetext2_create():
    msg = MIMEText('Hello, World!')
    if msg.get_content_type() != 'text/plain':
        return False
    if msg.get_payload() != 'Hello, World!':
        return False
    if msg.get_content_maintype() != 'text':
        return False
    if msg.get_content_subtype() != 'plain':
        return False
    return True


def mimetext2_html():
    msg = MIMEText('<h1>Hello</h1>', 'html')
    if msg.get_content_type() != 'text/html':
        return False
    if msg.get_payload() != '<h1>Hello</h1>':
        return False
    if msg.get_content_subtype() != 'html':
        return False
    return True


def mimetext2_as_string():
    msg = MIMEText('Test content')
    msg['Subject'] = 'Test Subject'
    msg['From'] = 'a@example.com'
    msg['To'] = 'b@example.com'
    s = msg.as_string()
    if 'Content-Type' not in s:
        return False
    if 'text/plain' not in s:
        return False
    if 'Test content' not in s:
        return False
    if 'Subject: Test Subject' not in s:
        return False
    if 'MIME-Version' not in s:
        return False
    return True