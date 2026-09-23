# generation B uuid class
import hashlib


class _Ids:
    class _Value:
        def __init__(self, hex_value):
            self.hex = hex_value

        def __str__(self):
            value = self.hex
            return "%s-%s-%s-%s-%s" % (
                value[0:8],
                value[8:12],
                value[12:16],
                value[16:20],
                value[20:32],
            )

    def UUID(self, hex_string):
        compact = hex_string.replace("-", "").lower()
        if len(compact) != 32:
            raise ValueError("badly formed hexadecimal UUID string")
        try:
            bytes.fromhex(compact)
        except ValueError:
            raise ValueError("badly formed hexadecimal UUID string")
        return self._Value(compact)

    def uuid5(self, namespace, name):
        namespace_value = self.UUID(namespace)
        digest = bytearray(
            hashlib.sha1(bytes.fromhex(namespace_value.hex) + name.encode("utf-8")).digest()[:16]
        )
        digest[6] = (digest[6] & 0x0F) | 0x50
        digest[8] = (digest[8] & 0x3F) | 0x80
        return str(self._Value(bytes(digest).hex()))


_IDS = _Ids()


def UUID(hex_string):
    return _IDS.UUID(hex_string)


def uuid5(namespace, name):
    return _IDS.uuid5(namespace, name)
