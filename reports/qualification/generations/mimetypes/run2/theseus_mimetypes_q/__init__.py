# generation B types class

from urllib.parse import urlsplit


class _Types:
    def __init__(self):
        self._encodings = {
            ".br": "br",
            ".bz2": "bzip2",
            ".gz": "gzip",
            ".xz": "xz",
            ".Z": "compress",
        }
        self._types = {
            ".3g2": "audio/3gpp2",
            ".3gp": "audio/3gpp",
            ".3gpp": "audio/3gpp",
            ".3gpp2": "audio/3gpp2",
            ".aac": "audio/aac",
            ".abw": "application/x-abiword",
            ".apng": "image/apng",
            ".arc": "application/x-freearc",
            ".avi": "video/x-msvideo",
            ".avif": "image/avif",
            ".azw": "application/vnd.amazon.ebook",
            ".bin": "application/octet-stream",
            ".bmp": "image/bmp",
            ".bz": "application/x-bzip",
            ".bz2": "application/x-bzip2",
            ".cda": "application/x-cdf",
            ".css": "text/css",
            ".csv": "text/csv",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".eot": "application/vnd.ms-fontobject",
            ".epub": "application/epub+zip",
            ".gz": "application/gzip",
            ".gif": "image/gif",
            ".htm": "text/html",
            ".html": "text/html",
            ".ico": "image/vnd.microsoft.icon",
            ".ics": "text/calendar",
            ".jar": "application/java-archive",
            ".jfif": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".jpg": "image/jpeg",
            ".js": "text/javascript",
            ".json": "application/json",
            ".jsonld": "application/ld+json",
            ".m4a": "audio/mp4",
            ".mid": "audio/midi",
            ".midi": "audio/midi",
            ".mjs": "text/javascript",
            ".mov": "video/quicktime",
            ".mp3": "audio/mpeg",
            ".mp4": "video/mp4",
            ".mpeg": "video/mpeg",
            ".mpkg": "application/vnd.apple.installer+xml",
            ".odp": "application/vnd.oasis.opendocument.presentation",
            ".ods": "application/vnd.oasis.opendocument.spreadsheet",
            ".odt": "application/vnd.oasis.opendocument.text",
            ".oga": "audio/ogg",
            ".ogv": "video/ogg",
            ".ogx": "application/ogg",
            ".opus": "audio/ogg",
            ".otf": "font/otf",
            ".pdf": "application/pdf",
            ".php": "application/x-httpd-php",
            ".png": "image/png",
            ".ppt": "application/vnd.ms-powerpoint",
            ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ".rar": "application/vnd.rar",
            ".rtf": "application/rtf",
            ".sh": "application/x-sh",
            ".svg": "image/svg+xml",
            ".tar": "application/x-tar",
            ".tif": "image/tiff",
            ".tiff": "image/tiff",
            ".ts": "video/mp2t",
            ".ttf": "font/ttf",
            ".txt": "text/plain",
            ".vsd": "application/vnd.visio",
            ".wav": "audio/wav",
            ".weba": "audio/webm",
            ".webm": "video/webm",
            ".webp": "image/webp",
            ".woff": "font/woff",
            ".woff2": "font/woff2",
            ".xhtml": "application/xhtml+xml",
            ".xls": "application/vnd.ms-excel",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".xml": "application/xml",
            ".xul": "application/vnd.mozilla.xul+xml",
            ".xz": "application/x-xz",
            ".zip": "application/zip",
            ".7z": "application/x-7z-compressed",
        }
        self._common = {
            ".md": "text/markdown",
            ".markdown": "text/markdown",
        }
        self._aliases = {
            ".svgz": (".svg", ".gz"),
            ".tbz": (".tar", ".bz2"),
            ".tbz2": (".tar", ".bz2"),
            ".tgz": (".tar", ".gz"),
            ".txz": (".tar", ".xz"),
        }

    def guess_type(self, url, strict=True):
        if isinstance(url, bytes):
            raise TypeError("url must be a string, not bytes")
        value = str(url)
        if value.startswith("data:"):
            header = value[5:].split(",", 1)[0]
            media_type = header.split(";", 1)[0]
            if "/" in media_type:
                return media_type, None
            return "text/plain", None

        path = urlsplit(value).path
        encoding = None
        dot = path.rfind(".")
        alias = self._aliases.get(path[dot:].lower()) if dot >= 0 else None
        if alias is not None:
            path = path[:dot] + alias[0] + alias[1]
        for suffix, name in self._encodings.items():
            if path.endswith(suffix):
                path = path[:-len(suffix)]
                encoding = name
                break

        dot = path.rfind(".")
        if dot < path.rfind("/"):
            return None, encoding
        suffix = path[dot:] if dot >= 0 else ""
        media_type = self._types.get(suffix)
        if media_type is None:
            media_type = self._types.get(suffix.lower())
        if media_type is None and not strict:
            media_type = self._common.get(suffix.lower())
        return media_type, encoding


_types = _Types()


def guess_type(url, strict=True):
    return _types.guess_type(url, strict)
