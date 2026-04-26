.PHONY: all start stop restart test clean report candidates extract filldeps validate validate-zspecs diff sync rank bulk-build seed import-pypi import-npm import-cargo compile-zsdl verify-behavior docker-build verify-behavior-docker verify-all-specs verify-all-specs-json spec-coverage orphan-specs spec-vector-coverage validate-e2e release docs docs-serve pipeline pipeline-all synthesize synthesize-all synthesize-report synthesize-waves synthesize-waves-list synthesize-waves-status synthesize-waves-next search compare provenance-report help

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
CARGO_SEED ?= ./reports/cargo-seed.txt
IMPORT_OUT ?= ./snapshots/$(shell date +%Y-%m-%d)
IMPORT_TIMEOUT ?= 15
PYTHON ?= python3

E2E_PACKAGE ?=
E2E_RECORD ?=
E2E_ZSPEC ?=
E2E_TARGET ?=
E2E_TIMEOUT ?= 600
E2E_JSON_OUT ?=

all:
	@$(PYTHON) --version > /dev/null 2>&1 || (echo "Error: Python 3.10+ required" && exit 1)
	@$(PYTHON) -c "import sys; assert sys.version_info >= (3, 9), 'Python 3.9+ required'" 2>/dev/null \
		|| (echo "Error: Python 3.9+ required" && exit 1)
	@echo "Theseus is ready. No runtime dependencies to install (stdlib only)."
	@echo "Run 'make test' to verify. Run 'make start' for a quick demo on examples/."

start:
	@if [ -d "$(SNAPSHOT)" ]; then \
		echo "Running analysis on snapshot: $(SNAPSHOT)"; \
		$(PYTHON) tools/overlap_report.py "$(SNAPSHOT)" --out "$(REPORT_OUT)"; \
		$(PYTHON) tools/top_candidates.py "$(SNAPSHOT)" --out "$(CANDIDATES_OUT)"; \
	else \
		echo "No snapshot found at $(SNAPSHOT). Running demo on examples/..."; \
		$(PYTHON) tools/overlap_report.py examples --out reports/demo-overlap; \
		$(PYTHON) tools/top_candidates.py examples --out reports/demo-candidates.json; \
		echo "Demo reports written to reports/demo-overlap/ and reports/demo-candidates.json"; \
	fi

stop:
	@echo "No running processes to stop (Theseus is a batch analysis tool)."

restart: stop start

test: compile-zsdl
	$(PYTHON) tools/validate_zspec.py
	$(PYTHON) tools/lint_cleanroom.py --new-only
	$(PYTHON) -m pytest tests/ -v

validate-zspecs: compile-zsdl
	$(PYTHON) tools/validate_zspec.py $(ZSPECS)

lint-cleanroom:
	$(PYTHON) tools/lint_cleanroom.py --new-only

clean:
	rm -rf _build/ snapshots/ reports/demo-overlap reports/demo-candidates.json
	rm -f verify_all_specs_out.json
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache

report:
	$(PYTHON) tools/overlap_report.py "$(SNAPSHOT)" --out "$(REPORT_OUT)"

candidates:
	$(PYTHON) tools/top_candidates.py "$(SNAPSHOT)" --out "$(CANDIDATES_OUT)"

extract:
	$(PYTHON) tools/extract_candidates.py "$(SNAPSHOT)" "$(CANDIDATES_OUT)" \
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
			--exclude='/config.site.yaml' \
			./ $$target; \
	done

filldeps:
	@test -n "$(SNAPSHOT)" || (echo "Usage: make filldeps SNAPSHOT=<dir> [NIXPKGS_ROOT=path] [FILL_TIMEOUT=30]" && exit 1)
	$(PYTHON) tools/fill_nixpkgs_deps.py "$(SNAPSHOT)/nixpkgs" "$(NIXPKGS_ROOT)" \
		--timeout "$(FILL_TIMEOUT)" --batch-size "$(FILL_BATCH_SIZE)" \
		$(if $(OVERWRITE),--overwrite)

rank:
	@test -n "$(SNAPSHOT)" || (echo "Usage: make rank SNAPSHOT=<dir> [RANK_OUT=file] [RANK_TOP=500] [RANK_MIN_REFS=2]" && exit 1)
	$(PYTHON) tools/rank_by_deps.py "$(SNAPSHOT)" \
		--out "$(RANK_OUT)" --top "$(RANK_TOP)" --min-refs "$(RANK_MIN_REFS)"

seed:
	@test -n "$(SNAPSHOT)" || (echo "Usage: make seed SNAPSHOT=<freebsd_ports_dir> [PYPI_SEED=file] [NPM_SEED=file] [NPM_TOP=100]" && exit 1)
	$(PYTHON) tools/seed_from_ports.py "$(SNAPSHOT)" \
		--pypi-out "$(PYPI_SEED)" --npm-out "$(NPM_SEED)" --npm-top "$(NPM_TOP)"

import-pypi:
	@test -f "$(PYPI_SEED)" || (echo "Run 'make seed SNAPSHOT=...' first to generate $(PYPI_SEED)" && exit 1)
	$(PYTHON) theseus/importer.py --pypi-list "$(PYPI_SEED)" \
		--out "$(IMPORT_OUT)" --timeout "$(IMPORT_TIMEOUT)"

import-npm:
	@test -f "$(NPM_SEED)" || (echo "Run 'make seed SNAPSHOT=...' first to generate $(NPM_SEED)" && exit 1)
	$(PYTHON) theseus/importer.py --npm-list "$(NPM_SEED)" \
		--out "$(IMPORT_OUT)" --timeout "$(IMPORT_TIMEOUT)"

import-cargo:
	@test -f "$(CARGO_SEED)" || (echo "Create $(CARGO_SEED) with crate names (one per line), or run 'make seed-cargo'" && exit 1)
	$(PYTHON) theseus/importer.py --cargo-list "$(CARGO_SEED)" \
		--out "$(IMPORT_OUT)" --timeout "$(IMPORT_TIMEOUT)"

validate-e2e: compile-zsdl
	@test -n "$(E2E_RECORD)" || (echo "Usage: make validate-e2e E2E_RECORD=specs/zlib.json E2E_ZSPEC=_build/zspecs/zlib.zspec.json [E2E_TARGET=ubuntu.local] [E2E_JSON_OUT=out.json]" && exit 1)
	@test -n "$(E2E_ZSPEC)" || (echo "Usage: make validate-e2e E2E_RECORD=specs/zlib.json E2E_ZSPEC=_build/zspecs/zlib.zspec.json [E2E_TARGET=ubuntu.local] [E2E_JSON_OUT=out.json]" && exit 1)
	python3 tools/build_and_verify.py \
		--record "$(E2E_RECORD)" \
		--zspec "$(E2E_ZSPEC)" \
		$(if $(E2E_TARGET),--target "$(E2E_TARGET)") \
		$(if $(E2E_JSON_OUT),--json-out "$(E2E_JSON_OUT)") \
		$(if $(VERBOSE),--verbose) \
		$(if $(ALL_TARGETS),--all-targets)

bulk-build:
	@test -n "$(SNAPSHOT)" || (echo "Usage: make bulk-build SNAPSHOT=<dir> [BULK_RANKED=file] [BULK_TOP=100] [BULK_MIN_REFS=5] [BULK_JOBS=2]" && exit 1)
	$(PYTHON) tools/bulk_build.py "$(BULK_RANKED)" "$(SNAPSHOT)/freebsd_ports" "$(SNAPSHOT)/nixpkgs" \
		--top "$(BULK_TOP)" --min-refs "$(BULK_MIN_REFS)" \
		--jobs "$(BULK_JOBS)" \
		$(if $(DRIVERS),--drivers "$(DRIVERS)") \
		$(if $(DRY_RUN),--dry-run)

compile-zsdl:
	@mkdir -p _build/zspecs
	$(PYTHON) tools/zsdl_compile.py $(if $(ZSDL),$(ZSDL),--all)

verify-behavior: compile-zsdl
	$(PYTHON) tools/verify_behavior.py $(or $(ZSPEC),_build/zspecs/zlib.zspec.json) \
		$(if $(FILTER),--filter "$(FILTER)") \
		$(if $(VERBOSE),--verbose) \
		$(if $(JSON_OUT),--json-out "$(JSON_OUT)")

# ── Docker-based isolated verification ────────────────────────────────────────
# Verifies a spec inside a disposable Ubuntu 26.04 container so no packages
# are installed on the host.  Supports all backend types:
#   Python pip packages:  PIP="requests urllib3"
#   Debian apt packages:  APT="zlib1g-dev libssl-dev"   (for ctypes specs)
#   Node.js npm packages: NPM="chalk"                    (for node specs)
#   Rust cargo crates:    CARGO="serde_json"             (for rust_module specs)
# Examples:
#   make docker-build
#   make verify-behavior-docker ZSDL=zspecs/zlib.zspec.zsdl
#   make verify-behavior-docker ZSDL=zspecs/requests.zspec.zsdl PIP=requests
#   make verify-behavior-docker ZSDL=zspecs/zlib_ctypes.zspec.zsdl APT=zlib1g-dev
#   make verify-behavior-docker ZSDL=zspecs/chalk.zspec.zsdl NPM=chalk
#   make verify-behavior-docker ZSDL=zspecs/serde_json_rust.zspec.zsdl CARGO=serde_json

docker-build:
	docker build -f docker/Dockerfile.verify -t theseus-verify:latest .

verify-behavior-docker:
	@test -n "$(ZSDL)" || \
	  (echo "Usage: make verify-behavior-docker ZSDL=zspecs/foo.zspec.zsdl [PIP=pkg] [APT=pkg] [NPM=pkg] [CARGO=crate]" && exit 1)
	$(PYTHON) tools/verify_in_docker.py "$(ZSDL)" \
	  $(if $(PIP),$(foreach p,$(PIP),--pip $(p))) \
	  $(if $(APT),$(foreach p,$(APT),--apt $(p))) \
	  $(if $(NPM),$(foreach p,$(NPM),--npm $(p))) \
	  $(if $(CARGO),$(foreach p,$(CARGO),--cargo $(p))) \
	  $(if $(VERBOSE),--verbose) \
	  $(if $(FILTER),--filter "$(FILTER)") \
	  $(if $(KEEP),--keep) \
	  $(if $(REBUILD),--rebuild)

verify-all-specs: compile-zsdl
	@total=0; passed=0; failed=0; \
	for spec in _build/zspecs/*.zspec.json; do \
		echo "--- $$spec ---"; \
		if $(PYTHON) tools/verify_behavior.py "$$spec" $(if $(VERBOSE),--verbose); then \
			passed=$$((passed+1)); \
		else \
			failed=$$((failed+1)); \
		fi; \
		total=$$((total+1)); \
	done; \
	echo ""; \
	echo "=== verify-all-specs: $$total specs, $$passed passed, $$failed failed ===";

verify-all-specs-json: compile-zsdl
	$(PYTHON) tools/verify_all_specs.py $(if $(SPECS),$(SPECS)) $(if $(OUT),--out $(OUT))

# freebsd-smoke — minimum cross-platform-portable spec set. Each entry was
# manually verified to pass on FreeBSD 16.0-CURRENT (libpcap from base,
# Python 3.11, Node 24, all listed npm packages installable via standard
# `npm install --no-save`). Use this on the FreeBSD CI job to gain
# cross-OS signal without booting the full ~12k-spec verifier inside a
# slower KVM runner.
FREEBSD_SMOKE_SPECS = \
	libpcap pcapng \
	os_path json datetime \
	semver ms ulid html_tags svg_tags \
	esbuild execa cross_spawn node_forge jszip
freebsd-smoke: compile-zsdl
	@total=0; passed=0; failed=0; failures=""; \
	for name in $(FREEBSD_SMOKE_SPECS); do \
		spec=_build/zspecs/$$name.zspec.json; \
		if [ ! -f $$spec ]; then echo "MISSING $$spec"; failed=$$((failed+1)); failures="$$failures $$name"; continue; fi; \
		echo "--- $$spec ---"; \
		if $(PYTHON) tools/verify_behavior.py $$spec; then \
			passed=$$((passed+1)); \
		else \
			failed=$$((failed+1)); failures="$$failures $$name"; \
		fi; \
		total=$$((total+1)); \
	done; \
	echo ""; \
	echo "=== freebsd-smoke: $$total specs, $$passed passed, $$failed failed ==="; \
	if [ $$failed -gt 0 ]; then echo "FAIL:$$failures"; exit 1; fi

spec-coverage:
	@test -n "$(EXTRACTION_DIR)" || (echo "Usage: make spec-coverage EXTRACTION_DIR=<dir> [TOP=N] [JSON=1]" && exit 1)
	$(PYTHON) tools/spec_coverage.py "$(EXTRACTION_DIR)" $(if $(TOP),--top $(TOP)) $(if $(JSON),--json)

orphan-specs: compile-zsdl
	@test -n "$(EXTRACTION_DIR)" || (echo "Usage: make orphan-specs EXTRACTION_DIR=<dir>" && exit 1)
	$(PYTHON) tools/orphan_specs.py "$(EXTRACTION_DIR)" $(if $(JSON),--json)

spec-vector-coverage: compile-zsdl
	$(PYTHON) tools/spec_vector_coverage.py $(if $(SPECS),$(SPECS)) $(if $(JSON),--json) $(if $(MIN_SCORE),--min-score $(MIN_SCORE))

validate:
	$(PYTHON) tools/validate_record.py $(or $(PATHS),examples/)

diff:
	@test -n "$(BEFORE)" || (echo "Usage: make diff BEFORE=<dir> AFTER=<dir> [OUT=<file>]" && exit 1)
	@test -n "$(AFTER)"  || (echo "Usage: make diff BEFORE=<dir> AFTER=<dir> [OUT=<file>]" && exit 1)
	$(PYTHON) tools/diff_snapshots.py --before "$(BEFORE)" --after "$(AFTER)" $(if $(OUT),--out "$(OUT)")

release:
	bash scripts/release.sh $(or $(BUMP),patch)

docs:
	pip install mkdocs-material --quiet
	mkdocs build

docs-serve:
	pip install mkdocs-material --quiet
	mkdocs serve

# ── ZSpec pipeline (compile + verify_real + synthesize + gate + annotate) ─────
# The pipeline is the canonical way to author and validate a spec.
# Synthesis is step 3 — not a separate optional task.  A spec that cannot
# produce any passing synthesis invariants is flagged and must be revised.
#
# Use make pipeline       for a single .zspec.zsdl
# Use make pipeline-all   for every spec in zspecs/
# Use make synthesize-*   for synthesis-only bulk/wave runs (no re-compile)
# ─────────────────────────────────────────────────────────────────────────────
SYNTH_SPEC     ?=
SYNTH_ZSDL     ?=
SYNTH_MAX_ITER ?= 3
SYNTH_WORK_DIR ?= /tmp/theseus-synthesis
SYNTH_OUT      ?= reports/synthesis/audit.json
SYNTH_BACKEND  ?=
SYNTH_TOP      ?=
SYNTH_JOBS     ?= 1

pipeline:
	@test -n "$(SYNTH_ZSDL)" || \
	  (echo "Usage: make pipeline SYNTH_ZSDL=zspecs/zlib.zspec.zsdl" && exit 1)
	$(PYTHON) tools/run_pipeline.py \
	  $(SYNTH_ZSDL) \
	  --max-iterations $(SYNTH_MAX_ITER) \
	  --work-dir $(SYNTH_WORK_DIR) \
	  $(if $(SKIP_REAL_VERIFY),--skip-real-verify) \
	  $(if $(NO_GATE),--no-gate) \
	  $(if $(NO_ANNOTATE),--no-annotate) \
	  $(if $(VERBOSE),--verbose) \
	  $(if $(DRY_RUN),--dry-run) \
	  $(if $(SYNTH_OUT),--out $(SYNTH_OUT))

pipeline-all:
	$(PYTHON) tools/run_pipeline.py \
	  --all \
	  --max-iterations $(SYNTH_MAX_ITER) \
	  --work-dir $(SYNTH_WORK_DIR) \
	  --jobs $(SYNTH_JOBS) \
	  $(if $(SKIP_REAL_VERIFY),--skip-real-verify) \
	  $(if $(NO_GATE),--no-gate) \
	  $(if $(NO_ANNOTATE),--no-annotate) \
	  $(if $(VERBOSE),--verbose) \
	  $(if $(DRY_RUN),--dry-run) \
	  $(if $(SYNTH_OUT),--out $(SYNTH_OUT))

synthesize: compile-zsdl
	@test -n "$(SYNTH_SPEC)" || \
	  (echo "Usage: make synthesize SYNTH_SPEC=_build/zspecs/zlib.zspec.json" && exit 1)
	$(PYTHON) tools/synthesize_spec.py \
	  $(SYNTH_SPEC) \
	  --max-iterations $(SYNTH_MAX_ITER) \
	  --work-dir $(SYNTH_WORK_DIR) \
	  $(if $(VERBOSE),--verbose) \
	  $(if $(NO_ANNOTATE),--no-annotate) \
	  $(if $(JSON_OUT),--json-out $(JSON_OUT)) \
	  $(if $(DRY_RUN),--dry-run)

synthesize-all: compile-zsdl
	$(PYTHON) tools/synthesize_all_specs.py \
	  --out $(SYNTH_OUT) \
	  --max-iterations $(SYNTH_MAX_ITER) \
	  --jobs $(SYNTH_JOBS) \
	  $(if $(SYNTH_BACKEND),--filter-backend $(SYNTH_BACKEND)) \
	  $(if $(SYNTH_TOP),--top $(SYNTH_TOP)) \
	  $(if $(NO_ANNOTATE),--no-annotate) \
	  $(if $(DRY_RUN),--dry-run)

synthesize-report:
	@test -f "$(SYNTH_OUT)" || (echo "Run 'make synthesize-all' first" && exit 1)
	$(PYTHON) -c "\
	  import json; d=json.load(open('$(SYNTH_OUT)')); s=d['summary']; \
	  print(f\"{s['total_specs']} specs | success={s['success_count']} \
	  partial={s['partial_count']} failed={s['failed_count']} \
	  infeasible={s['infeasible_count']} | rate={s['synthesizability_rate']:.1%}\")"

# Wave-based pipeline (mirrors the PLAN.md wave-series spec creation approach)
SYNTH_WAVE     ?=
SYNTH_TIMEOUT  ?= 0

synthesize-waves-list: compile-zsdl
	$(PYTHON) tools/synthesize_waves.py --list

synthesize-waves-status:
	$(PYTHON) tools/synthesize_waves.py --status

synthesize-waves-next: compile-zsdl
	$(PYTHON) tools/synthesize_waves.py --next \
	  --max-iterations $(SYNTH_MAX_ITER) \
	  --jobs $(SYNTH_JOBS) \
	  --timeout $(SYNTH_TIMEOUT) \
	  $(if $(NO_ANNOTATE),--no-annotate) \
	  $(if $(VERBOSE),--verbose) \
	  $(if $(FORCE),--force)

synthesize-waves: compile-zsdl
	@test -n "$(SYNTH_WAVE)" || \
	  (echo "Usage: make synthesize-waves SYNTH_WAVE=s1   (use make synthesize-waves-list to see waves)" && exit 1)
	$(PYTHON) tools/synthesize_waves.py --wave $(SYNTH_WAVE) \
	  --max-iterations $(SYNTH_MAX_ITER) \
	  --jobs $(SYNTH_JOBS) \
	  --timeout $(SYNTH_TIMEOUT) \
	  $(if $(NO_ANNOTATE),--no-annotate) \
	  $(if $(VERBOSE),--verbose) \
	  $(if $(FORCE),--force)

# ── Discovery, comparison, and provenance ────────────────────────────────────
QUERY      ?=
SPEC1      ?=
SPEC2      ?=
SPEC       ?=
PROV_OUT   ?=

search:
	$(PYTHON) tools/search_specs.py $(QUERY) \
	  $(if $(BACKEND),--backend $(BACKEND)) \
	  $(if $(VERIFIED),--verified) \
	  $(if $(LIST),--list) \
	  $(if $(JSON),--json)

compare: compile-zsdl
	@test -n "$(SPEC1)" || (echo "Usage: make compare SPEC1=<spec1> SPEC2=<spec2>" && exit 1)
	@test -n "$(SPEC2)" || (echo "Usage: make compare SPEC1=<spec1> SPEC2=<spec2>" && exit 1)
	$(PYTHON) tools/compare_specs.py "$(SPEC1)" "$(SPEC2)" $(if $(JSON),--json)

provenance-report:
	@test -n "$(SPEC)" || (echo "Usage: make provenance-report SPEC=zspecs/zlib.zspec.zsdl" && exit 1)
	$(PYTHON) tools/provenance_report.py "$(SPEC)" \
	  $(if $(JSON),--json) \
	  $(if $(PROV_OUT),--out "$(PROV_OUT)")

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
	@echo "  make import-cargo   Fetch Cargo crate metadata from crates.io (requires cargo-seed.txt, skips GPL)"
	@echo "  make compile-zsdl   Compile zspecs/*.zspec.zsdl → _build/zspecs/*.zspec.json (ZSDL=file for one)"
	@echo "  make verify-behavior  Run Z-layer behavioral spec verifier (ZSPEC=path, default: _build/zspecs/zlib.zspec.json)"
	@echo "  make docker-build   Build the Ubuntu 26.04 verification sandbox image (theseus-verify:latest)"
	@echo "  make verify-behavior-docker  Verify a spec in a disposable Docker container (ZSDL=path [PIP=pkg] [APT=pkg] [NPM=pkg] [CARGO=crate])"
	@echo "  make validate-e2e   Build from source and verify behavioral spec (E2E_RECORD=, E2E_ZSPEC=)"
	@echo "  make verify-all-specs Run every spec in _build/zspecs/ and report aggregate pass/fail (VERBOSE=1 for details)"
	@echo "  make verify-all-specs-json  Run all specs and write JSON results (OUT=file optional, SPECS=paths optional)"
	@echo "  make spec-coverage    Report which extracted candidates have a behavioral spec (EXTRACTION_DIR= required)"
	@echo "  make orphan-specs     Report which compiled specs have no matching extraction record (EXTRACTION_DIR= required)"
	@echo "  make validate       Validate records (PATHS=dir or file, default: examples/)"
	@echo "  make diff           Diff two snapshots (BEFORE=dir AFTER=dir [OUT=file])"
	@echo "  make release        Cut a release (BUMP=major|minor|patch, default: patch)"
	@echo "  make docs           Build user guide static site (requires mkdocs-material)"
	@echo "  make docs-serve     Serve user guide locally at http://127.0.0.1:8000"
	@echo ""
	@echo "Discovery, comparison, and provenance:"
	@echo "  make search             Search specs by name/keyword (QUERY=term, BACKEND=type, VERIFIED=1)"
	@echo "  make compare            Compare two specs (SPEC1=path SPEC2=path [JSON=1])"
	@echo "  make provenance-report  Generate provenance attestation (SPEC=zspecs/foo.zspec.zsdl [PROV_OUT=file])"
	@echo ""
	@echo "ZSpec pipeline (compile → verify_real → synthesize → gate → annotate):"
	@echo "  make pipeline              Full pipeline for one spec (SYNTH_ZSDL=zspecs/zlib.zspec.zsdl)"
	@echo "  make pipeline-all          Full pipeline for all specs in zspecs/"
	@echo ""
	@echo "Synthesis layer (synthesis-only, requires prior compile-zsdl):"
	@echo "  make synthesize            Synthesise one compiled spec (SYNTH_SPEC=_build/zspecs/zlib.zspec.json)"
	@echo "  make synthesize-all        Synthesise all compiled specs (SYNTH_BACKEND=, SYNTH_TOP=, SYNTH_JOBS=)"
	@echo "  make synthesize-report     Print summary of last audit report"
	@echo "  make synthesize-waves-list List all synthesis waves and their status"
	@echo "  make synthesize-waves-status Per-spec synthesis status"
	@echo "  make synthesize-waves-next Run the next pending synthesis wave"
	@echo "  make synthesize-waves      Run a specific wave (SYNTH_WAVE=s1)"
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
