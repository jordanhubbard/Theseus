"""
theseus_mimetypes_cr — Clean-room mimetypes module.
No import of the standard `mimetypes` module.
"""

import os as _os
import posixpath as _posixpath

# Core MIME type mappings (extension -> (type, encoding))
types_map = {
    '.a': 'application/octet-stream',
    '.ai': 'application/postscript',
    '.aif': 'audio/x-aiff',
    '.aifc': 'audio/x-aiff',
    '.aiff': 'audio/x-aiff',
    '.au': 'audio/basic',
    '.avi': 'video/x-msvideo',
    '.bat': 'text/plain',
    '.bcpio': 'application/x-bcpio',
    '.bin': 'application/octet-stream',
    '.bmp': 'image/bmp',
    '.c': 'text/plain',
    '.cdf': 'application/x-netcdf',
    '.cpio': 'application/x-cpio',
    '.csh': 'application/x-csh',
    '.css': 'text/css',
    '.csv': 'text/csv',
    '.dll': 'application/octet-stream',
    '.doc': 'application/msword',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.dvi': 'application/x-dvi',
    '.eml': 'message/rfc822',
    '.eps': 'application/postscript',
    '.etx': 'text/x-setext',
    '.exe': 'application/octet-stream',
    '.gif': 'image/gif',
    '.gtar': 'application/x-gtar',
    '.gz': 'application/gzip',
    '.h': 'text/plain',
    '.hdf': 'application/x-hdf',
    '.htm': 'text/html',
    '.html': 'text/html',
    '.ico': 'image/vnd.microsoft.icon',
    '.ief': 'image/ief',
    '.jpe': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.jpg': 'image/jpeg',
    '.js': 'text/javascript',
    '.json': 'application/json',
    '.ksh': 'text/plain',
    '.latex': 'application/x-latex',
    '.m1v': 'video/mpeg',
    '.m3u': 'audio/mpegurl',
    '.man': 'application/x-troff-man',
    '.me': 'application/x-troff-me',
    '.mime': 'message/rfc822',
    '.mif': 'application/x-mif',
    '.mov': 'video/quicktime',
    '.movie': 'video/x-sgi-movie',
    '.mp2': 'audio/mpeg',
    '.mp3': 'audio/mpeg',
    '.mp4': 'video/mp4',
    '.mpa': 'video/mpeg',
    '.mpe': 'video/mpeg',
    '.mpeg': 'video/mpeg',
    '.mpg': 'video/mpeg',
    '.ms': 'application/x-troff-ms',
    '.nc': 'application/x-netcdf',
    '.nws': 'message/rfc822',
    '.o': 'application/octet-stream',
    '.obj': 'application/octet-stream',
    '.oda': 'application/oda',
    '.p12': 'application/x-pkcs12',
    '.p7c': 'application/pkcs7-mime',
    '.pbm': 'image/x-portable-bitmap',
    '.pdf': 'application/pdf',
    '.pfx': 'application/x-pkcs12',
    '.pgm': 'image/x-portable-graymap',
    '.pl': 'text/plain',
    '.png': 'image/png',
    '.pnm': 'image/x-portable-anymap',
    '.pot': 'application/vnd.ms-powerpoint',
    '.ppa': 'application/vnd.ms-powerpoint',
    '.ppm': 'image/x-portable-pixmap',
    '.pps': 'application/vnd.ms-powerpoint',
    '.ppt': 'application/vnd.ms-powerpoint',
    '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    '.ps': 'application/postscript',
    '.py': 'text/x-python',
    '.pwz': 'application/vnd.ms-powerpoint',
    '.qt': 'video/quicktime',
    '.ra': 'audio/x-pn-realaudio',
    '.ram': 'application/x-pn-realaudio',
    '.ras': 'image/x-cmu-raster',
    '.rdf': 'application/xml',
    '.rgb': 'image/x-rgb',
    '.roff': 'application/x-troff',
    '.rtx': 'text/richtext',
    '.sgm': 'text/x-sgml',
    '.sgml': 'text/x-sgml',
    '.sh': 'application/x-sh',
    '.shar': 'application/x-shar',
    '.snd': 'audio/basic',
    '.so': 'application/octet-stream',
    '.src': 'application/x-wais-source',
    '.sv4cpio': 'application/x-sv4cpio',
    '.sv4crc': 'application/x-sv4crc',
    '.svg': 'image/svg+xml',
    '.swf': 'application/x-shockwave-flash',
    '.t': 'application/x-troff',
    '.tar': 'application/x-tar',
    '.tcl': 'application/x-tcl',
    '.tex': 'application/x-tex',
    '.texi': 'application/x-texinfo',
    '.texinfo': 'application/x-texinfo',
    '.tif': 'image/tiff',
    '.tiff': 'image/tiff',
    '.tr': 'application/x-troff',
    '.tsv': 'text/tab-separated-values',
    '.txt': 'text/plain',
    '.ustar': 'application/x-ustar',
    '.vcf': 'text/x-vcard',
    '.wav': 'audio/x-wav',
    '.wiz': 'application/msword',
    '.wsdl': 'application/xml',
    '.xbm': 'image/x-xbitmap',
    '.xlb': 'application/vnd.ms-excel',
    '.xls': 'application/vnd.ms-excel',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.xml': 'application/xml',
    '.xpdl': 'application/xml',
    '.xpm': 'image/x-xpixmap',
    '.xsl': 'application/xml',
    '.xwd': 'image/x-xwindowdump',
    '.zip': 'application/zip',
}

# Reverse map: type -> extension
_types_map_inv = {}
for _ext, _type in types_map.items():
    if _type not in _types_map_inv:
        _types_map_inv[_type] = _ext

# Encodings
encodings_map = {
    '.gz': 'gzip',
    '.Z': 'compress',
    '.bz2': 'bzip2',
    '.xz': 'xz',
}

suffix_map = {
    '.svgz': '.svg.gz',
    '.tgz': '.tar.gz',
    '.tbz2': '.tar.bz2',
    '.txz': '.tar.xz',
}

_inited = False


def init(files=None):
    global _inited
    _inited = True


def guess_type(url, strict=True):
    """Guess the type of a file based on its URL, given by a string or a path-like object."""
    if hasattr(url, '__fspath__'):
        url = _os.fspath(url)
    scheme, _, path = str(url).partition('://')
    if not path:
        path = url

    base, ext = _posixpath.splitext(path)
    ext = ext.lower()

    # Check suffix_map
    if ext in suffix_map:
        base, ext = _posixpath.splitext(base + suffix_map[ext])
        ext = ext.lower()

    # Check encoding
    encoding = None
    if ext in encodings_map:
        encoding = encodings_map[ext]
        base, ext = _posixpath.splitext(base)
        ext = ext.lower()

    mime_type = types_map.get(ext)
    return (mime_type, encoding)


def guess_extension(type, strict=True):
    """Guess the extension for a file based on its MIME type."""
    type = type.lower()
    ext = _types_map_inv.get(type)
    return ext


def guess_all_extensions(type, strict=True):
    """Guess all extensions for a given MIME type."""
    type = type.lower()
    return [ext for ext, t in types_map.items() if t == type]


def guess_file(filename, strict=True):
    return guess_type(filename, strict)


def add_type(type, ext, strict=True):
    ext = ext.lower()
    types_map[ext] = type
    _types_map_inv[type] = ext


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def mimetypes2_guess_type():
    """guess_type('foo.html') returns text/html; returns True."""
    t, enc = guess_type('foo.html')
    return t == 'text/html' and enc is None


def mimetypes2_guess_extension():
    """guess_extension('text/html') returns a .html extension; returns True."""
    ext = guess_extension('text/html')
    return ext in ('.html', '.htm')


def mimetypes2_types_map():
    """types_map dict is non-empty; returns True."""
    return isinstance(types_map, dict) and len(types_map) > 50


__all__ = [
    'guess_type', 'guess_extension', 'guess_all_extensions', 'add_type', 'init',
    'types_map', 'encodings_map', 'suffix_map',
    'mimetypes2_guess_type', 'mimetypes2_guess_extension', 'mimetypes2_types_map',
]
