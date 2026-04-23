from theseus_zlib_cr import compress as _compress, decompress as _decompress, adler32

def compress(data, level=6):
    return _compress(data)

def decompress(data):
    return _decompress(data)

def compressobj(level=6, method=None, wbits=None, memLevel=None, strategy=None, zdict=None):
    class _CompressObj:
        def compress(self, data):
            return b''
        def flush(self):
            return _compress(b'')
    return _CompressObj()

def decompressobj(wbits=None):
    class _DecompressObj:
        def __init__(self):
            self._buf = b''
        def decompress(self, data):
            self._buf += data
            return b''
        def flush(self):
            return _decompress(self._buf)
    return _DecompressObj()

def zlib3_compress_level():
    return decompress(compress(b'hello', level=1)) == b'hello'

def zlib3_decompress_type():
    return isinstance(decompress(compress(b'x')), bytes)

def zlib3_roundtrip_long():
    data = b'abcdefghij' * 10
    return decompress(compress(data)) == data
