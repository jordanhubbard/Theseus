# generation B indent class


class _Indent:
    def __init__(self, prefix):
        self.prefix = prefix

    def apply(self, text):
        return "".join(
            self.prefix + line if line.strip() else line
            for line in text.splitlines(keepends=True)
        )


def indent(text, prefix):
    return _Indent(prefix).apply(text)
