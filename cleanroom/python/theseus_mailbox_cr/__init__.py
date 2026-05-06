"""Clean-room implementation of a minimal mailbox module.

Provides Mailbox, Maildir, mbox, and Message classes without importing
the standard library's mailbox module.
"""

import os as _os
import io as _io
import time as _time


class Message:
    """Minimal mail message representation."""

    def __init__(self, message=None):
        self._headers = []
        self._payload = ""
        if message is None:
            return
        if isinstance(message, Message):
            self._headers = list(message._headers)
            self._payload = message._payload
        elif isinstance(message, str):
            self._parse(message)
        elif isinstance(message, bytes):
            self._parse(message.decode("latin-1"))
        elif hasattr(message, "read"):
            self._parse(message.read())

    def _parse(self, text):
        if isinstance(text, bytes):
            text = text.decode("latin-1")
        # Split headers from body
        sep_index = -1
        for sep in ("\r\n\r\n", "\n\n"):
            idx = text.find(sep)
            if idx != -1:
                sep_index = idx
                header_text = text[:idx]
                self._payload = text[idx + len(sep):]
                break
        if sep_index == -1:
            header_text = text
            self._payload = ""
        # Parse headers (handle continuation lines)
        lines = header_text.replace("\r\n", "\n").split("\n")
        current = None
        for line in lines:
            if not line:
                continue
            if line[0] in (" ", "\t") and current is not None:
                name, value = current
                current = (name, value + "\n" + line)
            else:
                if current is not None:
                    self._headers.append(current)
                colon = line.find(":")
                if colon == -1:
                    current = (line, "")
                else:
                    current = (line[:colon], line[colon + 1:].lstrip())
        if current is not None:
            self._headers.append(current)

    def __setitem__(self, name, value):
        self._headers.append((name, value))

    def __getitem__(self, name):
        lname = name.lower()
        for n, v in self._headers:
            if n.lower() == lname:
                return v
        return None

    def __delitem__(self, name):
        lname = name.lower()
        self._headers = [(n, v) for n, v in self._headers if n.lower() != lname]

    def __contains__(self, name):
        lname = name.lower()
        return any(n.lower() == lname for n, _ in self._headers)

    def get(self, name, default=None):
        result = self[name]
        return default if result is None else result

    def keys(self):
        return [n for n, _ in self._headers]

    def values(self):
        return [v for _, v in self._headers]

    def items(self):
        return list(self._headers)

    def get_payload(self):
        return self._payload

    def set_payload(self, payload):
        self._payload = payload

    def as_string(self):
        parts = []
        for n, v in self._headers:
            parts.append("%s: %s" % (n, v))
        parts.append("")
        parts.append(self._payload)
        return "\n".join(parts)

    def as_bytes(self):
        return self.as_string().encode("latin-1")

    def __str__(self):
        return self.as_string()


class Error(Exception):
    """Base class for mailbox-related exceptions."""
    pass


class NoSuchMailboxError(Error):
    pass


class NotEmptyError(Error):
    pass


class ExternalClashError(Error):
    pass


class FormatError(Error):
    pass


class Mailbox:
    """Base class for mailbox access."""

    def __init__(self, path, factory=None, create=True):
        self._path = _os.path.abspath(_os.path.expanduser(path))
        self._factory = factory
        self._create = create

    def add(self, message):
        raise NotImplementedError("Subclass must implement add")

    def remove(self, key):
        raise NotImplementedError("Subclass must implement remove")

    def __delitem__(self, key):
        self.remove(key)

    def discard(self, key):
        try:
            self.remove(key)
        except KeyError:
            pass

    def __setitem__(self, key, message):
        raise NotImplementedError("Subclass must implement __setitem__")

    def get(self, key, default=None):
        try:
            return self.__getitem__(key)
        except KeyError:
            return default

    def __getitem__(self, key):
        raise NotImplementedError("Subclass must implement __getitem__")

    def get_message(self, key):
        return self.__getitem__(key)

    def get_string(self, key):
        msg = self.__getitem__(key)
        if isinstance(msg, Message):
            return msg.as_string()
        return str(msg)

    def get_bytes(self, key):
        return self.get_string(key).encode("latin-1")

    def iterkeys(self):
        raise NotImplementedError("Subclass must implement iterkeys")

    def keys(self):
        return list(self.iterkeys())

    def itervalues(self):
        for key in self.iterkeys():
            try:
                yield self.__getitem__(key)
            except KeyError:
                continue

    def values(self):
        return list(self.itervalues())

    def __iter__(self):
        return self.itervalues()

    def iteritems(self):
        for key in self.iterkeys():
            try:
                yield key, self.__getitem__(key)
            except KeyError:
                continue

    def items(self):
        return list(self.iteritems())

    def __contains__(self, key):
        for k in self.iterkeys():
            if k == key:
                return True
        return False

    def __len__(self):
        return sum(1 for _ in self.iterkeys())

    def clear(self):
        for key in list(self.iterkeys()):
            self.discard(key)

    def pop(self, key, default=None):
        try:
            value = self.__getitem__(key)
        except KeyError:
            return default
        self.discard(key)
        return value

    def popitem(self):
        for key in self.iterkeys():
            value = self.__getitem__(key)
            self.discard(key)
            return key, value
        raise KeyError("Mailbox is empty")

    def update(self, arg=None):
        if arg is None:
            return
        if hasattr(arg, "items"):
            for k, v in arg.items():
                self.__setitem__(k, v)
        else:
            for k, v in arg:
                self.__setitem__(k, v)

    def flush(self):
        pass

    def lock(self):
        pass

    def unlock(self):
        pass

    def close(self):
        pass


class Maildir(Mailbox):
    """Maildir format mailbox."""

    SUBDIRS = ("tmp", "new", "cur")

    def __init__(self, dirname, factory=None, create=True):
        super().__init__(dirname, factory=factory, create=create)
        self._toc = {}
        self._counter = 0
        if not _os.path.exists(self._path):
            if create:
                _os.makedirs(self._path)
                for sub in self.SUBDIRS:
                    _os.mkdir(_os.path.join(self._path, sub))
            else:
                raise NoSuchMailboxError(self._path)
        else:
            for sub in self.SUBDIRS:
                p = _os.path.join(self._path, sub)
                if not _os.path.isdir(p):
                    if create:
                        _os.mkdir(p)
                    else:
                        raise NoSuchMailboxError(p)

    def _create_unique_name(self):
        self._counter += 1
        return "%d.%d_%d.%s" % (
            int(_time.time()),
            _os.getpid(),
            self._counter,
            "localhost",
        )

    def add(self, message):
        if isinstance(message, Message):
            data = message.as_string()
        elif isinstance(message, bytes):
            data = message.decode("latin-1")
        else:
            data = str(message)

        name = self._create_unique_name()
        tmp_path = _os.path.join(self._path, "tmp", name)
        new_path = _os.path.join(self._path, "new", name)
        with open(tmp_path, "w", encoding="latin-1") as f:
            f.write(data)
        _os.rename(tmp_path, new_path)
        self._toc[name] = _os.path.join("new", name)
        return name

    def remove(self, key):
        path = self._lookup(key)
        _os.remove(_os.path.join(self._path, path))
        if key in self._toc:
            del self._toc[key]

    def _refresh(self):
        self._toc = {}
        for sub in ("new", "cur"):
            d = _os.path.join(self._path, sub)
            if not _os.path.isdir(d):
                continue
            for entry in _os.listdir(d):
                if entry.startswith("."):
                    continue
                # Strip flags portion if present
                key = entry.split(":", 1)[0]
                self._toc[key] = _os.path.join(sub, entry)

    def _lookup(self, key):
        if key in self._toc:
            path = self._toc[key]
            if _os.path.exists(_os.path.join(self._path, path)):
                return path
        self._refresh()
        if key in self._toc:
            return self._toc[key]
        raise KeyError("No message with key %r" % key)

    def __getitem__(self, key):
        path = self._lookup(key)
        full = _os.path.join(self._path, path)
        with open(full, "r", encoding="latin-1") as f:
            data = f.read()
        if self._factory:
            return self._factory(_io.StringIO(data))
        return Message(data)

    def __setitem__(self, key, message):
        # Replace existing with new
        try:
            old_path = self._lookup(key)
            full_old = _os.path.join(self._path, old_path)
            if isinstance(message, Message):
                data = message.as_string()
            elif isinstance(message, bytes):
                data = message.decode("latin-1")
            else:
                data = str(message)
            with open(full_old, "w", encoding="latin-1") as f:
                f.write(data)
        except KeyError:
            # No existing message: place in new with given key
            new_path = _os.path.join(self._path, "new", key)
            if isinstance(message, Message):
                data = message.as_string()
            elif isinstance(message, bytes):
                data = message.decode("latin-1")
            else:
                data = str(message)
            with open(new_path, "w", encoding="latin-1") as f:
                f.write(data)
            self._toc[key] = _os.path.join("new", key)

    def iterkeys(self):
        self._refresh()
        for k in self._toc:
            yield k

    def list_folders(self):
        result = []
        for entry in _os.listdir(self._path):
            if entry.startswith(".") and entry not in (".", ".."):
                p = _os.path.join(self._path, entry)
                if _os.path.isdir(p):
                    result.append(entry[1:])
        return result

    def get_folder(self, folder):
        path = _os.path.join(self._path, "." + folder)
        if not _os.path.isdir(path):
            raise NoSuchMailboxError(path)
        return Maildir(path, factory=self._factory, create=False)

    def add_folder(self, folder):
        path = _os.path.join(self._path, "." + folder)
        return Maildir(path, factory=self._factory, create=True)


class _mboxMMDF(Mailbox):
    """Common base for mbox-style flat-file mailboxes."""

    _separator_prefix = "From "

    def __init__(self, path, factory=None, create=True):
        super().__init__(path, factory=factory, create=create)
        if not _os.path.exists(self._path):
            if create:
                # Create an empty file
                with open(self._path, "w", encoding="latin-1"):
                    pass
            else:
                raise NoSuchMailboxError(self._path)
        self._toc = None
        self._next_key = 0

    def _generate_toc(self):
        self._toc = {}
        if not _os.path.exists(self._path):
            return
        with open(self._path, "r", encoding="latin-1") as f:
            content = f.read()
        if not content:
            return
        lines = content.split("\n")
        starts = []
        for i, line in enumerate(lines):
            if line.startswith(self._separator_prefix) and (i == 0 or lines[i - 1] == ""):
                starts.append(i)
            elif i == 0 and line.startswith(self._separator_prefix):
                starts.append(i)
        # fallback: if first line is From and no entries grabbed
        if not starts and lines and lines[0].startswith(self._separator_prefix):
            starts = [0]
        for idx, start in enumerate(starts):
            end = starts[idx + 1] if idx + 1 < len(starts) else len(lines)
            self._toc[idx] = (start, end)
            self._next_key = idx + 1

    def _ensure_toc(self):
        if self._toc is None:
            self._generate_toc()

    def add(self, message):
        self._ensure_toc()
        if isinstance(message, Message):
            data = message.as_string()
        elif isinstance(message, bytes):
            data = message.decode("latin-1")
        else:
            data = str(message)
        from_line = "From MAILER-DAEMON %s" % _time.asctime(_time.gmtime())
        # Escape lines that begin with "From " in the body
        escaped_lines = []
        for line in data.split("\n"):
            if line.startswith("From "):
                escaped_lines.append(">" + line)
            else:
                escaped_lines.append(line)
        block = from_line + "\n" + "\n".join(escaped_lines)
        if not block.endswith("\n"):
            block += "\n"
        # Append to file with a blank line separator if needed
        with open(self._path, "a", encoding="latin-1") as f:
            if _os.path.getsize(self._path) > 0:
                f.write("\n")
            f.write(block)
        key = self._next_key
        self._next_key += 1
        # Force re-toc next access
        self._toc = None
        return key

    def remove(self, key):
        self._ensure_toc()
        if key not in self._toc:
            raise KeyError("No message with key %r" % key)
        with open(self._path, "r", encoding="latin-1") as f:
            lines = f.read().split("\n")
        start, end = self._toc[key]
        del lines[start:end]
        # Strip a leading blank line left over
        with open(self._path, "w", encoding="latin-1") as f:
            f.write("\n".join(lines))
        self._toc = None

    def __getitem__(self, key):
        self._ensure_toc()
        if key not in self._toc:
            raise KeyError("No message with key %r" % key)
        with open(self._path, "r", encoding="latin-1") as f:
            lines = f.read().split("\n")
        start, end = self._toc[key]
        # Skip the From_ separator line
        body_lines = lines[start + 1:end]
        # Unescape >From lines
        unescaped = []
        for line in body_lines:
            if line.startswith(">From "):
                unescaped.append(line[1:])
            else:
                unescaped.append(line)
        text = "\n".join(unescaped)
        if self._factory:
            return self._factory(_io.StringIO(text))
        return Message(text)

    def __setitem__(self, key, message):
        self.remove(key)
        new_key = self.add(message)
        # Note: keys may shift; not preserving exact key semantics
        return new_key

    def iterkeys(self):
        self._ensure_toc()
        for k in sorted(self._toc.keys()):
            yield k

    def __len__(self):
        self._ensure_toc()
        return len(self._toc)


class mbox(_mboxMMDF):
    """Unix mbox format mailbox."""
    _separator_prefix = "From "


class MMDF(_mboxMMDF):
    """MMDF format mailbox."""
    _separator_prefix = "\x01\x01\x01\x01"


# ----- Invariant probe functions -----

def mailbox2_message():
    """Verify Message construction and header/body parsing."""
    msg = Message("Subject: Hello\nFrom: a@b.com\n\nBody text here.")
    if msg["Subject"] != "Hello":
        return False
    if msg["From"] != "a@b.com":
        return False
    if "subject" not in msg:
        return False
    if msg.get_payload() != "Body text here.":
        return False
    msg2 = Message()
    msg2["X-Test"] = "value"
    msg2.set_payload("hi")
    if msg2["X-Test"] != "value":
        return False
    if "X-Test" not in msg2.keys():
        return False
    return True


def mailbox2_mbox_create():
    """Create an mbox, add a message, read it back, remove it."""
    import tempfile
    tmpdir = tempfile.mkdtemp(prefix="theseus_mbox_")
    try:
        path = _os.path.join(tmpdir, "test_mbox")
        box = mbox(path, create=True)
        if not _os.path.exists(path):
            return False
        msg = Message("Subject: Test\n\nHello from mbox.")
        key = box.add(msg)
        if key is None:
            return False
        if len(box) != 1:
            return False
        retrieved = box[key]
        if retrieved["Subject"] != "Test":
            return False
        if "Hello from mbox" not in retrieved.get_payload():
            return False
        # Add a second
        key2 = box.add(Message("Subject: Two\n\nSecond message."))
        if len(box) != 2:
            return False
        # Remove the first
        box.remove(key)
        if len(box) != 1:
            return False
        box.close()
        return True
    finally:
        try:
            for root, dirs, files in _os.walk(tmpdir, topdown=False):
                for f in files:
                    try:
                        _os.remove(_os.path.join(root, f))
                    except OSError:
                        pass
                for d in dirs:
                    try:
                        _os.rmdir(_os.path.join(root, d))
                    except OSError:
                        pass
            _os.rmdir(tmpdir)
        except OSError:
            pass


def mailbox2_maildir():
    """Create a Maildir, add a message, retrieve it, remove it."""
    import tempfile
    tmpdir = tempfile.mkdtemp(prefix="theseus_maildir_")
    try:
        path = _os.path.join(tmpdir, "test_maildir")
        box = Maildir(path, create=True)
        # Verify subdirs
        for sub in ("tmp", "new", "cur"):
            if not _os.path.isdir(_os.path.join(path, sub)):
                return False
        msg = Message("Subject: MD-Test\n\nHello from maildir.")
        key = box.add(msg)
        if not key:
            return False
        if len(box) != 1:
            return False
        retrieved = box[key]
        if retrieved["Subject"] != "MD-Test":
            return False
        if "Hello from maildir" not in retrieved.get_payload():
            return False
        # Iterate keys
        keys = list(box.iterkeys())
        if key not in keys:
            return False
        box.remove(key)
        if len(box) != 0:
            return False
        return True
    finally:
        try:
            for root, dirs, files in _os.walk(tmpdir, topdown=False):
                for f in files:
                    try:
                        _os.remove(_os.path.join(root, f))
                    except OSError:
                        pass
                for d in dirs:
                    try:
                        _os.rmdir(_os.path.join(root, d))
                    except OSError:
                        pass
            _os.rmdir(tmpdir)
        except OSError:
            pass