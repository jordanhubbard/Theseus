"""theseus.drivers — ecosystem-specific output generators."""
from .freebsd_ports import render as render_freebsd_ports
from .nixpkgs import render as render_nixpkgs

DRIVERS = {
    "freebsd_ports": render_freebsd_ports,
    "nixpkgs": render_nixpkgs,
}
