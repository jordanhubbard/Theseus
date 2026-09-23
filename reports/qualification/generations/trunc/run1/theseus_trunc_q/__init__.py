# generation A trunc scan

def trunc(x):
    if isinstance(x, int):
        return x
    if isinstance(x, float):
        return int(x)
    trunc_method = getattr(type(x), "__trunc__", None)
    if trunc_method is not None:
        result = trunc_method(x)
        if isinstance(result, int):
            return result
        return int(result)
    raise TypeError("trunc() argument must be a real number, not {}".format(type(x).__name__))
