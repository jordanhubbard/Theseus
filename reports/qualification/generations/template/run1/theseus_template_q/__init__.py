# generation A template scan

__all__ = ["Template"]


class Template:
    """Simple $-based template with substitute(mapping)."""

    def __init__(self, template):
        self.template = str(template)

    def substitute(self, mapping=None, **kwargs):
        if mapping is None:
            if kwargs:
                mapping = kwargs
            else:
                mapping = {}
        elif kwargs:
            combined = {}
            try:
                combined.update(mapping)
            except TypeError:
                for key in mapping:
                    combined[key] = mapping[key]
            combined.update(kwargs)
            mapping = combined
        return self._replace(mapping, safe=False)

    def _replace(self, mapping, safe):
        template = self.template
        pieces = []
        index = 0
        length = len(template)

        while index < length:
            char = template[index]
            if char != "$":
                pieces.append(char)
                index += 1
                continue

            if index + 1 >= length:
                self._invalid(index)
            nxt = template[index + 1]
            if nxt == "$":
                pieces.append("$")
                index += 2
                continue
            if nxt == "{":
                close = template.find("}", index + 2)
                if close == -1:
                    self._invalid(index)
                field = template[index + 2 : close]
                index = close + 1
                if not self._valid_name(field):
                    self._invalid(index - len(field) - 2)
                value = self._lookup(mapping, field, safe)
                if value is not None:
                    pieces.append(value)
                continue

            field, consumed = self._read_name(template, index + 1)
            if not field:
                self._invalid(index)
            index += 1 + consumed
            value = self._lookup(mapping, field, safe)
            if value is not None:
                pieces.append(value)

        return "".join(pieces)

    def _lookup(self, mapping, field, safe):
        try:
            return str(mapping[field])
        except KeyError:
            if safe:
                return None
            raise
        except TypeError:
            try:
                return str(mapping[field])
            except KeyError:
                if safe:
                    return None
                raise

    def _read_name(self, text, start):
        if start >= len(text):
            return "", 0
        first = text[start]
        if first != "_" and not first.isalpha():
            return "", 0
        end = start + 1
        while end < len(text):
            ch = text[end]
            if ch == "_" or ch.isalnum():
                end += 1
            else:
                break
        return text[start:end], end - start

    def _valid_name(self, name):
        if not name:
            return False
        first = name[0]
        if first != "_" and not first.isalpha():
            return False
        for ch in name[1:]:
            if ch != "_" and not ch.isalnum():
                return False
        return True

    def _invalid(self, index):
        raise ValueError(
            "Invalid placeholder in string: line 1, col {}".format(index + 1)
        )
