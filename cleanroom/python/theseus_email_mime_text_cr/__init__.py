"""Clean-room email.mime.text subset for Theseus invariants."""


class MIMEText:
    def __init__(self, _text, _subtype="plain", _charset=None, *, policy=None):
        self._text = _text
        self._subtype = _subtype
        self._headers = {"Content-Type": "text/%s" % _subtype}

    def __setitem__(self, key, value):
        self._headers[key] = value

    def __getitem__(self, key):
        return self._headers[key]

    def get_content_type(self):
        return "text/%s" % self._subtype

    def as_string(self):
        headers = "\n".join("%s: %s" % (k, v) for k, v in self._headers.items())
        return headers + "\n\n" + self._text


def mimetext2_create():
    return MIMEText("Hello World").get_content_type() == "text/plain"


def mimetext2_html():
    return MIMEText("<p>hi</p>", "html").get_content_type() == "text/html"


def mimetext2_as_string():
    msg = MIMEText("Test message", "plain")
    msg["From"] = "test@example.com"
    msg["To"] = "recv@example.com"
    msg["Subject"] = "Test"
    s = msg.as_string()
    return "Content-Type: text/plain" in s and "Test message" in s


__all__ = ["MIMEText", "mimetext2_create", "mimetext2_html", "mimetext2_as_string"]
