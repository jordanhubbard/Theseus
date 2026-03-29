.PHONY: all start stop restart test clean report candidates extract filldeps validate diff sync rank help

SNAPSHOT ?= ./snapshots/$(shell date +%Y-%m-%d)
REPORT_OUT ?= ./reports/overlap
CANDIDATES_OUT ?= ./reports/top-candidates.json
EXTRACT_OUT ?= ./reports/extractions
EXTRACT_TOP ?= 50
NIXPKGS_ROOT ?= ~/.nix-defexpr/channels/nixpkgs
SYNC_TARGET ?= freebsd.local:Src/Theseus/
FILL_TIMEOUT ?= 30
RANK_OUT ?= ./reports/ranked-by-deps.json
RANK_TOP ?= 500
RANK_MIN_REFS ?= 2

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

test:
	python3 -m pytest tests/ -v

clean:
	rm -rf snapshots/ reports/demo-overlap reports/demo-candidates.json
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
	rsync -av --delete \
		--exclude='.git' \
		--exclude='__pycache__' --exclude='*.pyc' --exclude='.pytest_cache' \
		--exclude='snapshots/' \
		--exclude='output/' \
		--exclude='stubs/' \
		--exclude='/config.yaml' \
		./ $(SYNC_TARGET)

filldeps:
	@test -n "$(SNAPSHOT)" || (echo "Usage: make filldeps SNAPSHOT=<dir> [NIXPKGS_ROOT=path] [FILL_TIMEOUT=30]" && exit 1)
	python3 tools/fill_nixpkgs_deps.py "$(SNAPSHOT)/nixpkgs" "$(NIXPKGS_ROOT)" \
		--timeout "$(FILL_TIMEOUT)" $(if $(OVERWRITE),--overwrite)

rank:
	@test -n "$(SNAPSHOT)" || (echo "Usage: make rank SNAPSHOT=<dir> [RANK_OUT=file] [RANK_TOP=500] [RANK_MIN_REFS=2]" && exit 1)
	python3 tools/rank_by_deps.py "$(SNAPSHOT)" \
		--out "$(RANK_OUT)" --top "$(RANK_TOP)" --min-refs "$(RANK_MIN_REFS)"

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
	@echo "  make test           Run test suite (requires pytest)"
	@echo "  make clean          Remove generated artifacts"
	@echo "  make report         Run overlap report (requires SNAPSHOT=)"
	@echo "  make candidates     Run candidate ranking (requires SNAPSHOT=)"
	@echo "  make extract        Run phase Z extraction (requires SNAPSHOT= and CANDIDATES_OUT)"
	@echo "  make filldeps       Fill nixpkgs dep lists (requires SNAPSHOT= and NIXPKGS_ROOT=)"
	@echo "  make rank           Rank packages by reverse-dep fan-in (requires SNAPSHOT=)"
	@echo "  make sync           Rsync code to SYNC_TARGET (safe: excludes snapshots, output, stubs)"
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
