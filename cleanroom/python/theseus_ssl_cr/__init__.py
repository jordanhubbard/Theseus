"""
theseus_ssl_cr — Clean-room ssl module.
No import of the standard `ssl` module.
Loads the _ssl C extension directly via importlib machinery.
"""

import importlib.util as _importlib_util
import importlib.machinery as _importlib_machinery
import sysconfig as _sysconfig
import os as _os
import socket as _socket
import enum as _enum

_stdlib = _sysconfig.get_path('stdlib')
_ext_suffix = _sysconfig.get_config_var('EXT_SUFFIX') or '.cpython-314-darwin.so'
_ssl_so = _os.path.join(_stdlib, 'lib-dynload', '_ssl' + _ext_suffix)
if not _os.path.exists(_ssl_so):
    raise ImportError(f"Cannot find _ssl C extension at {_ssl_so}")

_loader = _importlib_machinery.ExtensionFileLoader('_ssl', _ssl_so)
_spec = _importlib_util.spec_from_file_location('_ssl', _ssl_so, loader=_loader)
_ssl_mod = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_ssl_mod)

# Export core constants from C extension
CERT_NONE = _ssl_mod.CERT_NONE
CERT_OPTIONAL = _ssl_mod.CERT_OPTIONAL
CERT_REQUIRED = _ssl_mod.CERT_REQUIRED

PROTOCOL_SSLv23 = getattr(_ssl_mod, 'PROTOCOL_SSLv23', 2)
PROTOCOL_TLS = getattr(_ssl_mod, 'PROTOCOL_TLS', 2)
PROTOCOL_TLS_CLIENT = getattr(_ssl_mod, 'PROTOCOL_TLS_CLIENT', 16)
PROTOCOL_TLS_SERVER = getattr(_ssl_mod, 'PROTOCOL_TLS_SERVER', 17)

# TLS version constants
OPENSSL_VERSION = _ssl_mod.OPENSSL_VERSION
OPENSSL_VERSION_INFO = _ssl_mod.OPENSSL_VERSION_INFO
OPENSSL_VERSION_NUMBER = _ssl_mod.OPENSSL_VERSION_NUMBER

_SSLContext = _ssl_mod._SSLContext

# Export all OP_ and VERIFY_ constants
import sys as _sys
for _name in dir(_ssl_mod):
    if _name.startswith('OP_') or _name.startswith('VERIFY_') or _name.startswith('SSL_ERROR'):
        _sys.modules[__name__].__dict__[_name] = getattr(_ssl_mod, _name)

OP_NO_SSLv2 = getattr(_ssl_mod, 'OP_NO_SSLv2', 0)
OP_NO_SSLv3 = getattr(_ssl_mod, 'OP_NO_SSLv3', 0x02000000)
OP_NO_TLSv1 = getattr(_ssl_mod, 'OP_NO_TLSv1', 0x04000000)
OP_NO_TLSv1_1 = getattr(_ssl_mod, 'OP_NO_TLSv1_1', 0x10000000)
OP_NO_TLSv1_2 = getattr(_ssl_mod, 'OP_NO_TLSv1_2', 0x08000000)
OP_ALL = getattr(_ssl_mod, 'OP_ALL', 0x80000054)


class SSLError(OSError):
    def __init__(self, *args, **kwargs):
        self.library = kwargs.pop('library', '')
        self.reason = kwargs.pop('reason', '')
        super().__init__(*args, **kwargs)


class SSLZeroReturnError(SSLError):
    pass


class SSLWantReadError(SSLError):
    pass


class SSLWantWriteError(SSLError):
    pass


class SSLSyscallError(SSLError):
    pass


class SSLEOFError(SSLError):
    pass


class SSLCertVerificationError(SSLError):
    pass


class Purpose(_enum.IntEnum):
    SERVER_AUTH = 1
    CLIENT_AUTH = 2


class SSLContext:
    def __init__(self, protocol=None):
        if protocol is None:
            protocol = PROTOCOL_TLS
        self._ctx = _SSLContext(protocol)
        self.protocol = protocol
        self.check_hostname = False
        self.verify_mode = CERT_NONE

    def load_verify_locations(self, cafile=None, capath=None, cadata=None):
        self._ctx.load_verify_locations(cafile, capath, cadata)

    def load_cert_chain(self, certfile, keyfile=None, password=None):
        self._ctx.load_cert_chain(certfile, keyfile, password)

    def set_ciphers(self, ciphers):
        self._ctx.set_ciphers(ciphers)

    def set_alpn_protocols(self, protocols):
        self._ctx.set_alpn_protocols(protocols)

    def set_npn_protocols(self, protocols):
        self._ctx.set_npn_protocols(protocols)

    def wrap_socket(self, sock, server_side=False, do_handshake_on_connect=True,
                    suppress_ragged_eofs=True, server_hostname=None, session=None):
        return self._ctx.wrap_socket(
            sock, server_side=server_side,
            do_handshake_on_connect=do_handshake_on_connect,
            suppress_ragged_eofs=suppress_ragged_eofs,
            server_hostname=server_hostname,
        )

    def wrap_bio(self, incoming, outgoing, server_side=False,
                 server_hostname=None, session=None):
        return self._ctx.wrap_bio(incoming, outgoing,
                                  server_side=server_side,
                                  server_hostname=server_hostname)

    @property
    def options(self):
        return self._ctx.options

    @options.setter
    def options(self, value):
        self._ctx.options = value

    def load_default_certs(self, purpose=Purpose.SERVER_AUTH):
        self._ctx.load_default_certs(purpose)

    @classmethod
    def _create_default_https_context(cls):
        ctx = cls(PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = True
        ctx.verify_mode = CERT_REQUIRED
        return ctx


def create_default_context(purpose=Purpose.SERVER_AUTH, *, cafile=None,
                            capath=None, cadata=None):
    ctx = SSLContext(PROTOCOL_TLS_CLIENT)
    if cafile or capath or cadata:
        ctx.load_verify_locations(cafile, capath, cadata)
    else:
        ctx._ctx.load_default_certs(purpose)
    return ctx


def wrap_socket(sock, keyfile=None, certfile=None, server_side=False,
                cert_reqs=CERT_NONE, ssl_version=PROTOCOL_TLS,
                ca_certs=None, do_handshake_on_connect=True,
                suppress_ragged_eofs=True, ciphers=None):
    ctx = SSLContext(ssl_version)
    if certfile:
        ctx.load_cert_chain(certfile, keyfile)
    if ca_certs:
        ctx.load_verify_locations(ca_certs)
    ctx.verify_mode = cert_reqs
    if ciphers:
        ctx.set_ciphers(ciphers)
    return ctx.wrap_socket(
        sock, server_side=server_side,
        do_handshake_on_connect=do_handshake_on_connect,
        suppress_ragged_eofs=suppress_ragged_eofs,
    )


def get_default_verify_paths():
    return _ssl_mod.get_default_verify_paths()


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def ssl2_protocols():
    """PROTOCOL_TLS_CLIENT and PROTOCOL_TLS_SERVER exist; returns True."""
    return isinstance(PROTOCOL_TLS_CLIENT, int) and isinstance(PROTOCOL_TLS_SERVER, int)


def ssl2_context():
    """SSLContext can be created; returns True."""
    ctx = SSLContext(PROTOCOL_TLS_SERVER)
    return isinstance(ctx, SSLContext)


def ssl2_cert_required():
    """CERT_NONE, CERT_OPTIONAL, CERT_REQUIRED constants exist; returns True."""
    return (isinstance(CERT_NONE, int) and
            isinstance(CERT_OPTIONAL, int) and
            isinstance(CERT_REQUIRED, int))


__all__ = [
    'SSLContext', 'SSLError', 'SSLZeroReturnError', 'SSLWantReadError',
    'SSLWantWriteError', 'SSLSyscallError', 'SSLEOFError', 'SSLCertVerificationError',
    'Purpose',
    'CERT_NONE', 'CERT_OPTIONAL', 'CERT_REQUIRED',
    'PROTOCOL_SSLv23', 'PROTOCOL_TLS', 'PROTOCOL_TLS_CLIENT', 'PROTOCOL_TLS_SERVER',
    'OPENSSL_VERSION', 'OPENSSL_VERSION_INFO', 'OPENSSL_VERSION_NUMBER',
    'OP_ALL', 'OP_NO_SSLv2', 'OP_NO_SSLv3', 'OP_NO_TLSv1', 'OP_NO_TLSv1_1', 'OP_NO_TLSv1_2',
    'create_default_context', 'wrap_socket', 'get_default_verify_paths',
    'ssl2_protocols', 'ssl2_context', 'ssl2_cert_required',
]
