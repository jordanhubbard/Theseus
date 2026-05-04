"""Clean-room email.mime.multipart subset for Theseus invariants."""


class _TextPart:
    def __init__(self, text):
        self.text = text


class MIMEMultipart:
    def __init__(self, _subtype="mixed", boundary=None, _subparts=None, *, policy=None, **params):
        self._subtype = _subtype
        self._payload = list(_subparts or [])

    def get_content_type(self):
        return "multipart/%s" % self._subtype

    def attach(self, payload):
        self._payload.append(payload)

    def get_payload(self):
        return self._payload

    def as_string(self):
        return "Content-Type: %s\n\n%s part(s)" % (self.get_content_type(), len(self._payload))


def mimemultipart2_create():
    msg = MIMEMultipart()
    return isinstance(msg, MIMEMultipart) and msg.get_content_type() == "multipart/mixed"


def mimemultipart2_attach():
    msg = MIMEMultipart()
    msg.attach(_TextPart("hello"))
    payload = msg.get_payload()
    return isinstance(payload, list) and len(payload) == 1


def mimemultipart2_as_string():
    s = MIMEMultipart().as_string()
    return isinstance(s, str) and "multipart/mixed" in s


__all__ = [
    "MIMEMultipart", "mimemultipart2_create",
    "mimemultipart2_attach", "mimemultipart2_as_string",
]
