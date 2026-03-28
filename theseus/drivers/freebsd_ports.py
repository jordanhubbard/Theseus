"""
theseus/drivers/freebsd_ports.py

Render a canonical package record as FreeBSD Ports output files.
"""
from __future__ import annotations

from urllib.parse import urlparse

# SPDX → FreeBSD license name mapping
_LICENSE_MAP = {
    "MIT": "MIT",
    "Apache-2.0": "APACHE20",
    "GPL-2.0": "GPLv2",
    "GPL-2.0-only": "GPLv2",
    "GPL-2.0-or-later": "GPLv2",
    "GPL-3.0": "GPLv3",
    "GPL-3.0-only": "GPLv3",
    "GPL-3.0-or-later": "GPLv3",
    "BSD-2-Clause": "BSD2CLAUSE",
    "BSD-3-Clause": "BSD3CLAUSE",
    "LGPL-2.1": "LGPL21",
    "LGPL-2.1-only": "LGPL21",
    "LGPL-2.1-or-later": "LGPL21",
    "LGPL-3.0": "LGPL30",
    "LGPL-3.0-only": "LGPL30",
    "LGPL-3.0-or-later": "LGPL30",
    "MPL-2.0": "MPL",
    "ISC": "ISC",
    "Zlib": "ZLIB",
    "zlib": "ZLIB",
    "OpenSSL": "OpenSSL",
    "curl": "curl",
}


def _map_license(spdx: str) -> str:
    return _LICENSE_MAP.get(spdx, "UNKNOWN")


def _source_filename(url: str, portname: str, version: str) -> str:
    """Derive distfile name from URL or fall back to default."""
    path = urlparse(url).path
    if path:
        name = path.rstrip("/").split("/")[-1]
        if name:
            return name
    return f"{portname}-{version}.tar.gz"


def render(record: dict) -> dict[str, str]:
    """
    Render a canonical record into FreeBSD Ports output files.

    Returns a dict mapping filename → content:
      "Makefile", "distinfo", "pkg-descr"
    """
    identity = record.get("identity", {})
    descriptive = record.get("descriptive", {})
    sources = record.get("sources", [])
    dependencies = record.get("dependencies", {})
    build = record.get("build", {})
    features = record.get("features", {})
    conflicts = record.get("conflicts", [])

    portname = identity.get("canonical_name", "unknown")
    version = identity.get("version", "0")
    is_stub = record.get("stub", False)

    # CATEGORIES
    cats = descriptive.get("categories", [])
    categories = " ".join(cats) if cats else "misc"

    # MAINTAINER
    maintainers = descriptive.get("maintainers", [])
    maintainer = maintainers[0] if maintainers else "ports@FreeBSD.org"

    # COMMENT (max 70 chars)
    summary = descriptive.get("summary", "")
    comment = summary[:70] if len(summary) > 70 else summary

    # WWW
    homepage = descriptive.get("homepage", "")

    # LICENSE
    licenses = descriptive.get("license", [])
    if licenses:
        license_str = " ".join(_map_license(l) for l in licenses)
    else:
        license_str = "UNKNOWN"

    # MASTER_SITES and DISTFILES from sources
    archive_url = ""
    archive_filename = ""
    source_sha256 = ""
    source_size = 0
    for src in sources:
        url = src.get("url", "")
        if url and any(url.endswith(ext) for ext in (
            ".tar.gz", ".tar.bz2", ".tar.xz", ".tar.zst", ".zip",
            ".tgz", ".tbz", ".txz"
        )):
            archive_url = url
            archive_filename = src.get("filename") or _source_filename(url, portname, version)
            source_sha256 = src.get("sha256", "")
            source_size = int(src.get("size", 0) or 0)
            break
    if not archive_url:
        # Try any URL
        for src in sources:
            url = src.get("url", "")
            if url:
                archive_url = url
                archive_filename = src.get("filename") or _source_filename(url, portname, version)
                source_sha256 = src.get("sha256", "")
                source_size = int(src.get("size", 0) or 0)
                break

    # Build system → USES (merge driver inference with record's build.uses list)
    system_kind = build.get("system_kind", "")
    uses_map = {
        "cmake": "cmake",
        "meson": "meson ninja",
        "autotools": "",
        "freebsd_ports_make": "",
    }
    uses_parts: list[str] = []
    inferred = uses_map.get(system_kind, "")
    if inferred:
        uses_parts.extend(inferred.split())
    for u in build.get("uses", []):
        if u and u not in uses_parts:
            uses_parts.append(u)
    uses = " ".join(uses_parts)

    # Dependencies
    build_deps = dependencies.get("build", [])
    host_deps = dependencies.get("host", [])
    runtime_deps = dependencies.get("runtime", [])

    # OPTIONS_DEFINE
    options_define = features.get("options_define", [])

    # Build Makefile
    lines = []
    if is_stub:
        lines.append("# THESEUS STUB — review before use")
        lines.append("")

    lines.append(f"PORTNAME=\t{portname}")
    lines.append(f"DISTVERSION=\t{version}")
    lines.append(f"CATEGORIES=\t{categories}")
    lines.append("")

    if maintainer:
        lines.append(f"MAINTAINER=\t{maintainer}")
    if comment:
        lines.append(f"COMMENT=\t{comment}")
    if homepage:
        lines.append(f"WWW=\t\t{homepage}")
    lines.append("")

    if license_str:
        lines.append(f"LICENSE=\t{license_str}")
        lines.append("")

    if archive_url:
        # Derive MASTER_SITES from URL base
        parsed = urlparse(archive_url)
        base = f"{parsed.scheme}://{parsed.netloc}{'/'.join(parsed.path.split('/')[:-1])}/"
        lines.append(f"MASTER_SITES=\t{base}")
        lines.append(f"DISTFILES=\t{archive_filename}")
        lines.append("")

    if uses:
        lines.append(f"USES=\t\t{uses}")
        lines.append("")

    if system_kind == "autotools":
        lines.append("GNU_CONFIGURE=\tyes")
        configure_args = build.get("configure_args", [])
        if configure_args:
            joined = " \\\n\t\t".join(configure_args)
            lines.append(f"CONFIGURE_ARGS=\t{joined}")
        lines.append("")

    if build_deps:
        lines.append(f"# STUB: resolve port paths for: {' '.join(build_deps)}")
        lines.append("BUILD_DEPENDS=\t# (fill in)")
        lines.append("")

    if host_deps:
        lines.append(f"# STUB: resolve port paths for: {' '.join(host_deps)}")
        lines.append("LIB_DEPENDS=\t# (fill in)")
        lines.append("")

    if runtime_deps:
        lines.append(f"# STUB: resolve port paths for: {' '.join(runtime_deps)}")
        lines.append("RUN_DEPENDS=\t# (fill in)")
        lines.append("")

    if options_define:
        lines.append(f"OPTIONS_DEFINE=\t{' '.join(options_define)}")
        lines.append("")

    if conflicts:
        lines.append(f"CONFLICTS=\t{' '.join(conflicts)}")
        lines.append("")

    lines.append(".include <bsd.port.mk>")

    makefile = "\n".join(lines) + "\n"

    # Build distinfo
    distinfo_lines = []
    if source_sha256:
        distinfo_lines.append(f"SHA256 ({archive_filename}) = {source_sha256}")
        if source_size:
            distinfo_lines.append(f"SIZE ({archive_filename}) = {source_size}")
        # Omit SIZE when unknown — ports make fetch will skip size check
    else:
        if archive_filename:
            distinfo_lines.append("# STUB: fill in real checksums before use")
            distinfo_lines.append(f"SHA256 ({archive_filename}) = 0000000000000000000000000000000000000000000000000000000000000000")
        else:
            distinfo_lines.append("# STUB: no source URL found — fill in manually")
    distinfo_lines.append("TIMESTAMP = 0")
    distinfo = "\n".join(distinfo_lines) + "\n"

    # Build pkg-descr
    descr_lines = []
    descr_lines.append(summary if summary else "No description available.")
    if homepage:
        descr_lines.append("")
        descr_lines.append(f"WWW: {homepage}")
    pkg_descr = "\n".join(descr_lines) + "\n"

    return {
        "Makefile": makefile,
        "distinfo": distinfo,
        "pkg-descr": pkg_descr,
    }
