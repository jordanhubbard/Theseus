#!/usr/bin/env python3
"""
Entry-point shim.  All logic lives in theseus/importer.py.

    python3 bootstrap_canonical_recipes.py --nixpkgs ... --ports ... --out ...
"""
from theseus.importer import main

if __name__ == "__main__":
    main()
