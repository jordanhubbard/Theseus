# generation B shorten class


class _Short:
    _placeholder = " [...]"

    def shorten(self, text, width):
        words = text.split()
        collapsed = " ".join(words)
        if len(collapsed) <= width:
            return collapsed

        ending = self._placeholder.strip()
        if width < len(ending):
            raise ValueError("placeholder too large for max width")

        kept = []
        for word in words:
            candidate = " ".join(kept + [word])
            if len(candidate) + len(self._placeholder) > width:
                break
            kept.append(word)

        if not kept:
            return ending
        return " ".join(kept) + self._placeholder


def shorten(text, width):
    return _Short().shorten(text, width)
