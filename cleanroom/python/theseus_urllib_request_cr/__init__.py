"""Clean-room urllib.request subset for Theseus invariants."""


def _canon(name):
    return "-".join(part[:1].upper() + part[1:].lower() for part in name.split("-"))


class Request:
    def __init__(self, url, data=None, headers=None, origin_req_host=None, unverifiable=False, method=None):
        self.full_url = url
        self.data = data
        self.headers = {}
        self.method = method
        for key, value in (headers or {}).items():
            self.add_header(key, value)

    def get_method(self):
        return self.method or ("POST" if self.data is not None else "GET")

    def add_header(self, key, value):
        self.headers[_canon(key)] = value

    def get_header(self, header_name, default=None):
        return self.headers.get(_canon(header_name), default)


class OpenerDirector:
    pass


class BaseHandler:
    pass


HTTPHandler = HTTPSHandler = FileHandler = ProxyHandler = UnknownHandler = BaseHandler
HTTPErrorProcessor = HTTPRedirectHandler = HTTPDefaultErrorHandler = BaseHandler


def urlopen(*args, **kwargs):
    raise OSError("network access is not implemented")


def urlretrieve(*args, **kwargs):
    raise OSError("network access is not implemented")


def install_opener(opener):
    return None


def build_opener(*handlers):
    return OpenerDirector()


def pathname2url(pathname):
    return str(pathname).replace(" ", "%20")


def url2pathname(pathname):
    return str(pathname).replace("%20", " ")


def urllib_request2_request():
    r = Request("http://example.com/path", headers={"Accept": "text/html"})
    return r.full_url == "http://example.com/path" and r.get_method() == "GET"


def urllib_request2_add_header():
    r = Request("http://example.com/")
    r.add_header("User-Agent", "TestBot/1.0")
    r.add_header("Accept", "text/plain")
    return r.get_header("User-agent") == "TestBot/1.0"


def urllib_request2_pathname2url():
    return pathname2url("/usr/local/bin").startswith("/usr/local/bin")


__all__ = [
    "Request", "OpenerDirector", "BaseHandler", "HTTPHandler", "HTTPSHandler",
    "FileHandler", "ProxyHandler", "UnknownHandler", "pathname2url", "url2pathname",
    "urlopen", "urlretrieve", "install_opener", "build_opener",
    "urllib_request2_request", "urllib_request2_add_header", "urllib_request2_pathname2url",
]
