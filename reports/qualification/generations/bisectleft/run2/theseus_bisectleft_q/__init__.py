# generation B bisect class


class _Bisect:
    def bisect_left(self, a, x):
        low = 0
        high = len(a)
        while low < high:
            middle = (low + high) // 2
            if a[middle] < x:
                low = middle + 1
            else:
                high = middle
        return low


def bisect_left(a, x):
    return _Bisect().bisect_left(a, x)
