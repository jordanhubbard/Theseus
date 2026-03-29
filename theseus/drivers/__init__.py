"""theseus.drivers — ecosystem-specific output generators."""
from .freebsd_ports import render as render_freebsd_ports
from .nixpkgs import render as render_nixpkgs
from .pypi import render as render_pypi
from .npm import render as render_npm

DRIVERS = {
    "freebsd_ports": render_freebsd_ports,
    "nixpkgs": render_nixpkgs,
    "pypi": render_pypi,
    "npm": render_npm,
}
