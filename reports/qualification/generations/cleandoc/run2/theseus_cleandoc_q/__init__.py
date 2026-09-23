# generation B cleandoc class


class _Docs:
    def clean(self, text):
        lines = text.expandtabs().split("\n")
        margin = None

        for line in lines[1:]:
            content = line.lstrip()
            if content:
                indent = len(line) - len(content)
                if margin is None or indent < margin:
                    margin = indent

        if lines:
            lines[0] = lines[0].lstrip()
        if margin is not None:
            for index in range(1, len(lines)):
                lines[index] = lines[index][margin:]

        while lines and not lines[-1].strip():
            lines.pop()
        while lines and not lines[0].strip():
            lines.pop(0)

        return "\n".join(lines)


def cleandoc(text):
    return _Docs().clean(text)
