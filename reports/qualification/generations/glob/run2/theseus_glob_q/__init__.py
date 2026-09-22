# generation B escape class


class _Escaper:
    def escape(self, pathname):
        parts = []
        for character in pathname:
            if character in "*?[":
                parts.append("[" + character + "]")
            else:
                parts.append(character)
        return "".join(parts)


_escaper = _Escaper()


def escape(pathname):
    return _escaper.escape(pathname)
