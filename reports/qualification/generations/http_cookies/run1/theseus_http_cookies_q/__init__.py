# generation A cookie scan

__all__ = ["SimpleCookie"]


def parse_cookie_header(header):
    if not header:
        return None, None
    text = header.strip()
    if "=" not in text:
        return None, None
    name, value = text.split("=", 1)
    name = name.strip()
    value = value.strip()
    if not name:
        return None, None
    return name, value


def format_set_cookie(name, value):
    return "Set-Cookie: " + name + "=" + value


class CookieJar(object):
    def __init__(self):
        self._name = None
        self._value = None

    def load_pair(self, name, value):
        self._name = name
        self._value = value

    def pair(self):
        return self._name, self._value


class SimpleCookie(object):
    def __init__(self, header=None):
        self._jar = CookieJar()
        if header is not None:
            name, value = parse_cookie_header(header)
            if name is not None:
                self._jar.load_pair(name, value)

    def output(self, *args, **kwargs):
        name, value = self._jar.pair()
        if name is None:
            return ""
        return format_set_cookie(name, value)
