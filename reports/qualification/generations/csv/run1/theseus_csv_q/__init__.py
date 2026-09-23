# generation A row split

__all__ = ["reader"]


def reader(iterable, delimiter=","):
    quotechar = '"'
    source = iter(iterable)
    pending = None

    while True:
        if pending is None:
            try:
                line = next(source)
            except StopIteration:
                return
        else:
            line = pending
            pending = None

        while True:
            row, rest, need_more = _parse_line(
                line, delimiter, quotechar, at_eof=False
            )
            if need_more:
                try:
                    line = line + next(source)
                except StopIteration:
                    row, rest, _ = _parse_line(
                        line, delimiter, quotechar, at_eof=True
                    )
                    yield row
                    if rest:
                        pending = rest
                    return
                continue
            yield row
            if rest:
                line = rest
                continue
            break


def _parse_line(line, delimiter, quotechar, at_eof):
    fields = []
    field = []
    i = 0
    n = len(line)
    in_quotes = False

    if n == 0:
        return [], "", False

    while i < n:
        ch = line[i]
        if in_quotes:
            if ch == quotechar:
                if i + 1 < n and line[i + 1] == quotechar:
                    field.append(quotechar)
                    i += 2
                    continue
                in_quotes = False
                i += 1
                continue
            field.append(ch)
            i += 1
            continue

        if ch == quotechar:
            if not field:
                in_quotes = True
                i += 1
                continue
            field.append(ch)
            i += 1
            continue
        if ch == delimiter:
            fields.append("".join(field))
            field = []
            i += 1
            continue
        if ch in "\r\n":
            raise ValueError(
                "new-line character seen in unquoted field - do you need to open "
                "the file with newline=''?"
            )
        field.append(ch)
        i += 1

    if in_quotes and not at_eof:
        return None, None, True

    if field or fields:
        fields.append("".join(field))
    return fields, "", False
