# generation B reader class


class _Reader:
    def __init__(self, iterable, delimiter=","):
        if not isinstance(delimiter, str) or len(delimiter) != 1:
            raise TypeError("delimiter must be a one-character string")
        self._source = iter(iterable)
        self._delimiter = delimiter
        self._fields = []
        self._field = []
        self._quoted = False
        self._after_quote = False
        self._active = False
        self._pending = []
        self._skip_lf = False
        self._finished = False

    def __iter__(self):
        return self

    def _finish_record(self):
        if self._active:
            self._fields.append("".join(self._field))
        row = self._fields
        self._fields = []
        self._field = []
        self._active = False
        self._after_quote = False
        self._pending.append(row)

    def _feed(self, text):
        if not isinstance(text, str):
            raise TypeError("iterator should return strings")

        ended_record = False
        index = 0
        while index < len(text):
            char = text[index]

            if self._skip_lf:
                self._skip_lf = False
                if char == "\n":
                    index += 1
                    continue

            if self._quoted:
                if char == '"':
                    if index + 1 < len(text) and text[index + 1] == '"':
                        self._field.append('"')
                        index += 2
                        continue
                    self._quoted = False
                    self._after_quote = True
                else:
                    self._field.append(char)
                index += 1
                continue

            if self._after_quote:
                if char == self._delimiter:
                    self._fields.append("".join(self._field))
                    self._field = []
                    self._after_quote = False
                    self._active = True
                elif char == "\r" or char == "\n":
                    self._finish_record()
                    ended_record = True
                    if char == "\r":
                        self._skip_lf = True
                else:
                    self._field.append(char)
                    self._after_quote = False
                    self._active = True
                index += 1
                continue

            if char == self._delimiter:
                self._fields.append("".join(self._field))
                self._field = []
                self._active = True
            elif char == '"' and not self._field:
                self._quoted = True
                self._active = True
            elif char == "\r" or char == "\n":
                self._finish_record()
                ended_record = True
                if char == "\r":
                    self._skip_lf = True
            else:
                self._field.append(char)
                self._active = True
            index += 1

        if not self._quoted and (self._active or not ended_record):
            self._finish_record()

    def __next__(self):
        while not self._pending:
            if self._finished:
                raise StopIteration
            try:
                line = next(self._source)
            except StopIteration:
                self._finished = True
                if self._quoted or self._active:
                    self._quoted = False
                    self._finish_record()
                else:
                    raise
            else:
                self._feed(line)
        return self._pending.pop(0)


def reader(iterable, delimiter=","):
    return _Reader(iterable, delimiter)
