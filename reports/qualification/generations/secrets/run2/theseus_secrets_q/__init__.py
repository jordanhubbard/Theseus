# generation B digest class


class _Digest:
    @staticmethod
    def compare(a, b):
        if not isinstance(a, (str, bytes)) or not isinstance(b, type(a)):
            return False

        different = len(a) ^ len(b)
        limit = max(len(a), len(b))
        for index in range(limit):
            left = a[index] if index < len(a) else 0
            right = b[index] if index < len(b) else 0
            if isinstance(left, str):
                left = ord(left)
            if isinstance(right, str):
                right = ord(right)
            different |= left ^ right
        return different == 0


def compare_digest(a, b):
    return _Digest.compare(a, b)
