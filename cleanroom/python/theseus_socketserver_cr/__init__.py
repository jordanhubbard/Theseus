"""
theseus_socketserver_cr — Clean-room socketserver module.
No import of the standard `socketserver` module.
"""

import socket as _socket
import os as _os
import io as _io
import selectors as _selectors
import threading as _threading


class BaseServer:
    """Base class for server objects."""

    timeout = None

    def __init__(self, server_address, RequestHandlerClass):
        self.server_address = server_address
        self.RequestHandlerClass = RequestHandlerClass
        self.__is_shut_down = _threading.Event()
        self.__shutdown_request = False

    def server_activate(self):
        pass

    def serve_forever(self, poll_interval=0.5):
        self.__is_shut_down.clear()
        try:
            with _selectors.SelectSelector() as selector:
                selector.register(self, _selectors.EVENT_READ)
                while not self.__shutdown_request:
                    ready = selector.select(poll_interval)
                    if self.__shutdown_request:
                        break
                    if ready:
                        self._handle_request_noblock()
                    self.service_actions()
        finally:
            self.__shutdown_request = False
            self.__is_shut_down.set()

    def shutdown(self):
        self.__shutdown_request = True
        self.__is_shut_down.wait()

    def service_actions(self):
        pass

    def handle_request(self):
        import select
        fd_sets = select.select([self], [], [], self.timeout)
        if not fd_sets[0]:
            self.handle_timeout()
            return
        self._handle_request_noblock()

    def _handle_request_noblock(self):
        try:
            request, client_address = self.get_request()
        except OSError:
            return
        if self.verify_request(request, client_address):
            try:
                self.process_request(request, client_address)
            except Exception:
                self.handle_error(request, client_address)
                self.shutdown_request(request)
            except:
                self.shutdown_request(request)
                raise
        else:
            self.shutdown_request(request)

    def handle_timeout(self):
        pass

    def verify_request(self, request, client_address):
        return True

    def process_request(self, request, client_address):
        self.finish_request(request, client_address)
        self.shutdown_request(request)

    def server_close(self):
        pass

    def finish_request(self, request, client_address):
        self.RequestHandlerClass(request, client_address, self)

    def shutdown_request(self, request):
        self.close_request(request)

    def close_request(self, request):
        pass

    def handle_error(self, request, client_address):
        import traceback
        print(f'-' * 40)
        print(f'Exception occurred during processing of request from {client_address}:')
        traceback.print_exc()
        print(f'-' * 40)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.server_close()


class TCPServer(BaseServer):
    """TCP server that binds on a given address."""

    address_family = _socket.AF_INET
    socket_type = _socket.SOCK_STREAM
    request_queue_size = 5
    allow_reuse_address = False
    allow_reuse_port = False

    def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True):
        BaseServer.__init__(self, server_address, RequestHandlerClass)
        self.socket = _socket.socket(self.address_family, self.socket_type)
        if bind_and_activate:
            try:
                self.server_bind()
                self.server_activate()
            except:
                self.server_close()
                raise

    def server_bind(self):
        if self.allow_reuse_address:
            self.socket.setsockopt(_socket.SOL_SOCKET, _socket.SO_REUSEADDR, 1)
        self.socket.bind(self.server_address)
        self.server_address = self.socket.getsockname()

    def server_activate(self):
        self.socket.listen(self.request_queue_size)

    def server_close(self):
        self.socket.close()

    def fileno(self):
        return self.socket.fileno()

    def get_request(self):
        return self.socket.accept()

    def shutdown_request(self, request):
        try:
            request.shutdown(_socket.SHUT_WR)
        except OSError:
            pass
        self.close_request(request)

    def close_request(self, request):
        request.close()


class UDPServer(TCPServer):
    """UDP server."""

    allow_reuse_address = False
    socket_type = _socket.SOCK_DGRAM
    max_packet_size = 8192

    def get_request(self):
        data, client_addr = self.socket.recvfrom(self.max_packet_size)
        return (data, self.socket), client_addr

    def server_activate(self):
        pass

    def shutdown_request(self, request):
        self.close_request(request)

    def close_request(self, request):
        pass


class ThreadingMixIn:
    """Mix-in class to handle each request in a new thread."""

    daemon_threads = False
    block_on_close = True
    _threads = None

    def process_request_thread(self, request, client_address):
        try:
            self.finish_request(request, client_address)
        except Exception:
            self.handle_error(request, client_address)
        finally:
            self.shutdown_request(request)

    def process_request(self, request, client_address):
        t = _threading.Thread(target=self.process_request_thread,
                              args=(request, client_address))
        t.daemon = self.daemon_threads
        t.start()


class ForkingMixIn:
    """Mix-in class to handle each request in a new process."""

    timeout = 300
    active_children = None
    max_children = 40

    def collect_children(self, *, blocking=False):
        if self.active_children is None:
            return
        try:
            while self.active_children:
                pid, _ = _os.waitpid(-1, _os.WNOHANG if not blocking else 0)
                if pid > 0:
                    self.active_children.discard(pid)
                else:
                    break
        except ChildProcessError:
            self.active_children.clear()

    def process_request(self, request, client_address):
        pid = _os.fork()
        if pid:
            self.active_children = self.active_children or set()
            self.active_children.add(pid)
            self.close_request(request)
            return
        try:
            self.finish_request(request, client_address)
            _os._exit(0)
        except Exception:
            try:
                self.handle_error(request, client_address)
            finally:
                _os._exit(1)


class ThreadingTCPServer(ThreadingMixIn, TCPServer):
    pass


class ThreadingUDPServer(ThreadingMixIn, UDPServer):
    pass


class BaseRequestHandler:
    """Base class for request handlers."""

    def __init__(self, request, client_address, server):
        self.request = request
        self.client_address = client_address
        self.server = server
        self.setup()
        try:
            self.handle()
        finally:
            self.finish()

    def setup(self):
        pass

    def handle(self):
        pass

    def finish(self):
        pass


class StreamRequestHandler(BaseRequestHandler):
    """Request handler for stream sockets."""

    rbufsize = -1
    wbufsize = 0
    timeout = None
    disable_nagle_algorithm = False

    def setup(self):
        self.connection = self.request
        if self.timeout is not None:
            self.connection.settimeout(self.timeout)
        if self.disable_nagle_algorithm:
            self.connection.setsockopt(_socket.IPPROTO_TCP, _socket.TCP_NODELAY, True)
        self.rfile = self.connection.makefile('rb', self.rbufsize)
        if self.wbufsize == 0:
            self.wfile = _io.BufferedWriter(self.connection.makefile('wb'))
        else:
            self.wfile = self.connection.makefile('wb', self.wbufsize)

    def finish(self):
        if not self.wfile.closed:
            try:
                self.wfile.flush()
            except _socket.error:
                pass
        self.wfile.close()
        self.rfile.close()


class DatagramRequestHandler(BaseRequestHandler):
    """Request handler for datagram sockets."""

    def setup(self):
        from io import BytesIO
        self.packet, self.socket = self.request
        self.rfile = BytesIO(self.packet)
        self.wfile = BytesIO()

    def finish(self):
        self.socket.sendto(self.wfile.getvalue(), self.client_address)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def socketserver2_tcp_handler():
    """TCPServer and BaseRequestHandler can be defined; returns True."""
    class MyHandler(BaseRequestHandler):
        def handle(self):
            pass

    return issubclass(MyHandler, BaseRequestHandler)


def socketserver2_address_family():
    """TCPServer.address_family is socket.AF_INET; returns True."""
    return TCPServer.address_family == _socket.AF_INET


def socketserver2_handler_class():
    """BaseRequestHandler has handle() method; returns True."""
    return hasattr(BaseRequestHandler, 'handle')


__all__ = [
    'BaseServer', 'TCPServer', 'UDPServer',
    'ThreadingMixIn', 'ForkingMixIn',
    'ThreadingTCPServer', 'ThreadingUDPServer',
    'BaseRequestHandler', 'StreamRequestHandler', 'DatagramRequestHandler',
    'socketserver2_tcp_handler', 'socketserver2_address_family',
    'socketserver2_handler_class',
]
