# generation A null enter

class _Null(object):
    def __init__(self, enter_result=None):
        self._enter_result = enter_result

    def __enter__(self):
        return self._enter_result

    def __exit__(self, exc_type, exc_val, exc_tb):
        return None


def nullcontext(enter_result=None):
    return _Null(enter_result)
