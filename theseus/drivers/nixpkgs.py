"""
theseus/drivers/nixpkgs.py

Render a canonical package record as a Nixpkgs derivation.
"""
from __future__ import annotations

# SPDX → Nix license attribute mapping
_LICENSE_MAP = {
    "MIT": "licenses.mit",
    "Apache-2.0": "licenses.asl20",
    "GPL-2.0": "licenses.gpl2Only",
    "GPL-2.0-only": "licenses.gpl2Only",
    "GPL-2.0-or-later": "licenses.gpl2Plus",
    "GPL-3.0": "licenses.gpl3Only",
    "GPL-3.0-only": "licenses.gpl3Only",
    "GPL-3.0-or-later": "licenses.gpl3Plus",
    "BSD-2-Clause": "licenses.bsd2",
    "BSD-3-Clause": "licenses.bsd3",
    "LGPL-2.1": "licenses.lgpl21Only",
    "LGPL-2.1-only": "licenses.lgpl21Only",
    "LGPL-2.1-or-later": "licenses.lgpl21Plus",
    "LGPL-3.0": "licenses.lgpl3Only",
    "LGPL-3.0-only": "licenses.lgpl3Only",
    "LGPL-3.0-or-later": "licenses.lgpl3Plus",
    "MPL-2.0": "licenses.mpl20",
    "ISC": "licenses.isc",
    "Zlib": "licenses.zlib",
    "zlib": "licenses.zlib",
    "OpenSSL": "licenses.openssl",
    "curl": "licenses.curl",
}


def _map_license(spdx: str) -> str:
    return _LICENSE_MAP.get(spdx, "licenses.unfree")


def _nix_string(s: str) -> str:
    """Escape a string for Nix."""
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("${", "\\${")


def render(record: dict) -> dict[str, str]:
    """
    Render a canonical record into a Nixpkgs derivation.

    Returns a dict mapping filename → content:
      "default.nix"
    """
    identity = record.get("identity", {})
    descriptive = record.get("descriptive", {})
    sources = record.get("sources", [])
    dependencies = record.get("dependencies", {})
    build = record.get("build", {})
    platforms = record.get("platforms", {})

    pname = identity.get("canonical_name", "unknown")
    version = identity.get("version", "0")
    is_stub = record.get("stub", False)

    summary = descriptive.get("summary", "No description available.")
    homepage = descriptive.get("homepage", "")
    licenses = descriptive.get("license", [])
    maintainers = descriptive.get("maintainers", [])

    system_kind = build.get("system_kind", "")

    build_deps = dependencies.get("build", [])
    host_deps = dependencies.get("host", [])
    runtime_deps = dependencies.get("runtime", [])

    # Find archive source
    archive_url = ""
    source_sha256 = ""
    for src in sources:
        url = src.get("url", "")
        if url:
            archive_url = url
            source_sha256 = src.get("sha256", "")
            break

    # Determine builder type and native build inputs
    native_tools = []
    builder_fn = "stdenv.mkDerivation"
    use_go = False
    use_rust = False

    if system_kind == "cmake":
        native_tools.append("cmake")
    elif system_kind == "meson":
        native_tools.extend(["meson", "ninja"])
    elif system_kind == "go":
        builder_fn = "buildGoModule"
        use_go = True
    elif system_kind == "cargo":
        builder_fn = "rustPlatform.buildRustPackage"
        use_rust = True

    lines = []

    if is_stub:
        lines.append("# THESEUS STUB — review before use")
        lines.append("")

    # Function args — base set plus any dep packages so callPackage injects them
    args = ["lib", "stdenv", "fetchurl"]
    if system_kind == "cmake":
        args.append("cmake")
    elif system_kind == "meson":
        args.extend(["meson", "ninja"])
    elif use_go:
        args = ["lib", "buildGoModule", "fetchurl"]
    elif use_rust:
        args = ["lib", "rustPlatform", "fetchurl"]

    for dep in list(build_deps) + list(host_deps) + list(runtime_deps):
        if dep and dep not in args:
            args.append(dep)

    args_str = ", ".join(args)
    lines.append(f"{{ {args_str} }}:")
    lines.append("")
    lines.append(f"{builder_fn} rec {{")
    lines.append(f'  pname = "{_nix_string(pname)}";')
    lines.append(f'  version = "{_nix_string(version)}";')
    lines.append("")

    # src
    if archive_url:
        sha = source_sha256 if source_sha256 else "lib.fakeSha256"
        if not source_sha256:
            lines.append("  src = fetchurl {")
            lines.append(f'    url = "{_nix_string(archive_url)}";')
            lines.append(f"    sha256 = lib.fakeSha256;")
            lines.append("  };")
        else:
            lines.append("  src = fetchurl {")
            lines.append(f'    url = "{_nix_string(archive_url)}";')
            lines.append(f'    sha256 = "{_nix_string(source_sha256)}";')
            lines.append("  };")
    else:
        lines.append("  # TODO: specify source")
        lines.append('  src = null; # STUB: no source URL found')

    lines.append("")

    # nativeBuildInputs
    all_native = list(native_tools) + list(build_deps)
    if all_native:
        items = " ".join(all_native)
        lines.append(f"  nativeBuildInputs = [ {items} ];")
        lines.append("")

    # buildInputs
    if host_deps:
        items = " ".join(host_deps)
        lines.append(f"  buildInputs = [ {items} ];")
        lines.append("")

    # propagatedBuildInputs
    if runtime_deps:
        items = " ".join(runtime_deps)
        lines.append(f"  propagatedBuildInputs = [ {items} ];")
        lines.append("")

    # configureFlags (autotools only)
    configure_args = build.get("configure_args", [])
    if configure_args and system_kind not in ("go", "cargo"):
        flags = " ".join(f'"{_nix_string(a)}"' for a in configure_args)
        lines.append(f"  configureFlags = [ {flags} ];")
        lines.append("")

    # meta
    lines.append("  meta = with lib; {")
    lines.append(f'    description = "{_nix_string(summary)}";')
    if homepage:
        lines.append(f'    homepage = "{_nix_string(homepage)}";')

    if licenses:
        if len(licenses) == 1:
            lines.append(f"    license = {_map_license(licenses[0])};")
        else:
            lic_list = " ".join(_map_license(l) for l in licenses)
            lines.append(f"    license = [ {lic_list} ];")

    if maintainers:
        maint_list = " ".join(f'"{_nix_string(m)}"' for m in maintainers)
        lines.append(f"    maintainers = [ {maint_list} ];")

    include_platforms = platforms.get("include", [])
    if include_platforms:
        plat_list = " ".join(f'"{p}"' for p in include_platforms)
        lines.append(f"    platforms = [ {plat_list} ];")
    else:
        lines.append("    platforms = platforms.all;")

    lines.append("  };")
    lines.append("}")

    nix = "\n".join(lines) + "\n"

    return {"default.nix": nix}
