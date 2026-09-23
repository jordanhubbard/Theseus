# generation B cookie class

__all__ = ["SimpleCookie"]


class _Cookie:
    def __init__(self, header):
        name, separator, value = header.partition("=")
        if not separator or not name.strip():
            raise ValueError("cookie header must contain one name=value pair")
        self.name = name.strip()
        self.value = value.strip()

    def output(self):
        return "Set-Cookie: {0}={1}".format(self.name, self.value)


SimpleCookie = _Cookie
