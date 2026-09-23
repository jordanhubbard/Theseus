# generation B gettext class


class _Catalog:
    def gettext(self, message):
        return message


_catalog = _Catalog()


def gettext(message):
    return _catalog.gettext(message)
