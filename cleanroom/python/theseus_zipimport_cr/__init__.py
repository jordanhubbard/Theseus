"""Clean-room reimplementation of zipimport functionality.

Provides a ZipImportError exception and a zipimporter class that can locate
modules inside ZIP archives. This implementation does not import the original
zipimport module; it parses the ZIP central directory directly using struct.
"""

import os
import sys
import struct
import marshal
import time


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------

class ZipImportError(ImportError):
    """Raised when a zipimporter cannot find or load a module."""
    pass


# ---------------------------------------------------------------------------
# Low-level ZIP parsing
# ---------------------------------------------------------------------------

# End of central directory record signature
_EOCD_SIG = b"PK\x05\x06"
# Central directory file header signature
_CDFH_SIG = b"PK\x01\x02"
# Local file header signature
_LFH_SIG = b"PK\x03\x04"

# Compression methods
_COMP_STORED = 0
_COMP_DEFLATED = 8


def _find_eocd(fp, file_size):
    """Locate the End of Central Directory record."""
    # Search from the end backwards (max comment length is 65535)
    max_comment = 65535
    search_size = min(file_size, max_comment + 22)
    fp.seek(file_size - search_size)
    data = fp.read(search_size)
    idx = data.rfind(_EOCD_SIG)
    if idx < 0:
        raise ZipImportError("not a Zip file")
    return data[idx:idx + 22], file_size - search_size + idx


def _read_central_directory(path):
    """Parse the ZIP central directory and return a dict of file info."""
    try:
        fp = open(path, "rb")
    except (OSError, IOError):
        raise ZipImportError("can't open Zip file: %r" % path)

    try:
        fp.seek(0, 2)  # end
        file_size = fp.tell()
        if file_size < 22:
            raise ZipImportError("not a Zip file: %r" % path)

        eocd, _ = _find_eocd(fp, file_size)
        # Parse EOCD
        # 4s signature, 2s disk_no, 2s disk_with_cd, 2s entries_on_disk,
        # 2s total_entries, 4s cd_size, 4s cd_offset, 2s comment_len
        (sig, _disk, _disk_cd, _ent_disk, total, cd_size, cd_offset,
         _comment_len) = struct.unpack("<4sHHHHIIH", eocd)

        fp.seek(cd_offset)
        cd_data = fp.read(cd_size)

        files = {}
        pos = 0
        for _ in range(total):
            if cd_data[pos:pos + 4] != _CDFH_SIG:
                raise ZipImportError("bad central directory in %r" % path)
            # Central directory file header is 46 bytes fixed
            header = cd_data[pos:pos + 46]
            (sig, _ver_made, _ver_needed, flags, method, mtime, mdate,
             crc, comp_size, uncomp_size, name_len, extra_len, comment_len,
             _disk_start, _int_attr, _ext_attr,
             local_header_offset) = struct.unpack("<4s6H3I5H2I", header)
            name = cd_data[pos + 46:pos + 46 + name_len]
            pos += 46 + name_len + extra_len + comment_len
            try:
                name = name.decode("utf-8")
            except UnicodeDecodeError:
                name = name.decode("latin-1")
            files[name] = (path, comp_size, uncomp_size, method,
                           mtime, mdate, crc, local_header_offset)
        return files
    finally:
        fp.close()


def _read_data(archive, info):
    """Read and decompress the data for a single zip entry."""
    (_path, comp_size, uncomp_size, method,
     _mtime, _mdate, _crc, local_offset) = info
    fp = open(archive, "rb")
    try:
        fp.seek(local_offset)
        lfh = fp.read(30)
        if lfh[:4] != _LFH_SIG:
            raise ZipImportError("bad local header in %r" % archive)
        # Skip name + extra of local header
        name_len = struct.unpack("<H", lfh[26:28])[0]
        extra_len = struct.unpack("<H", lfh[28:30])[0]
        fp.seek(local_offset + 30 + name_len + extra_len)
        raw = fp.read(comp_size)
    finally:
        fp.close()

    if method == _COMP_STORED:
        return raw
    elif method == _COMP_DEFLATED:
        # Use zlib via raw deflate
        try:
            import zlib
        except ImportError:
            raise ZipImportError("can't decompress data; zlib not available")
        decomp = zlib.decompressobj(-15)  # raw deflate
        return decomp.decompress(raw) + decomp.flush()
    else:
        raise ZipImportError("unsupported compression method %d" % method)


# ---------------------------------------------------------------------------
# zipimporter class
# ---------------------------------------------------------------------------

# Search order: try these path suffixes within the archive when locating a
# module. (suffix, is_package, is_bytecode)
_SEARCH_ORDER = [
    ("/__init__.pyc", True, True),
    ("/__init__.py", True, False),
    (".pyc", False, True),
    (".py", False, False),
]


class zipimporter:
    """Importer for modules stored inside a ZIP archive."""

    def __init__(self, path):
        if not isinstance(path, (str, bytes)):
            raise ZipImportError("archive path must be a string")
        if isinstance(path, bytes):
            try:
                path = path.decode(sys.getfilesystemencoding() or "utf-8")
            except UnicodeDecodeError:
                raise ZipImportError("invalid path bytes")

        # Walk up from `path` to find a real file (the archive). Anything left
        # over becomes the prefix inside the archive.
        if not path:
            raise ZipImportError("archive path is empty")

        archive = path
        prefix = ""
        while True:
            if os.path.isfile(archive):
                break
            parent = os.path.dirname(archive)
            if parent == archive or not parent:
                raise ZipImportError("not a Zip file: %r" % path)
            base = os.path.basename(archive)
            prefix = base + ("/" + prefix if prefix else "")
            archive = parent

        self.archive = archive
        # Normalize prefix: empty or ending with "/"
        if prefix and not prefix.endswith("/"):
            prefix = prefix + "/"
        self.prefix = prefix

        try:
            self._files = _read_central_directory(archive)
        except ZipImportError:
            raise
        except Exception as exc:
            raise ZipImportError("can't read Zip file %r: %s" % (archive, exc))

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _get_module_info(self, fullname):
        """Return (key, is_package, is_bytecode) or None if not found."""
        subname = fullname.rsplit(".", 1)[-1]
        path = self.prefix + subname
        for suffix, is_pkg, is_bc in _SEARCH_ORDER:
            key = path + suffix
            if key in self._files:
                return key, is_pkg, is_bc
        return None

    # ------------------------------------------------------------------
    # Public API (PEP 302 / importlib.abc.Loader-ish)
    # ------------------------------------------------------------------

    def find_module(self, fullname, path=None):
        """Return self if `fullname` can be loaded, else None."""
        info = self._get_module_info(fullname)
        if info is not None:
            return self
        return None

    def find_loader(self, fullname, path=None):
        info = self._get_module_info(fullname)
        if info is None:
            return None, []
        _key, is_pkg, _is_bc = info
        if is_pkg:
            portions = [self.archive + os.sep + self.prefix +
                        fullname.rsplit(".", 1)[-1]]
            return self, portions
        return self, []

    def is_package(self, fullname):
        info = self._get_module_info(fullname)
        if info is None:
            raise ZipImportError("can't find module %r" % fullname)
        return info[1]

    def get_data(self, pathname):
        # Strip archive path prefix if present
        if pathname.startswith(self.archive):
            key = pathname[len(self.archive):].lstrip(os.sep).lstrip("/")
        else:
            key = pathname
        key = key.replace(os.sep, "/")
        if key in self._files:
            return _read_data(self.archive, self._files[key])
        raise OSError("file not found in zip: %r" % pathname)

    def get_source(self, fullname):
        info = self._get_module_info(fullname)
        if info is None:
            raise ZipImportError("can't find module %r" % fullname)
        key, is_pkg, _is_bc = info
        # Prefer .py source if available
        subname = fullname.rsplit(".", 1)[-1]
        candidates = []
        if is_pkg:
            candidates.append(self.prefix + subname + "/__init__.py")
        else:
            candidates.append(self.prefix + subname + ".py")
        for cand in candidates:
            if cand in self._files:
                data = _read_data(self.archive, self._files[cand])
                try:
                    return data.decode("utf-8")
                except UnicodeDecodeError:
                    return data.decode("latin-1")
        return None

    def get_code(self, fullname):
        info = self._get_module_info(fullname)
        if info is None:
            raise ZipImportError("can't find module %r" % fullname)
        key, is_pkg, is_bc = info
        if is_bc:
            data = _read_data(self.archive, self._files[key])
            # Skip the .pyc header (16 bytes for Python 3.7+)
            return marshal.loads(data[16:])
        else:
            src = self.get_source(fullname)
            if src is None:
                raise ZipImportError("can't get source for %r" % fullname)
            filename = self.archive + os.sep + key
            return compile(src, filename, "exec", dont_inherit=True)

    def get_filename(self, fullname):
        info = self._get_module_info(fullname)
        if info is None:
            raise ZipImportError("can't find module %r" % fullname)
        key, _is_pkg, _is_bc = info
        return self.archive + os.sep + key.replace("/", os.sep)

    def load_module(self, fullname):
        """Load and return the module named `fullname` (legacy PEP 302)."""
        info = self._get_module_info(fullname)
        if info is None:
            raise ZipImportError("can't find module %r" % fullname)
        key, is_pkg, _is_bc = info
        code = self.get_code(fullname)

        # Reuse existing module if present (per PEP 302)
        mod = sys.modules.get(fullname)
        if mod is None:
            import types
            mod = types.ModuleType(fullname)
            sys.modules[fullname] = mod
        mod.__loader__ = self
        mod.__file__ = self.get_filename(fullname)
        if is_pkg:
            mod.__path__ = [self.archive + os.sep +
                            self.prefix +
                            fullname.rsplit(".", 1)[-1]]
            mod.__package__ = fullname
        else:
            mod.__package__ = fullname.rpartition(".")[0]
        try:
            exec(code, mod.__dict__)
        except BaseException:
            sys.modules.pop(fullname, None)
            raise
        return sys.modules[fullname]

    def __repr__(self):
        if self.prefix:
            return "<zipimporter object %r>" % (
                self.archive + os.sep + self.prefix)
        return "<zipimporter object %r>" % self.archive


# ---------------------------------------------------------------------------
# path-hook style helper
# ---------------------------------------------------------------------------

# A small cache to mirror zipimport._zip_directory_cache
_zip_directory_cache = {}


def _path_hook(path):
    """Return a zipimporter for `path` if appropriate."""
    return zipimporter(path)


# ---------------------------------------------------------------------------
# Invariant entry points
# ---------------------------------------------------------------------------

def zipimport2_error():
    """Verify that ZipImportError is defined and behaves as an ImportError."""
    if not isinstance(ZipImportError, type):
        return False
    if not issubclass(ZipImportError, ImportError):
        return False
    try:
        raise ZipImportError("test")
    except ZipImportError as exc:
        if str(exc) != "test":
            return False
    except Exception:
        return False
    return True


def zipimport2_importer():
    """Verify that the zipimporter class exists and rejects bad input."""
    if not isinstance(zipimporter, type):
        return False
    # Constructor should refuse a non-string argument.
    try:
        zipimporter(12345)
    except ZipImportError:
        pass
    except Exception:
        return False
    else:
        return False
    # Constructor should refuse a path that does not exist.
    try:
        zipimporter("/this/path/should/never/exist/__nope__.zip")
    except ZipImportError:
        pass
    except Exception:
        return False
    else:
        return False
    # Required attributes / methods
    for attr in ("find_module", "get_code", "get_data", "get_source",
                 "is_package", "load_module", "get_filename"):
        if not hasattr(zipimporter, attr):
            return False
    return True


def zipimport2_find():
    """Verify the find logic by building a tiny in-memory zip and querying it."""
    import tempfile
    import zlib

    # Build a minimal ZIP file with a single stored entry: "mod.py"
    name = b"mod.py"
    content = b"value = 42\n"
    crc = zlib.crc32(content) & 0xFFFFFFFF

    # Local file header
    lfh = struct.pack(
        "<4s5H3I2H",
        _LFH_SIG, 20, 0, 0, 0, 0,
        crc, len(content), len(content),
        len(name), 0,
    )
    local_offset = 0
    local = lfh + name + content

    # Central directory file header
    cdfh = struct.pack(
        "<4s6H3I5H2I",
        _CDFH_SIG, 20, 20, 0, 0, 0, 0,
        crc, len(content), len(content),
        len(name), 0, 0,
        0, 0, 0,
        local_offset,
    ) + name
    cd_offset = len(local)
    cd_size = len(cdfh)

    eocd = struct.pack(
        "<4sHHHHIIH",
        _EOCD_SIG, 0, 0, 1, 1,
        cd_size, cd_offset, 0,
    )

    blob = local + cdfh + eocd

    fd, path = tempfile.mkstemp(suffix=".zip")
    try:
        os.write(fd, blob)
        os.close(fd)

        imp = zipimporter(path)
        if imp.find_module("mod") is not imp:
            return False
        if imp.find_module("does_not_exist") is not None:
            return False
        if imp.is_package("mod"):
            return False
        src = imp.get_source("mod")
        if src is None or "value = 42" not in src:
            return False
        # get_data round-trip
        data = imp.get_data(path + os.sep + "mod.py")
        if data != content:
            return False
        # get_filename should reference the archive
        fn = imp.get_filename("mod")
        if not fn.startswith(path):
            return False
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
    return True


__all__ = [
    "ZipImportError",
    "zipimporter",
    "zipimport2_error",
    "zipimport2_importer",
    "zipimport2_find",
]