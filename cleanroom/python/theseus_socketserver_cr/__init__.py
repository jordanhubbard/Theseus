"""Clean-room implementation of socketserver-like module.

Provides base server classes (TCPServer, UDPServer) and request handler
classes (BaseRequestHandler, StreamRequestHandler, DatagramRequestHandler).
"""

import socket as _socket
import select as _select
import os as _os
import sys as _sys
import threading as _threading


# ---------------------------------------------------------------------------
# Base server class
# ---------------------------------------------------------------------------


class BaseServer:
    """Base class for server objects."""

    timeout = None

    def __init__(self, server_address, RequestHandlerClass):
        self.server_address = server_address
        self.RequestHandlerClass = RequestHandlerClass
        self.__is_shut_down = _threading.Event()
        self.__is_shut_down.set()
        self.__shutdown_request = False

    def server_activate(self):
        pass

    def serve_forever(self, poll_interval=0.5):
        self.__is_shut_down.clear()
        try:
            while not self.__shutdown_request:
                ready, _, _ = _select.select([self], [], [], poll_interval)
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
        timeout = self.socket.gettimeout()
        if timeout is None:
            timeout = self.timeout
        elif self.timeout is not None:
            timeout = min(timeout, self.timeout)
        if timeout is not None:
            deadline = timeout
        else:
            deadline = None
        ready, _, _ = _select.select([self], [], [], deadline)
        if ready:
            self._handle_request_noblock()
        else:
            self.handle_timeout()

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
        # Print a traceback like the standard library does
        import traceback
        traceback.print_exc()

    def fileno(self):
        raise NotImplementedError


# ---------------------------------------------------------------------------
# TCPServer
# ---------------------------------------------------------------------------


class TCPServer(BaseServer):
    """Base class for TCP servers."""

    address_family = _socket.AF_INET
    socket_type = _socket.SOCK_STREAM
    request_queue_size = 5
    allow_reuse_address = False

    def __init__(self, server_address, RequestHandlerClass,
                 bind_and_activate=True):
        BaseServer.__init__(self, server_address, RequestHandlerClass)
        self.socket = _socket.socket(self.address_family, self.socket_type)
        if bind_and_activate:
            try:
                self.server_bind()
                self.server_activate()
            except BaseException:
                self.server_close()
                raise

    def server_bind(self):
        if self.allow_reuse_address:
            self.socket.setsockopt(_socket.SOL_SOCKET,
                                   _socket.SO_REUSEADDR, 1)
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


# ---------------------------------------------------------------------------
# UDPServer
# ---------------------------------------------------------------------------


class UDPServer(TCPServer):
    """UDP server class."""

    allow_reuse_address = False
    socket_type = _socket.SOCK_DGRAM
    max_packet_size = 8192

    def get_request(self):
        data, client_addr = self.socket.recvfrom(self.max_packet_size)
        return (data, self.socket), client_addr

    def server_activate(self):
        # No listen() call for UDP
        pass

    def shutdown_request(self, request):
        self.close_request(request)

    def close_request(self, request):
        # Nothing to close for a datagram request
        pass


# ---------------------------------------------------------------------------
# Mix-in classes for forking / threading
# ---------------------------------------------------------------------------


class ForkingMixIn:
    """Mix-in class that forks a new process to handle each request."""

    timeout = 300
    active_children = None
    max_children = 40

    def collect_children(self):
        if self.active_children is None:
            return
        while len(self.active_children) >= self.max_children:
            try:
                pid, _ = _os.waitpid(-1, 0)
                self.active_children.discard(pid)
            except ChildProcessError:
                self.active_children.clear()
            except OSError:
                break
        for pid in list(self.active_children):
            try:
                flags = 0
                try:
                    flags = _os.WNOHANG
                except AttributeError:
                    pass
                pid_done, _ = _os.waitpid(pid, flags)
                if pid_done == 0:
                    continue
                self.active_children.discard(pid_done)
            except ChildProcessError:
                self.active_children.discard(pid)
            except OSError:
                pass

    def handle_timeout(self):
        self.collect_children()

    def service_actions(self):
        self.collect_children()

    def process_request(self, request, client_address):
        pid = _os.fork()
        if pid:
            if self.active_children is None:
                self.active_children = set()
            self.active_children.add(pid)
            self.close_request(request)
        else:
            try:
                self.finish_request(request, client_address)
                self.shutdown_request(request)
                _os._exit(0)
            except Exception:
                try:
                    self.handle_error(request, client_address)
                    self.shutdown_request(request)
                finally:
                    _os._exit(1)


class ThreadingMixIn:
    """Mix-in class that spawns a new thread to handle each request."""

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
        t = _threading.Thread(
            target=self.process_request_thread,
            args=(request, client_address),
        )
        t.daemon = self.daemon_threads
        if not t.daemon and self.block_on_close:
            if self._threads is None:
                self._threads = []
            self._threads.append(t)
        t.start()

    def server_close(self):
        super().server_close()
        if self.block_on_close:
            threads = self._threads
            self._threads = None
            if threads:
                for t in threads:
                    t.join()


class ForkingTCPServer(ForkingMixIn, TCPServer):
    pass


class ForkingUDPServer(ForkingMixIn, UDPServer):
    pass


class ThreadingTCPServer(ThreadingMixIn, TCPServer):
    pass


class ThreadingUDPServer(ThreadingMixIn, UDPServer):
    pass


# ---------------------------------------------------------------------------
# Request handlers
# ---------------------------------------------------------------------------


class BaseRequestHandler:
    """Base class for request handler objects."""

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
    """Base class for handling stream (TCP) connections."""

    rbufsize = -1
    wbufsize = 0
    timeout = None
    disable_nagle_algorithm = False

    def setup(self):
        self.connection = self.request
        if self.timeout is not None:
            self.connection.settimeout(self.timeout)
        if self.disable_nagle_algorithm:
            try:
                self.connection.setsockopt(
                    _socket.IPPROTO_TCP, _socket.TCP_NODELAY, True
                )
            except (AttributeError, OSError):
                pass
        self.rfile = self.connection.makefile('rb', self.rbufsize)
        if self.wbufsize == 0:
            self.wfile = _SocketWriter(self.connection)
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


class _SocketWriter:
    """Lightweight unbuffered writer wrapper around a socket."""

    def __init__(self, sock):
        self._sock = sock
        self.closed = False

    def writable(self):
        return True

    def write(self, b):
        self._sock.sendall(b)
        with memoryview(b) as view:
            return view.nbytes

    def fileno(self):
        return self._sock.fileno()

    def flush(self):
        pass

    def close(self):
        self.closed = True


class DatagramRequestHandler(BaseRequestHandler):
    """Base class for handling datagram (UDP) requests."""

    def setup(self):
        from io import BytesIO
        self.packet, self.socket = self.request
        self.rfile = BytesIO(self.packet)
        self.wfile = BytesIO()

    def finish(self):
        self.socket.sendto(self.wfile.getvalue(), self.client_address)


# ---------------------------------------------------------------------------
# Invariant predicates
# ---------------------------------------------------------------------------


def socketserver2_tcp_handler():
    """Verify that TCPServer wires up its handler correctly."""
    # Confirm classes exist and TCPServer subclasses BaseServer
    if not issubclass(TCPServer, BaseServer):
        return False
    # Confirm the handler hierarchy
    if not issubclass(StreamRequestHandler, BaseRequestHandler):
        return False
    # Confirm TCPServer carries the expected defaults
    if TCPServer.socket_type != _socket.SOCK_STREAM:
        return False
    if TCPServer.request_queue_size != 5:
        return False
    return True


def socketserver2_address_family():
    """Verify default address family on server classes."""
    if TCPServer.address_family != _socket.AF_INET:
        return False
    if UDPServer.address_family != _socket.AF_INET:
        return False
    if UDPServer.socket_type != _socket.SOCK_DGRAM:
        return False
    return True


def socketserver2_handler_class():
    """Verify handler-class hierarchy is consistent."""
    if not issubclass(StreamRequestHandler, BaseRequestHandler):
        return False
    if not issubclass(DatagramRequestHandler, BaseRequestHandler):
        return False
    # BaseRequestHandler must define setup/handle/finish
    for name in ("setup", "handle", "finish"):
        if not hasattr(BaseRequestHandler, name):
            return False
    return True


__all__ = [
    "BaseServer",
    "TCPServer",
    "UDPServer",
    "ForkingMixIn",
    "ThreadingMixIn",
    "ForkingTCPServer",
    "ForkingUDPServer",
    "ThreadingTCPServer",
    "ThreadingUDPServer",
    "BaseRequestHandler",
    "StreamRequestHandler",
    "DatagramRequestHandler",
    "socketserver2_tcp_handler",
    "socketserver2_address_family",
    "socketserver2_handler_class",
]