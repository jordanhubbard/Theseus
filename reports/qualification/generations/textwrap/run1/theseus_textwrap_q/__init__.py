# generation A width loops

import re

__all__ = ["wrap", "fill", "dedent", "indent", "shorten"]

_unicode_whitespace_trans = dict.fromkeys(map(ord, "\t\n\v\f\r "), 32)

_wordsep_re = re.compile(r"""
    (
      [\t\n\v\f\r ]+
    |
      (?<=[\w!"\'&.,?]) -{2,} (?=\w)
    |
      [^\t\n\v\f\r ]+? (?:
          -(?:
              (?<=[^\d\W]{2}-) |
              (?<=[^\d\W]-[^\d\W]-)
            )
            (?=[^\d\W]-?[^\d\W])
        |
          (?=[\t\n\v\f\r ]|\z)
        |
          (?<=[\w!"\'&.,?]) (?=-{2,}\w)
        )
    )
""", re.VERBOSE)

_wordsep_simple_re = re.compile(r"([\t\n\v\f\r ]+)")

_sentence_end_re = re.compile(r"[a-z][\.\!\?][\"']?\z")


def fill(text, width=70, initial_indent="", subsequent_indent="", expand_tabs=True,
         replace_whitespace=True, fix_sentence_endings=False, break_long_words=True,
         drop_whitespace=True, break_on_hyphens=True, tabsize=8, max_lines=None,
         placeholder=" [...]"):
    return "\n".join(wrap(
        text, width=width, initial_indent=initial_indent,
        subsequent_indent=subsequent_indent, expand_tabs=expand_tabs,
        replace_whitespace=replace_whitespace,
        fix_sentence_endings=fix_sentence_endings,
        break_long_words=break_long_words, drop_whitespace=drop_whitespace,
        break_on_hyphens=break_on_hyphens, tabsize=tabsize, max_lines=max_lines,
        placeholder=placeholder,
    ))


def wrap(text, width=70, initial_indent="", subsequent_indent="", expand_tabs=True,
         replace_whitespace=True, fix_sentence_endings=False, break_long_words=True,
         drop_whitespace=True, break_on_hyphens=True, tabsize=8, max_lines=None,
         placeholder=" [...]"):
    if width <= 0:
        raise ValueError("invalid width %r (must be > 0)" % (width,))
    if max_lines is not None:
        if max_lines <= 0:
            raise ValueError("max_lines must be positive")
        if max_lines > 1:
            indent = subsequent_indent
        else:
            indent = initial_indent
        if len(indent) + len(placeholder.lstrip()) > width:
            raise ValueError("placeholder too large for max width")

    chunks = _split_chunks(
        text, expand_tabs, replace_whitespace, tabsize, break_on_hyphens,
    )
    if fix_sentence_endings:
        _fix_sentence_endings(chunks)
    if not chunks:
        return []
    return _wrap_chunks(
        chunks, width, initial_indent, subsequent_indent, break_long_words,
        break_on_hyphens, drop_whitespace, max_lines, placeholder,
    )


def _munge_whitespace(text, expand_tabs, replace_whitespace, tabsize):
    if expand_tabs:
        text = text.expandtabs(tabsize)
    if replace_whitespace:
        text = text.translate(_unicode_whitespace_trans)
    return text


def _split(text, break_on_hyphens):
    if break_on_hyphens:
        chunks = _wordsep_re.split(text)
    else:
        chunks = _wordsep_simple_re.split(text)
    return [chunk for chunk in chunks if chunk]


def _split_chunks(text, expand_tabs, replace_whitespace, tabsize, break_on_hyphens):
    text = _munge_whitespace(text, expand_tabs, replace_whitespace, tabsize)
    return _split(text, break_on_hyphens)


def _fix_sentence_endings(chunks):
    index = 0
    while index < len(chunks) - 1:
        if chunks[index + 1] == " " and _sentence_end_re.search(chunks[index]):
            chunks[index + 1] = "  "
            index += 2
        else:
            index += 1


def _handle_long_word(reversed_chunks, cur_line, cur_len, width, break_long_words,
                      break_on_hyphens):
    if width < 1:
        space_left = 1
    else:
        space_left = width - cur_len

    if break_long_words and space_left > 0:
        end = space_left
        chunk = reversed_chunks[-1]
        if break_on_hyphens and len(chunk) > space_left:
            hyphen = chunk.rfind("-", 0, space_left)
            if hyphen > 0 and any(ch != "-" for ch in chunk[:hyphen]):
                end = hyphen + 1
        cur_line.append(chunk[:end])
        reversed_chunks[-1] = chunk[end:]
    elif not cur_line:
        cur_line.append(reversed_chunks.pop())


def _wrap_chunks(chunks, width, initial_indent, subsequent_indent, break_long_words,
                 break_on_hyphens, drop_whitespace, max_lines, placeholder):
    lines = []
    chunks = list(chunks)
    chunks.reverse()

    while chunks:
        cur_line = []
        cur_len = 0

        if lines:
            indent = subsequent_indent
        else:
            indent = initial_indent

        line_width = width - len(indent)

        if drop_whitespace and chunks[-1].strip() == "" and lines:
            del chunks[-1]

        while chunks:
            piece_len = len(chunks[-1])
            if cur_len + piece_len <= line_width:
                cur_line.append(chunks.pop())
                cur_len += piece_len
            else:
                break

        if chunks and len(chunks[-1]) > line_width:
            _handle_long_word(
                chunks, cur_line, cur_len, line_width, break_long_words,
                break_on_hyphens,
            )
            cur_len = sum(len(part) for part in cur_line)

        if drop_whitespace and cur_line and cur_line[-1].strip() == "":
            cur_len -= len(cur_line[-1])
            del cur_line[-1]

        if cur_line:
            if (max_lines is None or
                    len(lines) + 1 < max_lines or
                    (not chunks or
                     drop_whitespace and
                     len(chunks) == 1 and
                     not chunks[0].strip()) and cur_len <= line_width):
                lines.append(indent + "".join(cur_line))
            else:
                while cur_line:
                    if (cur_line[-1].strip() and
                            cur_len + len(placeholder) <= line_width):
                        cur_line.append(placeholder)
                        lines.append(indent + "".join(cur_line))
                        break
                    cur_len -= len(cur_line[-1])
                    del cur_line[-1]
                else:
                    if lines:
                        prev_line = lines[-1].rstrip()
                        if len(prev_line) + len(placeholder) <= width:
                            lines[-1] = prev_line + placeholder
                            break
                    lines.append(indent + placeholder.lstrip())
                break

    return lines


def dedent(text):
    if not text:
        return text
    lines = text.splitlines(True)
    margin = None
    for line in lines:
        content = line.rstrip("\n\r")
        if not content.strip():
            continue
        indent_len = len(content) - len(content.lstrip(" \t"))
        if margin is None or indent_len < margin:
            margin = indent_len
    if margin is None:
        margin = 0
    elif margin > 0:
        prefix = None
        for line in lines:
            content = line.rstrip("\n\r")
            if not content.strip():
                continue
            if len(content) < margin:
                margin = 0
                break
            candidate = content[:margin]
            if any(ch not in " \t" for ch in candidate):
                margin = 0
                break
            if prefix is None:
                prefix = candidate
            elif candidate != prefix:
                margin = 0
                break

    result = []
    for line in lines:
        ending = ""
        if line.endswith("\n"):
            ending = "\n"
        elif line.endswith("\r"):
            ending = "\r"
        content = line[: len(line) - len(ending)] if ending else line
        if not content.strip():
            result.append(ending)
            continue
        if margin > 0 and len(content) >= margin:
            result.append(content[margin:] + ending)
        else:
            result.append(content + ending)
    return "".join(result)


def indent(text, prefix, predicate=None):
    if predicate is None:
        def predicate(line):
            return line.strip()
    lines = text.splitlines(True)
    result = []
    for line in lines:
        if predicate(line):
            result.append(prefix + line)
        else:
            result.append(line)
    return "".join(result)


def shorten(text, width, fix_sentence_endings=False, break_long_words=True,
            break_on_hyphens=True, placeholder=" [...]"):
    collapsed = " ".join(text.strip().split())
    return fill(
        collapsed,
        width=width,
        max_lines=1,
        fix_sentence_endings=fix_sentence_endings,
        break_long_words=break_long_words,
        break_on_hyphens=break_on_hyphens,
        placeholder=placeholder,
    )
