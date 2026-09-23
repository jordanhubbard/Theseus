# generation B nt class


class _Nt:
    def _marks(self, path):
        if isinstance(path, bytes):
            return b"\\", b"/", b":", b".", b".."
        return "\\", "/", ":", ".", ".."

    def _is_sep(self, character, path):
        backslash, slash, _, _, _ = self._marks(path)
        return character == backslash or character == slash

    def splitdrive(self, path):
        path = path[:]
        backslash, _, colon, _, _ = self._marks(path)
        length = len(path)

        if length >= 2 and path[1:2] == colon:
            return path[:2], path[2:]

        if length >= 2 and self._is_sep(path[0:1], path) and self._is_sep(
                path[1:2], path):
            start = 2
            if length >= 8 and path[2:8].lower() == (
                    b"?\\unc\\" if isinstance(path, bytes) else "?\\unc\\"):
                start = 8
            elif length >= 4 and path[2:3] in (
                    b"?" if isinstance(path, bytes) else "?",
                    b"." if isinstance(path, bytes) else ".",
            ) and self._is_sep(path[3:4], path):
                if length >= 6 and path[5:6] == colon:
                    return path[:6], path[6:]

            server_end = start
            while server_end < length and not self._is_sep(
                    path[server_end:server_end + 1], path):
                server_end += 1
            if server_end == start or server_end == length:
                return path[:0], path

            share_start = server_end + 1
            share_end = share_start
            while share_end < length and not self._is_sep(
                    path[share_end:share_end + 1], path):
                share_end += 1
            if share_end == share_start:
                return path[:0], path
            return path[:share_end], path[share_end:]

        return path[:0], path

    def join(self, path, *paths):
        path = path[:]
        backslash, _, colon, _, _ = self._marks(path)
        drive, tail = self.splitdrive(path)

        for part in paths:
            part = part[:]
            part_drive, part_tail = self.splitdrive(part)
            rooted = bool(part_tail) and self._is_sep(part_tail[:1], part_tail)

            if rooted:
                if part_drive or not drive:
                    drive = part_drive
                tail = part_tail
                continue

            if part_drive:
                if not drive or part_drive.lower() != drive.lower():
                    drive = part_drive
                    tail = part_tail
                    continue
                drive = part_drive

            if tail and not self._is_sep(tail[-1:], tail):
                tail += backslash
            tail += part_tail

        if drive and tail and not self._is_sep(tail[:1], tail):
            if not drive.endswith(colon) and not self._is_sep(drive[-1:], drive):
                return drive + backslash + tail
        return drive + tail

    def basename(self, path):
        _, tail = self.splitdrive(path)
        end = len(tail)
        while end:
            if self._is_sep(tail[end - 1:end], tail):
                return tail[end:]
            end -= 1
        return tail

    def normpath(self, path):
        path = path[:]
        backslash, slash, _, dot, dotdot = self._marks(path)
        if not path:
            return dot

        path = path.replace(slash, backslash)
        drive, tail = self.splitdrive(path)
        rooted = bool(tail) and tail.startswith(backslash)
        pieces = tail.split(backslash)
        normalized = []

        for piece in pieces:
            if not piece or piece == dot:
                continue
            if piece == dotdot:
                if normalized and normalized[-1] != dotdot:
                    normalized.pop()
                elif not rooted:
                    normalized.append(piece)
            else:
                normalized.append(piece)

        result = backslash.join(normalized)
        if rooted:
            result = backslash + result
        if not drive and not result:
            return backslash if rooted else dot
        if drive and not result:
            return drive + (backslash if rooted else path[:0])
        return drive + result


_nt = _Nt()


def join(path, *paths):
    return _nt.join(path, *paths)


def splitdrive(path):
    return _nt.splitdrive(path)


def basename(path):
    return _nt.basename(path)


def normpath(path):
    return _nt.normpath(path)
