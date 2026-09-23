# generation B template class


class _Template:
    def __init__(self, text):
        self.template = text

    @staticmethod
    def _is_identifier_start(character):
        return (
            character == "_"
            or "a" <= character <= "z"
            or "A" <= character <= "Z"
        )

    @staticmethod
    def _is_identifier_part(character):
        return _Template._is_identifier_start(character) or "0" <= character <= "9"

    def substitute(self, mapping):
        text = self.template
        pieces = []
        index = 0

        while index < len(text):
            dollar = text.find("$", index)
            if dollar < 0:
                pieces.append(text[index:])
                break

            pieces.append(text[index:dollar])
            index = dollar + 1
            if index >= len(text):
                raise ValueError("Invalid placeholder in string")

            marker = text[index]
            if marker == "$":
                pieces.append("$")
                index += 1
                continue

            if marker == "{":
                name_start = index + 1
                name_end = name_start
                while name_end < len(text) and self._is_identifier_part(text[name_end]):
                    name_end += 1
                if (
                    name_end == name_start
                    or not self._is_identifier_start(text[name_start])
                    or name_end >= len(text)
                    or text[name_end] != "}"
                ):
                    raise ValueError("Invalid placeholder in string")
                name = text[name_start:name_end]
                index = name_end + 1
            else:
                if not self._is_identifier_start(marker):
                    raise ValueError("Invalid placeholder in string")
                name_end = index + 1
                while name_end < len(text) and self._is_identifier_part(text[name_end]):
                    name_end += 1
                name = text[index:name_end]
                index = name_end

            pieces.append(str(mapping[name]))

        return "".join(pieces)


Template = _Template
