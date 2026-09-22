# generation B wrapper class
"""Clean-room paragraph wrapping helpers."""

import re


_REPLACED_WHITESPACE = "\t\n\v\f\r"
_SENTENCE_END = re.compile(r"[a-z][.!?][\"']?$")


class _Wrapper:
    """Configurable single-paragraph wrapper."""

    def __init__(
        self,
        width=70,
        initial_indent="",
        subsequent_indent="",
        expand_tabs=True,
        replace_whitespace=True,
        fix_sentence_endings=False,
        break_long_words=True,
        drop_whitespace=True,
        break_on_hyphens=True,
        tabsize=8,
        max_lines=None,
        placeholder=" [...]",
    ):
        self.width = width
        self.initial_indent = initial_indent
        self.subsequent_indent = subsequent_indent
        self.expand_tabs = expand_tabs
        self.replace_whitespace = replace_whitespace
        self.fix_sentence_endings = fix_sentence_endings
        self.break_long_words = break_long_words
        self.drop_whitespace = drop_whitespace
        self.break_on_hyphens = break_on_hyphens
        self.tabsize = tabsize
        self.max_lines = max_lines
        self.placeholder = placeholder

    def _munge(self, text):
        if self.expand_tabs:
            text = text.expandtabs(self.tabsize)
        if self.replace_whitespace:
            text = text.translate(dict((ord(char), " ") for char in _REPLACED_WHITESPACE))
        return text

    def _split(self, text):
        if not text:
            return []
        chunks = re.findall(r"\s+|\S+", text)
        if self.break_on_hyphens:
            split_chunks = []
            for chunk in chunks:
                if chunk.isspace() or "-" not in chunk:
                    split_chunks.append(chunk)
                    continue
                start = 0
                for match in re.finditer(r"(?<=\w)-(?=\w)", chunk):
                    split_chunks.append(chunk[start:match.end()])
                    start = match.end()
                if start < len(chunk):
                    split_chunks.append(chunk[start:])
            chunks = split_chunks
        if self.fix_sentence_endings:
            for index in range(len(chunks) - 1):
                if (
                    chunks[index + 1] == " "
                    and _SENTENCE_END.search(chunks[index])
                ):
                    chunks[index + 1] = "  "
        return chunks

    def _break_chunk(self, chunk, room):
        if room < 1:
            room = 1
        if self.break_on_hyphens:
            limit = min(room, len(chunk))
            point = chunk.rfind("-", 0, limit)
            if point > 0:
                return chunk[:point + 1], chunk[point + 1:]
        return chunk[:room], chunk[room:]

    def _append_placeholder(self, lines, indent):
        placeholder = self.placeholder
        if len(indent) + len(placeholder.lstrip()) > self.width:
            raise ValueError("placeholder too large for max width")
        base = lines[-1].rstrip() if lines else indent
        clean_placeholder = placeholder.rstrip()
        while base and len(base) + len(clean_placeholder) > self.width:
            parts = base.split()
            if not parts:
                base = indent
                break
            parts.pop()
            base = indent + " ".join(parts[1:] if parts and parts[0] == indent else parts)
        if len(base) + len(clean_placeholder) <= self.width:
            return base + clean_placeholder
        return indent + clean_placeholder.lstrip()

    def wrap(self, text):
        if self.width <= 0:
            raise ValueError("invalid width")
        chunks = self._split(self._munge(text))
        if not chunks:
            return []

        lines = []
        while chunks:
            indent = self.initial_indent if not lines else self.subsequent_indent
            room = self.width - len(indent)
            if room <= 0 and chunks:
                raise ValueError("indent larger than width")

            if self.drop_whitespace and lines:
                while chunks and chunks[0].isspace():
                    chunks.pop(0)
            current = []
            length = 0

            while chunks:
                chunk = chunks[0]
                chunk_length = len(chunk)
                if length + chunk_length <= room:
                    current.append(chunks.pop(0))
                    length += chunk_length
                    continue
                if chunk.isspace():
                    break
                if chunk_length > room and self.break_long_words:
                    available = room - length
                    if available <= 0:
                        break
                    head, tail = self._break_chunk(chunk, available)
                    current.append(head)
                    length += len(head)
                    if tail:
                        chunks[0] = tail
                    else:
                        chunks.pop(0)
                elif not current:
                    current.append(chunks.pop(0))
                    length += chunk_length
                break

            if self.drop_whitespace:
                while current and current[-1].isspace():
                    current.pop()
                if not current:
                    continue

            line = indent + "".join(current)
            truncated = bool(chunks)
            if self.max_lines is not None and len(lines) + 1 >= self.max_lines and truncated:
                lines.append(self._append_placeholder([line], indent))
                break
            lines.append(line)

        return lines

    def fill(self, text):
        return "\n".join(self.wrap(text))


def wrap(
    text,
    width=70,
    *,
    initial_indent="",
    subsequent_indent="",
    expand_tabs=True,
    replace_whitespace=True,
    fix_sentence_endings=False,
    break_long_words=True,
    drop_whitespace=True,
    break_on_hyphens=True,
    tabsize=8,
    max_lines=None,
    placeholder=" [...]",
):
    return _Wrapper(
        width=width,
        initial_indent=initial_indent,
        subsequent_indent=subsequent_indent,
        expand_tabs=expand_tabs,
        replace_whitespace=replace_whitespace,
        fix_sentence_endings=fix_sentence_endings,
        break_long_words=break_long_words,
        drop_whitespace=drop_whitespace,
        break_on_hyphens=break_on_hyphens,
        tabsize=tabsize,
        max_lines=max_lines,
        placeholder=placeholder,
    ).wrap(text)


def fill(
    text,
    width=70,
    *,
    initial_indent="",
    subsequent_indent="",
    expand_tabs=True,
    replace_whitespace=True,
    fix_sentence_endings=False,
    break_long_words=True,
    drop_whitespace=True,
    break_on_hyphens=True,
    tabsize=8,
    max_lines=None,
    placeholder=" [...]",
):
    return _Wrapper(
        width=width,
        initial_indent=initial_indent,
        subsequent_indent=subsequent_indent,
        expand_tabs=expand_tabs,
        replace_whitespace=replace_whitespace,
        fix_sentence_endings=fix_sentence_endings,
        break_long_words=break_long_words,
        drop_whitespace=drop_whitespace,
        break_on_hyphens=break_on_hyphens,
        tabsize=tabsize,
        max_lines=max_lines,
        placeholder=placeholder,
    ).fill(text)


def dedent(text):
    lines = text.splitlines(True)
    if not lines:
        return text
    margin = None
    normalized = []
    for line in lines:
        body = line.rstrip("\r\n")
        ending = line[len(body):]
        if body.strip(" \t") == "":
            normalized.append(ending or "")
            continue
        match = re.match(r"[ \t]*", body)
        prefix = match.group(0)
        if margin is None:
            margin = prefix
        else:
            limit = min(len(margin), len(prefix))
            index = 0
            while index < limit and margin[index] == prefix[index]:
                index += 1
            margin = margin[:index]
        normalized.append(body + ending)
    if not margin:
        return "".join(normalized)
    result = []
    for line in normalized:
        if line.strip(" \t\r\n"):
            result.append(line[len(margin):])
        else:
            result.append(line)
    return "".join(result)


def indent(text, prefix, predicate=None):
    if predicate is None:
        predicate = lambda line: line.strip()
    return "".join(
        prefix + line if predicate(line) else line
        for line in text.splitlines(True)
    )


def shorten(
    text,
    width,
    *,
    fix_sentence_endings=False,
    break_long_words=True,
    break_on_hyphens=True,
    placeholder=" [...]",
):
    collapsed = " ".join(text.strip().split())
    return _Wrapper(
        width=width,
        max_lines=1,
        placeholder=placeholder,
        fix_sentence_endings=fix_sentence_endings,
        break_long_words=break_long_words,
        break_on_hyphens=break_on_hyphens,
    ).fill(collapsed)


__all__ = ["wrap", "fill", "dedent", "indent", "shorten"]
