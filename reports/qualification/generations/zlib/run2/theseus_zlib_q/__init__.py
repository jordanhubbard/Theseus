# generation B crc class

__all__ = ["crc32"]


class _Crc:
    _POLYNOMIAL = 0xEDB88320

    def __init__(self, data):
        self._data = data

    def value(self):
        crc = 0xFFFFFFFF
        for byte in self._data:
            crc ^= byte
            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ self._POLYNOMIAL
                else:
                    crc >>= 1
        return (crc ^ 0xFFFFFFFF) & 0xFFFFFFFF


def crc32(data):
    return _Crc(data).value()
