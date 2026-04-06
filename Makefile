.PHONY: all start stop restart test clean report candidates extract filldeps validate validate-zspecs diff sync rank bulk-build seed import-pypi import-npm compile-zsdl verify-behavior verify-all-specs verify-all-specs-json spec-coverage orphan-specs spec-vector-coverage help

SNAPSHOT ?= ./snapshots/$(shell date +%Y-%m-%d)
REPORT_OUT ?= ./reports/overlap
CANDIDATES_OUT ?= ./reports/top-candidates.json
EXTRACT_OUT ?= ./reports/extractions
EXTRACT_TOP ?= 50
NIXPKGS_ROOT ?= ~/.nix-defexpr/channels/nixpkgs
SYNC_TARGETS ?= freebsd.local:Src/Theseus/ ubuntu.local:Src/Theseus/
FILL_TIMEOUT ?= 60
FILL_BATCH_SIZE ?= 50
RANK_OUT ?= ./reports/ranked-by-deps.json
RANK_TOP ?= 500
RANK_MIN_REFS ?= 2
BULK_RANKED ?= ./reports/ranked-by-deps.json
BULK_TOP ?= 100
BULK_MIN_REFS ?= 5
BULK_JOBS ?= 2
PYPI_SEED ?= ./reports/pypi-seed.txt
NPM_SEED ?= ./reports/npm-seed.txt
NPM_TOP ?= 100
IMPORT_OUT ?= ./snapshots/$(shell date +%Y-%m-%d)
IMPORT_TIMEOUT ?= 15

all:
	@python3 --version > /dev/null 2>&1 || (echo "Error: Python 3.10+ required" && exit 1)
	@python3 -c "import sys; assert sys.version_info >= (3, 9), 'Python 3.9+ required'" 2>/dev/null \
		|| (echo "Error: Python 3.9+ required" && exit 1)
	@echo "Theseus is ready. No runtime dependencies to install (stdlib only)."
	@echo "Run 'make test' to verify. Run 'make start' for a quick demo on examples/."

start:
	@if [ -d "$(SNAPSHOT)" ]; then \
		echo "Running analysis on snapshot: $(SNAPSHOT)"; \
		python3 tools/overlap_report.py "$(SNAPSHOT)" --out "$(REPORT_OUT)"; \
		python3 tools/top_candidates.py "$(SNAPSHOT)" --out "$(CANDIDATES_OUT)"; \
	else \
		echo "No snapshot found at $(SNAPSHOT). Running demo on examples/..."; \
		python3 tools/overlap_report.py examples --out reports/demo-overlap; \
		python3 tools/top_candidates.py examples --out reports/demo-candidates.json; \
		echo "Demo reports written to reports/demo-overlap/ and reports/demo-candidates.json"; \
	fi

stop:
	@echo "No running processes to stop (Theseus is a batch analysis tool)."

restart: stop start

test: compile-zsdl
	python3 tools/validate_zspec.py
	python3 -m pytest tests/ -v

validate-zspecs: compile-zsdl
	python3 tools/validate_zspec.py $(ZSPECS)

clean:
	rm -rf _build/ snapshots/ reports/demo-overlap reports/demo-candidates.json
	rm -f verify_all_specs_out.json
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache

report:
	python3 tools/overlap_report.py "$(SNAPSHOT)" --out "$(REPORT_OUT)"

candidates:
	python3 tools/top_candidates.py "$(SNAPSHOT)" --out "$(CANDIDATES_OUT)"

extract:
	python3 tools/extract_candidates.py "$(SNAPSHOT)" "$(CANDIDATES_OUT)" \
		--out "$(EXTRACT_OUT)" --top "$(EXTRACT_TOP)"

sync:
	@for target in $(SYNC_TARGETS); do \
		echo "Syncing to $$target ..."; \
		rsync -av --delete \
			--exclude='.git' \
			--exclude='__pycache__' --exclude='*.pyc' --exclude='.pytest_cache' \
			--exclude='snapshots/' \
			--exclude='output/' \
			--exclude='stubs/' \
			--exclude='/config.yaml' \
			./ $$target; \
	done

filldeps:
	@test -n "$(SNAPSHOT)" || (echo "Usage: make filldeps SNAPSHOT=<dir> [NIXPKGS_ROOT=path] [FILL_TIMEOUT=30]" && exit 1)
	python3 tools/fill_nixpkgs_deps.py "$(SNAPSHOT)/nixpkgs" "$(NIXPKGS_ROOT)" \
		--timeout "$(FILL_TIMEOUT)" --batch-size "$(FILL_BATCH_SIZE)" \
		$(if $(OVERWRITE),--overwrite)

rank:
	@test -n "$(SNAPSHOT)" || (echo "Usage: make rank SNAPSHOT=<dir> [RANK_OUT=file] [RANK_TOP=500] [RANK_MIN_REFS=2]" && exit 1)
	python3 tools/rank_by_deps.py "$(SNAPSHOT)" \
		--out "$(RANK_OUT)" --top "$(RANK_TOP)" --min-refs "$(RANK_MIN_REFS)"

seed:
	@test -n "$(SNAPSHOT)" || (echo "Usage: make seed SNAPSHOT=<freebsd_ports_dir> [PYPI_SEED=file] [NPM_SEED=file] [NPM_TOP=100]" && exit 1)
	python3 tools/seed_from_ports.py "$(SNAPSHOT)" \
		--pypi-out "$(PYPI_SEED)" --npm-out "$(NPM_SEED)" --npm-top "$(NPM_TOP)"

import-pypi:
	@test -f "$(PYPI_SEED)" || (echo "Run 'make seed SNAPSHOT=...' first to generate $(PYPI_SEED)" && exit 1)
	python3 theseus/importer.py --pypi-list "$(PYPI_SEED)" \
		--out "$(IMPORT_OUT)" --timeout "$(IMPORT_TIMEOUT)"

import-npm:
	@test -f "$(NPM_SEED)" || (echo "Run 'make seed SNAPSHOT=...' first to generate $(NPM_SEED)" && exit 1)
	python3 theseus/importer.py --npm-list "$(NPM_SEED)" \
		--out "$(IMPORT_OUT)" --timeout "$(IMPORT_TIMEOUT)"

bulk-build:
	@test -n "$(SNAPSHOT)" || (echo "Usage: make bulk-build SNAPSHOT=<dir> [BULK_RANKED=file] [BULK_TOP=100] [BULK_MIN_REFS=5] [BULK_JOBS=2]" && exit 1)
	python3 tools/bulk_build.py "$(BULK_RANKED)" "$(SNAPSHOT)/freebsd_ports" "$(SNAPSHOT)/nixpkgs" \
		--top "$(BULK_TOP)" --min-refs "$(BULK_MIN_REFS)" \
		--jobs "$(BULK_JOBS)" \
		$(if $(DRIVERS),--drivers "$(DRIVERS)") \
		$(if $(DRY_RUN),--dry-run)

compile-zsdl:
	@mkdir -p _build/zspecs
	python3 tools/zsdl_compile.py $(if $(ZSDL),$(ZSDL),--all)

verify-behavior: compile-zsdl
	python3 tools/verify_behavior.py $(or $(ZSPEC),_build/zspecs/zlib.zspec.json) \
		$(if $(FILTER),--filter "$(FILTER)") \
		$(if $(VERBOSE),--verbose) \
		$(if $(JSON_OUT),--json-out "$(JSON_OUT)")

verify-all-specs: compile-zsdl
	@total=0; passed=0; failed=0; \
	for spec in _build/zspecs/*.zspec.json; do \
		echo "--- $$spec ---"; \
		if python3 tools/verify_behavior.py "$$spec" $(if $(VERBOSE),--verbose); then \
			passed=$$((passed+1)); \
		else \
			failed=$$((failed+1)); \
		fi; \
		total=$$((total+1)); \
	done; \
	echo ""; \
	echo "=== verify-all-specs: $$total specs, $$passed passed, $$failed failed ===";

verify-all-specs-json: compile-zsdl
	python3 tools/verify_all_specs.py $(if $(SPECS),$(SPECS)) $(if $(OUT),--out $(OUT))

spec-coverage:
	@test -n "$(EXTRACTION_DIR)" || (echo "Usage: make spec-coverage EXTRACTION_DIR=<dir> [TOP=N] [JSON=1]" && exit 1)
	python3 tools/spec_coverage.py "$(EXTRACTION_DIR)" $(if $(TOP),--top $(TOP)) $(if $(JSON),--json)

orphan-specs: compile-zsdl
	@test -n "$(EXTRACTION_DIR)" || (echo "Usage: make orphan-specs EXTRACTION_DIR=<dir>" && exit 1)
	python3 tools/orphan_specs.py "$(EXTRACTION_DIR)" $(if $(JSON),--json)

spec-vector-coverage: compile-zsdl
	python3 tools/spec_vector_coverage.py $(if $(SPECS),$(SPECS)) $(if $(JSON),--json) $(if $(MIN_SCORE),--min-score $(MIN_SCORE))

validate:
	python3 tools/validate_record.py $(or $(PATHS),examples/)

diff:
	@test -n "$(BEFORE)" || (echo "Usage: make diff BEFORE=<dir> AFTER=<dir> [OUT=<file>]" && exit 1)
	@test -n "$(AFTER)"  || (echo "Usage: make diff BEFORE=<dir> AFTER=<dir> [OUT=<file>]" && exit 1)
	python3 tools/diff_snapshots.py --before "$(BEFORE)" --after "$(AFTER)" $(if $(OUT),--out "$(OUT)")

help:
	@echo "Theseus — canonical package recipe toolchain"
	@echo ""
	@echo "Targets:"
	@echo "  make / make all     Check Python version, print usage"
	@echo "  make start          Run analysis (SNAPSHOT=path, or demo on examples/)"
	@echo "  make stop           No-op (batch tool, no daemon)"
	@echo "  make restart        stop + start"
	@echo "  make test           Validate Z-specs then run test suite (requires pytest)"
	@echo "  make validate-zspecs  Validate Z-spec JSON files against schema (ZSPECS=path optional)"
	@echo "  make clean          Remove generated artifacts"
	@echo "  make report         Run overlap report (requires SNAPSHOT=)"
	@echo "  make candidates     Run candidate ranking (requires SNAPSHOT=)"
	@echo "  make extract        Run phase Z extraction (requires SNAPSHOT= and CANDIDATES_OUT)"
	@echo "  make filldeps       Fill nixpkgs dep lists (requires SNAPSHOT= and NIXPKGS_ROOT=)"
	@echo "  make rank           Rank packages by reverse-dep fan-in (requires SNAPSHOT=)"
	@echo "  make sync           Rsync code to SYNC_TARGETS (safe: excludes snapshots, output, stubs)"
	@echo "  make bulk-build     Full pipeline: ranked list -> specs/ (requires SNAPSHOT=)"
	@echo "  make seed           Generate PyPI/npm seed lists from freebsd_ports snapshot"
	@echo "  make import-pypi    Fetch PyPI package metadata (requires pypi-seed.txt)"
	@echo "  make import-npm     Fetch npm package metadata (requires npm-seed.txt)"
	@echo "  make compile-zsdl   Compile zspecs/*.zspec.zsdl → _build/zspecs/*.zspec.json (ZSDL=file for one)"
	@echo "  make verify-behavior  Run Z-layer behavioral spec verifier (ZSPEC=path, default: _build/zspecs/zlib.zspec.json)"
	@echo "  make verify-all-specs Run every spec in _build/zspecs/ and report aggregate pass/fail (VERBOSE=1 for details)"
	@echo "  make verify-all-specs-json  Run all specs and write JSON results (OUT=file optional, SPECS=paths optional)"
	@echo "  make spec-coverage    Report which extracted candidates have a behavioral spec (EXTRACTION_DIR= required)"
	@echo "  make orphan-specs     Report which compiled specs have no matching extraction record (EXTRACTION_DIR= required)"
	@echo "  make validate       Validate records (PATHS=dir or file, default: examples/)"
	@echo "  make diff           Diff two snapshots (BEFORE=dir AFTER=dir [OUT=file])"
	@echo ""
	@echo "Variables:"
	@echo "  SNAPSHOT            Snapshot directory (default: ./snapshots/YYYY-MM-DD)"
	@echo "  REPORT_OUT          Output dir for overlap report (default: ./reports/overlap)"
	@echo "  CANDIDATES_OUT      Output file for ranking (default: ./reports/top-candidates.json)"
	@echo "  EXTRACT_OUT         Output dir for phase Z extraction (default: ./reports/extractions)"
	@echo "  EXTRACT_TOP         How many top candidates to extract (default: 50)"
	@echo "  NIXPKGS_ROOT        nixpkgs checkout for filldeps (default: ~/.nix-defexpr/channels/nixpkgs)"
	@echo "  FILL_TIMEOUT        Per-package dep eval timeout secs (default: 30)"
	@echo "  PATHS               Path(s) for 'make validate' (default: examples/)"
	@echo "  BEFORE / AFTER      Snapshot dirs for 'make diff'"
	@echo "  OUT                 Output file for 'make diff'"
	@echo "  RANK_OUT            Output file for ranking (default: ./reports/ranked-by-deps.json)"
	@echo "  RANK_TOP            How many top entries to emit (default: 500)"
	@echo "  RANK_MIN_REFS       Minimum reverse-dep count to include (default: 2)"
	@echo "  BULK_RANKED         Ranked JSON input for bulk-build (default: ./reports/ranked-by-deps.json)"
	@echo "  BULK_TOP            How many top packages to build (default: 100)"
	@echo "  BULK_MIN_REFS       Minimum refs for bulk-build filter (default: 5)"
	@echo "  BULK_JOBS           Parallel build threads (default: 2)"
	@echo "  DRIVERS             Comma-separated drivers for bulk-build (default: freebsd_ports,nixpkgs)"
	@echo "  DRY_RUN             Set to any value to pass --dry-run to bulk-build"
	@echo "  PYPI_SEED           PyPI seed list file (default: ./reports/pypi-seed.txt)"
	@echo "  NPM_SEED            npm seed list file (default: ./reports/npm-seed.txt)"
	@echo "  NPM_TOP             Number of curated npm packages in seed (default: 100)"
	@echo "  IMPORT_OUT          Output snapshot dir for import-pypi/npm (default: ./snapshots/YYYY-MM-DD)"
	@echo "  IMPORT_TIMEOUT      HTTP timeout for PyPI/npm fetches in secs (default: 15)"
	@echo "  SYNC_TARGETS        Space-separated rsync destinations (default: freebsd.local ubuntu.local)"
