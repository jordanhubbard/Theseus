"""Clean-room subset of xdrlib."""

import struct


class Error(Exception):
    def __init__(self, msg):
        self.msg = msg
        Exception.__init__(self, msg)


class ConversionError(Error):
    pass


class Packer(object):
    def __init__(self):
        self.reset()

    def reset(self):
        self._buf = bytearray()

    def get_buffer(self):
        return bytes(self._buf)

    def get_buf(self):
        return self.get_buffer()

    def pack_uint(self, value):
        value = int(value)
        if not 0 <= value <= 0xffffffff:
            raise ConversionError("unsigned integer out of range")
        self._buf.extend(value.to_bytes(4, "big", signed=False))

    def pack_int(self, value):
        value = int(value)
        if not -(2 ** 31) <= value <= 2 ** 31 - 1:
            raise ConversionError("integer out of range")
        self._buf.extend(value.to_bytes(4, "big", signed=True))

    def pack_enum(self, value):
        self.pack_int(value)

    def pack_bool(self, value):
        self.pack_uint(1 if value else 0)

    def pack_uhyper(self, value):
        value = int(value)
        if not 0 <= value <= 0xffffffffffffffff:
            raise ConversionError("unsigned hyper integer out of range")
        self._buf.extend(value.to_bytes(8, "big", signed=False))

    def pack_hyper(self, value):
        value = int(value)
        if not -(2 ** 63) <= value <= 2 ** 63 - 1:
            raise ConversionError("hyper integer out of range")
        self._buf.extend(value.to_bytes(8, "big", signed=True))

    def pack_float(self, value):
        self._buf.extend(struct.pack(">f", float(value)))

    def pack_double(self, value):
        self._buf.extend(struct.pack(">d", float(value)))

    def pack_fstring(self, n, data):
        data = _bytes(data)
        if len(data) != n:
            data = data[:n].ljust(n, b"\0")
        self._buf.extend(data)
        self._buf.extend(b"\0" * _padding(n))

    def pack_fopaque(self, n, data):
        self.pack_fstring(n, data)

    def pack_string(self, data):
        data = _bytes(data)
        self.pack_uint(len(data))
        self.pack_fstring(len(data), data)

    def pack_opaque(self, data):
        self.pack_string(data)

    def pack_bytes(self, data):
        self.pack_string(data)

    def pack_list(self, values, pack_item):
        for value in values:
            self.pack_uint(1)
            pack_item(value)
        self.pack_uint(0)

    def pack_farray(self, n, values, pack_item):
        if len(values) != n:
            raise ValueError("wrong array size")
        for value in values:
            pack_item(value)

    def pack_array(self, values, pack_item):
        self.pack_uint(len(values))
        self.pack_farray(len(values), values, pack_item)


class Unpacker(object):
    def __init__(self, data):
        self.reset(data)

    def reset(self, data):
        self._buf = _bytes(data)
        self._pos = 0

    def get_position(self):
        return self._pos

    def set_position(self, position):
        if not 0 <= position <= len(self._buf):
            raise Error("position out of range")
        self._pos = position

    def get_buffer(self):
        return self._buf

    def done(self):
        if self._pos != len(self._buf):
            raise Error("unextracted data remains")

    def _read(self, n):
        end = self._pos + n
        if end > len(self._buf):
            raise EOFError("not enough data to unpack")
        data = self._buf[self._pos:end]
        self._pos = end
        return data

    def unpack_uint(self):
        return int.from_bytes(self._read(4), "big", signed=False)

    def unpack_int(self):
        return int.from_bytes(self._read(4), "big", signed=True)

    def unpack_enum(self):
        return self.unpack_int()

    def unpack_bool(self):
        return bool(self.unpack_uint())

    def unpack_uhyper(self):
        return int.from_bytes(self._read(8), "big", signed=False)

    def unpack_hyper(self):
        return int.from_bytes(self._read(8), "big", signed=True)

    def unpack_float(self):
        return struct.unpack(">f", self._read(4))[0]

    def unpack_double(self):
        return struct.unpack(">d", self._read(8))[0]

    def unpack_fstring(self, n):
        data = self._read(n)
        pad = _padding(n)
        if pad:
            self._read(pad)
        return data

    def unpack_fopaque(self, n):
        return self.unpack_fstring(n)

    def unpack_string(self):
        return self.unpack_fstring(self.unpack_uint())

    def unpack_opaque(self):
        return self.unpack_string()

    def unpack_bytes(self):
        return self.unpack_string()

    def unpack_list(self, unpack_item):
        values = []
        while True:
            present = self.unpack_uint()
            if present == 0:
                return values
            values.append(unpack_item())

    def unpack_farray(self, n, unpack_item):
        return [unpack_item() for _ in range(n)]

    def unpack_array(self, unpack_item):
        return self.unpack_farray(self.unpack_uint(), unpack_item)


def _bytes(value):
    if isinstance(value, bytes):
        return value
    if isinstance(value, bytearray):
        return bytes(value)
    if isinstance(value, str):
        return value.encode("utf-8")
    return bytes(value)


def _padding(n):
    return (-n) % 4


def xdrlib_uint_roundtrip():
    packer = Packer()
    packer.pack_uint(7)
    unpacker = Unpacker(packer.get_buffer())
    ok = unpacker.unpack_uint() == 7
    unpacker.done()
    return ok


def xdrlib_string_roundtrip():
    packer = Packer()
    packer.pack_string(b"abc")
    unpacker = Unpacker(packer.get_buffer())
    ok = unpacker.unpack_string() == b"abc"
    unpacker.done()
    return ok


def xdrlib_array_roundtrip():
    packer = Packer()
    packer.pack_array([1, 2, 3], packer.pack_int)
    unpacker = Unpacker(packer.get_buffer())
    result = unpacker.unpack_array(unpacker.unpack_int)
    unpacker.done()
    return result


def xdrlib_error_msg():
    return Error("bad").msg == "bad"
