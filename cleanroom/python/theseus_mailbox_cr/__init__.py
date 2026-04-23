"""
theseus_mailbox_cr — Clean-room mailbox module.
No import of the standard `mailbox` module.
"""

import os as _os
import time as _time
import socket as _socket
import email as _email
import email.parser as _email_parser


class Message:
    """A message object."""

    def __init__(self, message=None):
        if message is None:
            self._data = b''
        elif isinstance(message, bytes):
            self._data = message
        elif isinstance(message, str):
            self._data = message.encode('utf-8', errors='replace')
        elif hasattr(message, 'as_bytes'):
            self._data = message.as_bytes()
        else:
            self._data = bytes(message)

    def as_bytes(self):
        return self._data

    def as_string(self):
        return self._data.decode('utf-8', errors='replace')

    def __bytes__(self):
        return self._data

    def __str__(self):
        return self.as_string()

    def get(self, key, default=None):
        parser = _email_parser.BytesParser()
        msg = parser.parsebytes(self._data)
        return msg.get(key, default)

    def __getitem__(self, key):
        result = self.get(key)
        if result is None:
            raise KeyError(key)
        return result


class Mailbox:
    """Base class for mailboxes."""

    def __init__(self, path, factory=None, create=True):
        self._path = _os.path.abspath(path)
        self._factory = factory or Message
        if create and not _os.path.exists(self._path):
            _os.makedirs(self._path, exist_ok=True)

    def add(self, message):
        raise NotImplementedError

    def remove(self, key):
        raise NotImplementedError

    def __delitem__(self, key):
        self.remove(key)

    def __len__(self):
        raise NotImplementedError

    def keys(self):
        raise NotImplementedError

    def __iter__(self):
        for key in self.keys():
            yield self[key]

    def __contains__(self, key):
        return key in self.keys()

    def close(self):
        pass

    def flush(self):
        pass


class mbox(Mailbox):
    """Mailbox in Unix mbox format."""

    def __init__(self, path, factory=None, create=True):
        self._path = _os.path.abspath(path)
        self._factory = factory or Message
        self._messages = []
        if create and not _os.path.exists(self._path):
            open(self._path, 'wb').close()
        elif _os.path.exists(self._path):
            self._parse()

    def _parse(self):
        self._messages = []
        try:
            with open(self._path, 'rb') as f:
                content = f.read()
        except OSError:
            return
        if not content:
            return
        lines = content.split(b'\n')
        current = []
        for line in lines:
            if line.startswith(b'From ') and current:
                self._messages.append(b'\n'.join(current))
                current = [line]
            else:
                current.append(line)
        if current:
            data = b'\n'.join(current)
            if data.strip():
                self._messages.append(data)

    def add(self, message):
        if isinstance(message, Message):
            data = message.as_bytes()
        elif isinstance(message, bytes):
            data = message
        elif isinstance(message, str):
            data = message.encode('utf-8', errors='replace')
        else:
            data = bytes(message)
        key = len(self._messages)
        from_line = b'From MAILER-DAEMON ' + _time.asctime().encode() + b'\n'
        full = from_line + data
        if not full.endswith(b'\n'):
            full += b'\n'
        self._messages.append(full)
        with open(self._path, 'ab') as f:
            f.write(full + b'\n')
        return key

    def remove(self, key):
        if 0 <= key < len(self._messages):
            self._messages[key] = None

    def __getitem__(self, key):
        if key < 0 or key >= len(self._messages):
            raise KeyError(key)
        data = self._messages[key]
        if data is None:
            raise KeyError(key)
        lines = data.split(b'\n')
        if lines and lines[0].startswith(b'From '):
            data = b'\n'.join(lines[1:])
        return self._factory(data)

    def __len__(self):
        return sum(1 for m in self._messages if m is not None)

    def keys(self):
        return [i for i, m in enumerate(self._messages) if m is not None]

    def flush(self):
        pass

    def close(self):
        pass


class Maildir(Mailbox):
    """Mailbox in Maildir format."""

    def __init__(self, path, factory=None, create=True):
        self._path = _os.path.abspath(path)
        self._factory = factory or Message
        if create:
            for sub in ('', 'new', 'cur', 'tmp'):
                _os.makedirs(_os.path.join(self._path, sub), exist_ok=True)

    def add(self, message):
        if isinstance(message, Message):
            data = message.as_bytes()
        elif isinstance(message, bytes):
            data = message
        elif isinstance(message, str):
            data = message.encode('utf-8', errors='replace')
        else:
            data = bytes(message)
        hostname = _socket.gethostname().replace('/', '\\057').replace(':', '\\072')
        uniq = f"{_time.time():.6f}.{_os.getpid()}.{hostname}"
        tmp_path = _os.path.join(self._path, 'tmp', uniq)
        new_path = _os.path.join(self._path, 'new', uniq)
        with open(tmp_path, 'wb') as f:
            f.write(data)
        _os.rename(tmp_path, new_path)
        return uniq

    def remove(self, key):
        for subdir in ('new', 'cur'):
            path = _os.path.join(self._path, subdir, key)
            if _os.path.exists(path):
                _os.remove(path)
                return
        raise KeyError(key)

    def __getitem__(self, key):
        for subdir in ('new', 'cur'):
            path = _os.path.join(self._path, subdir, key)
            if _os.path.exists(path):
                with open(path, 'rb') as f:
                    return self._factory(f.read())
        raise KeyError(key)

    def keys(self):
        result = []
        for subdir in ('new', 'cur'):
            d = _os.path.join(self._path, subdir)
            if _os.path.isdir(d):
                result.extend(_os.listdir(d))
        return result

    def __len__(self):
        return len(self.keys())

    def close(self):
        pass


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def mailbox2_mbox_create():
    """mbox mailbox can be created, messages added, len works; returns True."""
    import tempfile as _tempfile
    with _tempfile.NamedTemporaryFile(suffix='.mbox', delete=False) as f:
        path = f.name
    try:
        mb = mbox(path)
        mb.add(b'Subject: test\n\nHello world\n')
        mb.add(b'Subject: test2\n\nSecond message\n')
        result = len(mb) == 2
    finally:
        _os.unlink(path)
    return result


def mailbox2_message():
    """Message can be constructed from bytes and accessed; returns True."""
    msg = Message(b'Subject: hello\n\nBody text\n')
    return isinstance(msg.as_bytes(), bytes) and len(msg.as_bytes()) > 0


def mailbox2_maildir():
    """Maildir can be created and messages added; returns True."""
    import tempfile as _tempfile
    import shutil as _shutil
    d = _tempfile.mkdtemp()
    try:
        mb = Maildir(_os.path.join(d, 'test'))
        key = mb.add(b'Subject: maildir test\n\nHello\n')
        result = len(mb) == 1 and key is not None
    finally:
        _shutil.rmtree(d)
    return result


__all__ = [
    'Mailbox', 'mbox', 'Maildir', 'Message',
    'mailbox2_mbox_create', 'mailbox2_message', 'mailbox2_maildir',
]
