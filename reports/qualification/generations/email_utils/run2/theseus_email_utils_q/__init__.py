# generation B address class


class _Addr:
    def _unquote(self, text):
        text = text.strip()
        if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
            out = []
            escaped = False
            for char in text[1:-1]:
                if escaped:
                    out.append(char)
                    escaped = False
                elif char == "\\":
                    escaped = True
                else:
                    out.append(char)
            if escaped:
                out.append("\\")
            return "".join(out)
        return text

    def _comments(self, text):
        clean = []
        comments = []
        current = []
        depth = 0
        quoted = False
        escaped = False

        for char in text:
            if escaped:
                (current if depth else clean).append(char)
                escaped = False
                continue
            if char == "\\":
                if depth:
                    current.append(char)
                else:
                    clean.append(char)
                escaped = True
                continue
            if char == '"' and depth == 0:
                quoted = not quoted
                clean.append(char)
                continue
            if not quoted and char == "(":
                if depth:
                    current.append(char)
                depth += 1
                continue
            if not quoted and char == ")" and depth:
                depth -= 1
                if depth:
                    current.append(char)
                else:
                    value = "".join(current).strip()
                    if value:
                        comments.append(value)
                    current = []
                continue
            (current if depth else clean).append(char)

        if depth:
            clean.append("(")
            clean.extend(current)
        return "".join(clean), comments

    def _first(self, text):
        quoted = False
        escaped = False
        comment = 0
        angle = 0
        for index, char in enumerate(text):
            if escaped:
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            if char == '"' and comment == 0:
                quoted = not quoted
            elif not quoted:
                if char == "(":
                    comment += 1
                elif char == ")" and comment:
                    comment -= 1
                elif comment == 0:
                    if char == "<":
                        angle += 1
                    elif char == ">" and angle:
                        angle -= 1
                    elif char == "," and angle == 0:
                        return text[:index]
        return text

    def _angle(self, text):
        quoted = False
        escaped = False
        comment = 0
        start = None
        for index, char in enumerate(text):
            if escaped:
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            if char == '"' and comment == 0:
                quoted = not quoted
            elif not quoted:
                if char == "(":
                    comment += 1
                elif char == ")" and comment:
                    comment -= 1
                elif comment == 0 and char == "<" and start is None:
                    start = index
                elif comment == 0 and char == ">" and start is not None:
                    return start, index
        return None

    def parse(self, addr):
        if not isinstance(addr, str):
            return "", ""

        text = self._first(addr).strip()
        if not text:
            return "", ""

        bounds = self._angle(text)
        if bounds is not None:
            start, end = bounds
            name_text, name_comments = self._comments(text[:start])
            address_text, unused = self._comments(text[start + 1:end])
            name = self._unquote(name_text.strip())
            if not name and name_comments:
                name = " ".join(name_comments)
            address = address_text.strip()
            if ":" in address and address.lstrip().startswith("@"):
                address = address.rsplit(":", 1)[-1].strip()
            return name, address

        clean, comments = self._comments(text)
        clean = clean.strip()

        if ":" in clean and clean.endswith(";"):
            clean = clean.split(":", 1)[1][:-1].strip()
            clean = self._first(clean).strip()

        name = " ".join(comments)
        return name, clean


_ADDRESS_PARSER = _Addr()


def parseaddr(addr):
    return _ADDRESS_PARSER.parse(addr)
