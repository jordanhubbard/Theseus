"""Clean-room http.server subset for Theseus invariants."""

responses = {
    200: ("OK", "Request fulfilled"),
    301: ("Moved Permanently", "Object moved permanently"),
    302: ("Found", "Object moved temporarily"),
    400: ("Bad Request", "Bad request syntax"),
    403: ("Forbidden", "Request forbidden"),
    404: ("Not Found", "Nothing matches the given URI"),
    500: ("Internal Server Error", "Server got itself in trouble"),
}


class BaseHTTPRequestHandler:
    pass


class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    pass


class HTTPServer:
    pass


class ThreadingHTTPServer(HTTPServer):
    pass


def parse_request_line(requestline):
    parts = requestline.split()
    if len(parts) == 3:
        return tuple(parts)
    if len(parts) == 2:
        return parts[0], parts[1], "HTTP/0.9"
    raise ValueError("bad request line")


def http_server2_responses():
    return 200 in responses and 404 in responses and responses[200][0] == "OK" and responses[404][0] == "Not Found"


def http_server2_handler_exists():
    return isinstance(BaseHTTPRequestHandler, type)


def http_server2_parse_request():
    cmd, path, version = parse_request_line("GET /index.html HTTP/1.1")
    return cmd == "GET" and path == "/index.html" and version == "HTTP/1.1"


__all__ = [
    "BaseHTTPRequestHandler", "SimpleHTTPRequestHandler", "HTTPServer",
    "ThreadingHTTPServer", "responses", "parse_request_line",
    "http_server2_responses", "http_server2_handler_exists", "http_server2_parse_request",
]
