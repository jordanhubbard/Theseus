"""
theseus_gettext_cr — Clean-room gettext module.
No import of the standard `gettext` module.
"""

import os as _os
import struct as _struct
import io as _io


class NullTranslations:
    def __init__(self, fp=None):
        self._info = {}
        self._charset = None
        self._output_charset = None
        self._fallback = None
        if fp is not None:
            self._parse(fp)

    def _parse(self, fp):
        pass

    def add_fallback(self, fallback):
        if self._fallback:
            self._fallback.add_fallback(fallback)
        else:
            self._fallback = fallback

    def gettext(self, message):
        if self._fallback:
            return self._fallback.gettext(message)
        return message

    def ngettext(self, msgid1, msgid2, n):
        if self._fallback:
            return self._fallback.ngettext(msgid1, msgid2, n)
        return msgid1 if n == 1 else msgid2

    def pgettext(self, context, message):
        if self._fallback:
            return self._fallback.pgettext(context, message)
        return message

    def npgettext(self, context, msgid1, msgid2, n):
        if self._fallback:
            return self._fallback.npgettext(context, msgid1, msgid2, n)
        return msgid1 if n == 1 else msgid2

    def lgettext(self, message):
        return self.gettext(message)

    def lngettext(self, msgid1, msgid2, n):
        return self.ngettext(msgid1, msgid2, n)

    def info(self):
        return self._info

    def charset(self):
        return self._charset

    def output_charset(self):
        return self._output_charset

    def set_output_charset(self, charset):
        self._output_charset = charset

    def install(self, names=None):
        import builtins as _builtins
        _builtins.__dict__['_'] = self.gettext
        if names is not None:
            for name in names:
                _builtins.__dict__[name] = getattr(self, name)


class GNUTranslations(NullTranslations):
    LE_MAGIC = 0x950412de
    BE_MAGIC = 0xde120495

    def _parse(self, fp):
        buf = fp.read()
        if len(buf) < 28:
            return
        magic = _struct.unpack_from('<I', buf, 0)[0]
        if magic == self.LE_MAGIC:
            fmt = '<II'
        elif magic == self.BE_MAGIC:
            fmt = '>II'
        else:
            return
        version, msgcount = _struct.unpack_from(fmt, buf, 4)
        origidx, transidx = _struct.unpack_from(fmt, buf, 12)
        self._catalog = {}
        for i in range(msgcount):
            origlen, origoff = _struct.unpack_from(fmt, buf, origidx + i*8)
            translen, transoff = _struct.unpack_from(fmt, buf, transidx + i*8)
            orig = buf[origoff:origoff+origlen].decode('utf-8')
            trans = buf[transoff:transoff+translen].decode('utf-8')
            self._catalog[orig] = trans

    def gettext(self, message):
        if hasattr(self, '_catalog') and message in self._catalog:
            return self._catalog[message]
        if self._fallback:
            return self._fallback.gettext(message)
        return message


def find(domain, localedir=None, languages=None, all=False):
    """Find the .mo file for a given domain."""
    if localedir is None:
        localedir = _os.path.join(_os.environ.get('HOME', '/'), 'locale')

    if languages is None:
        languages = []
        for envvar in ('LANGUAGE', 'LC_ALL', 'LC_MESSAGES', 'LANG'):
            val = _os.environ.get(envvar)
            if val:
                languages.extend(val.split(':'))
                break
        if 'C' not in languages:
            languages.append('C')

    nelangs = []
    for lang in languages:
        for nelang in [lang]:
            if nelang not in nelangs:
                nelangs.append(nelang)

    result = []
    for lang in nelangs:
        if lang == 'C':
            break
        mofile = _os.path.join(localedir, lang, 'LC_MESSAGES', f'{domain}.mo')
        if _os.path.exists(mofile):
            if all:
                result.append(mofile)
            else:
                return mofile

    return result if all else None


def translation(domain, localedir=None, languages=None, class_=None,
                codeset=None, fallback=False):
    if class_ is None:
        class_ = GNUTranslations
    mofile = find(domain, localedir, languages)
    if mofile is None:
        if fallback:
            return NullTranslations()
        raise FileNotFoundError(f"No translation file for domain '{domain}'")
    with open(mofile, 'rb') as f:
        return class_(f)


def install(domain, localedir=None, codeset=None, names=None):
    t = translation(domain, localedir, fallback=True)
    t.install(names)


def gettext(message):
    return message


def ngettext(msgid1, msgid2, n):
    return msgid1 if n == 1 else msgid2


def pgettext(context, message):
    return message


def npgettext(context, msgid1, msgid2, n):
    return msgid1 if n == 1 else msgid2


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def gettext2_nulltranslations():
    """NullTranslations().gettext(msg) returns msg unchanged; returns True."""
    t = NullTranslations()
    return t.gettext('Hello World') == 'Hello World'


def gettext2_install():
    """install function is callable; returns True."""
    return callable(install)


def gettext2_find():
    """find() returns None when no .mo file found; returns True."""
    result = find('nonexistent_domain_xyz', localedir='/nonexistent/path')
    return result is None


__all__ = [
    'NullTranslations', 'GNUTranslations',
    'find', 'translation', 'install',
    'gettext', 'ngettext', 'pgettext', 'npgettext',
    'gettext2_nulltranslations', 'gettext2_install', 'gettext2_find',
]
