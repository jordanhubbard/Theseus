# generation A posix parts


class _PathParts(object):
    __slots__ = ("_raw", "_parts")

    def __init__(self, text):
        self._raw = text if isinstance(text, str) else str(text)
        self._parts = self._split_posix(self._raw)

    @staticmethod
    def _split_posix(path):
        if path in ("", "."):
            return ()
        if path == "..":
            return ("..",)

        rel = not path.startswith("/")
        anchor = ""
        rest = path
        if not rel:
            if path.startswith("//") and (len(path) == 2 or path[2] != "/"):
                anchor = "//"
                rest = path[2:]
            else:
                anchor = "/"
                rest = path[1:]

        names = []
        for segment in rest.split("/"):
            if segment in ("", "."):
                continue
            if segment == "..":
                if names and names[-1] != "..":
                    names.pop()
                elif rel:
                    names.append("..")
                continue
            names.append(segment)

        if anchor:
            return (anchor,) + tuple(names)
        return tuple(names)

    @property
    def name(self):
        parts = self._parts
        if not parts:
            return ""
        last = parts[-1]
        if last in ("/", "//"):
            return ""
        return last

    @property
    def suffix(self):
        name = self.name
        dot = name.rfind(".")
        if dot <= 0:
            return ""
        if dot == len(name) - 1:
            if name[dot - 1] == ".":
                return ""
            return "."
        if name[dot - 1] == ".":
            return ""
        return name[dot:]


class PurePosixPath(object):
    __slots__ = ("_parts",)

    def __init__(self, *pathsegments):
        if not pathsegments:
            text = "."
        elif len(pathsegments) == 1:
            text = pathsegments[0] if isinstance(pathsegments[0], str) else str(pathsegments[0])
        else:
            chunks = []
            for segment in pathsegments:
                chunks.append(segment if isinstance(segment, str) else str(segment))
            text = "/".join(chunks)
        self._parts = _PathParts(text)

    @property
    def name(self):
        return self._parts.name

    @property
    def suffix(self):
        return self._parts.suffix
