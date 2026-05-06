"""Clean-room implementation of a minimal email.message-like module."""


class Message:
    """A minimal email message with headers and payload."""

    def __init__(self):
        self._headers = []  # list of (name, value) preserving order
        self._payload = None
        self._default_type = "text/plain"

    # ---- Header handling ----

    def __setitem__(self, name, value):
        self._headers.append((name, value))

    def __getitem__(self, name):
        lname = name.lower()
        for k, v in self._headers:
            if k.lower() == lname:
                return v
        return None

    def __delitem__(self, name):
        lname = name.lower()
        self._headers = [(k, v) for k, v in self._headers if k.lower() != lname]

    def __contains__(self, name):
        lname = name.lower()
        return any(k.lower() == lname for k, v in self._headers)

    def keys(self):
        return [k for k, v in self._headers]

    def values(self):
        return [v for k, v in self._headers]

    def items(self):
        return list(self._headers)

    def get(self, name, failobj=None):
        v = self[name]
        return failobj if v is None else v

    def get_all(self, name, failobj=None):
        lname = name.lower()
        result = [v for k, v in self._headers if k.lower() == lname]
        if not result:
            return failobj
        return result

    def add_header(self, name, value, **params):
        parts = [value]
        for k, v in params.items():
            k = k.replace("_", "-")
            if v is None:
                parts.append(k)
            else:
                parts.append('%s="%s"' % (k, v))
        self._headers.append((name, "; ".join(parts)))

    def replace_header(self, name, value):
        lname = name.lower()
        for i, (k, v) in enumerate(self._headers):
            if k.lower() == lname:
                self._headers[i] = (k, value)
                return
        raise KeyError(name)

    # ---- Payload handling ----

    def set_payload(self, payload, charset=None):
        self._payload = payload
        if charset is not None:
            self.set_charset(charset)

    def get_payload(self, i=None, decode=False):
        if i is None:
            return self._payload
        if isinstance(self._payload, list):
            return self._payload[i]
        raise TypeError("Expected list payload")

    def attach(self, payload):
        if self._payload is None:
            self._payload = [payload]
        elif isinstance(self._payload, list):
            self._payload.append(payload)
        else:
            raise TypeError("Cannot attach to non-multipart payload")

    def is_multipart(self):
        return isinstance(self._payload, list)

    # ---- Content type ----

    def set_type(self, type_, header="Content-Type"):
        del self[header]
        self[header] = type_

    def get_content_type(self):
        value = self["Content-Type"]
        if value is None:
            return self._default_type
        # parse the main/subtype
        main = value.split(";", 1)[0].strip().lower()
        if "/" in main:
            return main
        return self._default_type

    def get_content_maintype(self):
        return self.get_content_type().split("/", 1)[0]

    def get_content_subtype(self):
        ct = self.get_content_type()
        if "/" in ct:
            return ct.split("/", 1)[1]
        return ""

    def get_default_type(self):
        return self._default_type

    def set_default_type(self, ctype):
        self._default_type = ctype

    def get_params(self, failobj=None, header="Content-Type", unquote=True):
        value = self[header]
        if value is None:
            return failobj
        parts = [p.strip() for p in value.split(";")]
        result = []
        first = True
        for p in parts:
            if not p:
                continue
            if first:
                result.append((p, ""))
                first = False
                continue
            if "=" in p:
                k, v = p.split("=", 1)
                k = k.strip().lower()
                v = v.strip()
                if unquote and len(v) >= 2 and v[0] == '"' and v[-1] == '"':
                    v = v[1:-1]
                result.append((k, v))
            else:
                result.append((p.strip().lower(), ""))
        return result

    def get_param(self, param, failobj=None, header="Content-Type", unquote=True):
        params = self.get_params(failobj=None, header=header, unquote=unquote)
        if params is None:
            return failobj
        plower = param.lower()
        for k, v in params[1:]:
            if k == plower:
                return v
        return failobj

    def set_charset(self, charset):
        if "Content-Type" not in self:
            self["Content-Type"] = "text/plain; charset=%s" % charset
        else:
            value = self["Content-Type"]
            if "charset=" in value.lower():
                # leave as-is (simple approach)
                pass
            else:
                self.replace_header("Content-Type", value + "; charset=%s" % charset)

    def get_charset(self):
        return self.get_param("charset")


# ---- Invariant test functions ----

def emailmsg2_create():
    """Verify a Message can be created and headers set."""
    try:
        m = Message()
        m["From"] = "alice@example.com"
        m["To"] = "bob@example.com"
        m["Subject"] = "Hello"
        if m["From"] != "alice@example.com":
            return False
        if m["to"] != "bob@example.com":  # case-insensitive
            return False
        if m["Subject"] != "Hello":
            return False
        if "From" not in m:
            return False
        if "Cc" in m:
            return False
        keys = m.keys()
        if "From" not in keys or "To" not in keys or "Subject" not in keys:
            return False
        return True
    except Exception:
        return False


def emailmsg2_payload():
    """Verify payload set/get and multipart attach."""
    try:
        # Simple string payload
        m = Message()
        m.set_payload("Hello, world!")
        if m.get_payload() != "Hello, world!":
            return False
        if m.is_multipart():
            return False

        # Multipart payload via attach
        outer = Message()
        part1 = Message()
        part1.set_payload("part one")
        part2 = Message()
        part2.set_payload("part two")
        outer.attach(part1)
        outer.attach(part2)
        if not outer.is_multipart():
            return False
        if len(outer.get_payload()) != 2:
            return False
        if outer.get_payload(0).get_payload() != "part one":
            return False
        if outer.get_payload(1).get_payload() != "part two":
            return False
        return True
    except Exception:
        return False


def emailmsg2_content_type():
    """Verify content-type parsing and defaults."""
    try:
        # Default content type
        m = Message()
        if m.get_content_type() != "text/plain":
            return False
        if m.get_content_maintype() != "text":
            return False
        if m.get_content_subtype() != "plain":
            return False

        # Explicit content type with params
        m2 = Message()
        m2["Content-Type"] = 'text/html; charset="utf-8"'
        if m2.get_content_type() != "text/html":
            return False
        if m2.get_content_maintype() != "text":
            return False
        if m2.get_content_subtype() != "html":
            return False
        if m2.get_param("charset") != "utf-8":
            return False

        # Multipart
        m3 = Message()
        m3["Content-Type"] = "multipart/mixed; boundary=abc"
        if m3.get_content_type() != "multipart/mixed":
            return False
        if m3.get_param("boundary") != "abc":
            return False

        # set_type
        m4 = Message()
        m4.set_type("application/json")
        if m4.get_content_type() != "application/json":
            return False
        return True
    except Exception:
        return False