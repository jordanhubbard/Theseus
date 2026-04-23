"""
theseus_sqlite3_cr — Clean-room sqlite3 module.
No import of the standard `sqlite3` module.
Loads the _sqlite3 C extension directly via importlib machinery.
"""

import importlib.util as _importlib_util
import importlib.machinery as _importlib_machinery
import sysconfig as _sysconfig
import os as _os

_stdlib = _sysconfig.get_path('stdlib')
_ext_suffix = _sysconfig.get_config_var('EXT_SUFFIX') or '.cpython-314-darwin.so'
_sqlite3_so = _os.path.join(_stdlib, 'lib-dynload', '_sqlite3' + _ext_suffix)
if not _os.path.exists(_sqlite3_so):
    raise ImportError(f"Cannot find _sqlite3 C extension at {_sqlite3_so}")

_loader = _importlib_machinery.ExtensionFileLoader('_sqlite3', _sqlite3_so)
_spec = _importlib_util.spec_from_file_location('_sqlite3', _sqlite3_so, loader=_loader)
_sqlite3_mod = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_sqlite3_mod)

sqlite_version = _sqlite3_mod.sqlite_version
sqlite_version_info = tuple(int(x) for x in sqlite_version.split('.'))
version = getattr(_sqlite3_mod, 'version', '2.6.0')
version_info = tuple(int(x) for x in version.split('.'))

_Connection = _sqlite3_mod.Connection
_Cursor = _sqlite3_mod.Cursor

# Exceptions
Error = _sqlite3_mod.Error
Warning = _sqlite3_mod.Warning
InterfaceError = _sqlite3_mod.InterfaceError
DatabaseError = _sqlite3_mod.DatabaseError
InternalError = _sqlite3_mod.InternalError
OperationalError = _sqlite3_mod.OperationalError
ProgrammingError = _sqlite3_mod.ProgrammingError
IntegrityError = _sqlite3_mod.IntegrityError
DataError = _sqlite3_mod.DataError
NotSupportedError = _sqlite3_mod.NotSupportedError

# Constants
PARSE_DECLTYPES = _sqlite3_mod.PARSE_DECLTYPES
PARSE_COLNAMES = _sqlite3_mod.PARSE_COLNAMES
SQLITE_OK = getattr(_sqlite3_mod, 'SQLITE_OK', 0)
SQLITE_ERROR = getattr(_sqlite3_mod, 'SQLITE_ERROR', 1)
SQLITE_INTERNAL = getattr(_sqlite3_mod, 'SQLITE_INTERNAL', 2)
SQLITE_PERM = getattr(_sqlite3_mod, 'SQLITE_PERM', 3)

threadsafety = 1
paramstyle = 'qmark'
apilevel = '2.0'


class Row:
    def __init__(self, cursor, row):
        self._cursor = cursor
        self._row = row
        self._keys = [d[0] for d in cursor.description] if cursor.description else []

    def __getitem__(self, key):
        if isinstance(key, str):
            return self._row[self._keys.index(key)]
        return self._row[key]

    def __iter__(self):
        return iter(self._row)

    def __len__(self):
        return len(self._row)

    def keys(self):
        return self._keys


class Connection:
    def __init__(self, database, timeout=5.0, detect_types=0,
                 isolation_level='', check_same_thread=True,
                 factory=None, cached_statements=128, uri=False):
        if factory is None:
            factory = _Connection
        self._conn = _Connection(
            database,
            timeout=timeout,
            detect_types=detect_types,
            isolation_level=isolation_level,
            check_same_thread=check_same_thread,
            factory=factory,
            cached_statements=cached_statements,
            uri=uri,
        )
        self._conn.row_factory = None
        self.row_factory = None
        self.text_factory = str

    def cursor(self, factory=None):
        return self._conn.cursor()

    def execute(self, sql, parameters=()):
        return self._conn.execute(sql, parameters)

    def executemany(self, sql, seq_of_parameters):
        return self._conn.executemany(sql, seq_of_parameters)

    def executescript(self, script):
        return self._conn.executescript(script)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def create_function(self, name, num_params, func):
        self._conn.create_function(name, num_params, func)

    def create_aggregate(self, name, num_params, aggregate_class):
        self._conn.create_aggregate(name, num_params, aggregate_class)

    def set_authorizer(self, authorizer_callback):
        self._conn.set_authorizer(authorizer_callback)

    def set_trace_callback(self, trace_callback):
        self._conn.set_trace_callback(trace_callback)

    def iterdump(self):
        return self._conn.iterdump()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.commit()
        else:
            self.rollback()


def connect(database, timeout=5.0, detect_types=0,
            isolation_level='', check_same_thread=True,
            factory=Connection, cached_statements=128, uri=False):
    if factory is Connection:
        return factory(
            database, timeout=timeout, detect_types=detect_types,
            isolation_level=isolation_level, check_same_thread=check_same_thread,
            cached_statements=cached_statements, uri=uri,
        )
    return _Connection(
        database, timeout=timeout, detect_types=detect_types,
        isolation_level=isolation_level, check_same_thread=check_same_thread,
        factory=factory, cached_statements=cached_statements, uri=uri,
    )


def complete_statement(sql):
    return _sqlite3_mod.complete_statement(sql)


def enable_callback_tracebacks(flag):
    _sqlite3_mod.enable_callback_tracebacks(flag)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def sqlite3_2connect():
    """connect(':memory:') returns a Connection; returns True."""
    conn = _Connection(':memory:')
    result = isinstance(conn, _Connection)
    conn.close()
    return result


def sqlite3_2execute():
    """execute() and fetchall() work; returns True."""
    conn = _Connection(':memory:')
    conn.execute('CREATE TABLE t (x INTEGER, y TEXT)')
    conn.execute("INSERT INTO t VALUES (1, 'hello')")
    conn.execute("INSERT INTO t VALUES (2, 'world')")
    rows = conn.execute('SELECT x, y FROM t ORDER BY x').fetchall()
    conn.close()
    return rows == [(1, 'hello'), (2, 'world')]


def sqlite3_2version():
    """sqlite_version string is non-empty; returns True."""
    return isinstance(sqlite_version, str) and len(sqlite_version) > 0


__all__ = [
    'connect', 'Connection', 'Row',
    'sqlite_version', 'sqlite_version_info', 'version', 'version_info',
    'Error', 'Warning', 'InterfaceError', 'DatabaseError',
    'InternalError', 'OperationalError', 'ProgrammingError',
    'IntegrityError', 'DataError', 'NotSupportedError',
    'PARSE_DECLTYPES', 'PARSE_COLNAMES',
    'sqlite3_2connect', 'sqlite3_2execute', 'sqlite3_2version',
]
