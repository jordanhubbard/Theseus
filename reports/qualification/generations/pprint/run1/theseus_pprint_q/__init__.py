# generation A format recursion

__all__ = ["pformat"]


def pformat(obj, sort_dicts=True):
    return _format_value(obj, sort_dicts)


def _format_value(obj, sort_dicts):
    if obj is None:
        return "None"
    if obj is True:
        return "True"
    if obj is False:
        return "False"
    if type(obj) is int:
        return str(obj)
    if isinstance(obj, str):
        return repr(obj)
    if isinstance(obj, list):
        parts = [_format_value(item, sort_dicts) for item in obj]
        return "[" + ", ".join(parts) + "]"
    if isinstance(obj, dict):
        if sort_dicts:
            keys = sorted(obj.keys())
        else:
            keys = list(obj)
        parts = []
        for key in keys:
            part = _format_value(key, sort_dicts) + ": " + _format_value(obj[key], sort_dicts)
            parts.append(part)
        return "{" + ", ".join(parts) + "}"
    return repr(obj)
