# generation B posix class


class _Posix:
    @staticmethod
    def _slash(path):
        return b"/" if isinstance(path, bytes) else "/"

    @staticmethod
    def _dot(path):
        return b"." if isinstance(path, bytes) else "."

    @staticmethod
    def _dotdot(path):
        return b".." if isinstance(path, bytes) else ".."

    def join(self, path, *paths):
        slash = self._slash(path)
        result = path
        for part in paths:
            if part.startswith(slash):
                result = part
            elif not result or result.endswith(slash):
                result += part
            else:
                result += slash + part
        return result

    def basename(self, path):
        slash = self._slash(path)
        return path[path.rfind(slash) + 1:]

    def normpath(self, path):
        slash = self._slash(path)
        dot = self._dot(path)
        dotdot = self._dotdot(path)

        if not path:
            return dot

        leading = 0
        if path.startswith(slash):
            leading = 1
            if path.startswith(slash + slash) and not path.startswith(
                    slash + slash + slash):
                leading = 2

        parts = []
        for part in path.split(slash):
            if not part or part == dot:
                continue
            if part == dotdot:
                if parts and parts[-1] != dotdot:
                    parts.pop()
                elif not leading:
                    parts.append(part)
            else:
                parts.append(part)

        result = slash.join(parts)
        if leading:
            result = slash * leading + result
        return result or dot

    def splitext(self, path):
        slash = self._slash(path)
        dot = self._dot(path)
        separator_index = path.rfind(slash)
        dot_index = path.rfind(dot)

        if dot_index > separator_index:
            filename_start = separator_index + 1
            for index in range(filename_start, dot_index):
                if path[index:index + 1] != dot:
                    return path[:dot_index], path[dot_index:]
        empty = path[:0]
        return path, empty


_posix = _Posix()


def join(path, *paths):
    return _posix.join(path, *paths)


def basename(path):
    return _posix.basename(path)


def normpath(path):
    return _posix.normpath(path)


def splitext(path):
    return _posix.splitext(path)
