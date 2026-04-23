"""
theseus_gettext_cr2 - Clean-room gettext utilities.
No import of the original gettext module.
"""

import builtins


class NullTranslations:
    """Base translation class that returns strings unchanged."""

    def gettext(self, message):
        """Return message unchanged (identity translation)."""
        return message

    def ngettext(self, singular, plural, n):
        """Return singular if n == 1, else plural."""
        if n == 1:
            return singular
        return plural

    def install(self):
        """Install _() into builtins."""
        builtins._ = self.gettext


class GNUTranslations(NullTranslations):
    """
    Translation class that loads from a .mo file or an in-memory catalog dict.
    """

    def __init__(self, catalog=None, fp=None):
        """
        Initialize with either a catalog dict or a file-like object pointing
        to a .mo file.

        :param catalog: dict mapping msgid -> msgstr (and for plurals,
                        msgid -> list of plural forms)
        :param fp: file-like object for a .mo file (binary mode)
        """
        self._catalog = {}
        self._plural_catalog = {}

        if catalog is not None:
            for key, value in catalog.items():
                if isinstance(value, list):
                    self._plural_catalog[key] = value
                else:
                    self._catalog[key] = value

        if fp is not None:
            self._parse_mo(fp)

    def _parse_mo(self, fp):
        """Parse a GNU .mo binary file."""
        import struct

        data = fp.read()
        if len(data) < 20:
            return

        # Check magic number
        magic = struct.unpack_from('<I', data, 0)[0]
        if magic == 0x950412de:
            # Little-endian
            fmt = '<'
        elif magic == 0xde120495:
            # Big-endian
            fmt = '>'
        else:
            return

        revision = struct.unpack_from(fmt + 'I', data, 4)[0]
        num_strings = struct.unpack_from(fmt + 'I', data, 8)[0]
        orig_offset = struct.unpack_from(fmt + 'I', data, 12)[0]
        trans_offset = struct.unpack_from(fmt + 'I', data, 16)[0]

        for i in range(num_strings):
            orig_len, orig_off = struct.unpack_from(fmt + 'II', data,
                                                    orig_offset + i * 8)
            trans_len, trans_off = struct.unpack_from(fmt + 'II', data,
                                                      trans_offset + i * 8)

            orig = data[orig_off: orig_off + orig_len]
            trans = data[trans_off: trans_off + trans_len]

            # Handle plural forms: original may contain \x00 separator
            if b'\x00' in orig:
                parts = orig.split(b'\x00')
                singular_key = parts[0].decode('utf-8', errors='replace')
                plural_forms = trans.split(b'\x00')
                self._plural_catalog[singular_key] = [
                    p.decode('utf-8', errors='replace') for p in plural_forms
                ]
            else:
                key = orig.decode('utf-8', errors='replace')
                value = trans.decode('utf-8', errors='replace')
                self._catalog[key] = value

    def gettext(self, message):
        """Return translated message, or message if not found."""
        return self._catalog.get(message, message)

    def ngettext(self, singular, plural, n):
        """Return translated plural form, or fallback to singular/plural."""
        if singular in self._plural_catalog:
            forms = self._plural_catalog[singular]
            # Simple plural rule: index 0 for n==1, index 1 otherwise
            # (covers most Western languages)
            idx = 0 if n == 1 else 1
            if idx < len(forms):
                return forms[idx]
            if forms:
                return forms[-1]
        # Fallback
        return singular if n == 1 else plural


# ---------------------------------------------------------------------------
# Zero-arg invariant functions
# ---------------------------------------------------------------------------

def gettext2_null_gettext():
    """NullTranslations().gettext('hello') == 'hello'"""
    return NullTranslations().gettext('hello')


def gettext2_null_ngettext():
    """NullTranslations().ngettext('item', 'items', 1) == 'item'"""
    return NullTranslations().ngettext('item', 'items', 1)


def gettext2_null_ngettext_plural():
    """NullTranslations().ngettext('item', 'items', 2) == 'items'"""
    return NullTranslations().ngettext('item', 'items', 2)