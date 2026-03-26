.PHONY: all start stop restart test clean report candidates help

SNAPSHOT ?= ./snapshots/$(shell date +%Y-%m-%d)
REPORT_OUT ?= ./reports/overlap
CANDIDATES_OUT ?= ./reports/top-candidates.json

all:
	@python3 --version > /dev/null 2>&1 || (echo "Error: Python 3.10+ required" && exit 1)
	@python3 -c "import sys; assert sys.version_info >= (3, 10), 'Python 3.10+ required'" 2>/dev/null \
		|| (echo "Error: Python 3.10+ required" && exit 1)
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
	@echo ""
	@echo "Variables:"
	@echo "  SNAPSHOT            Snapshot directory (default: ./snapshots/YYYY-MM-DD)"
	@echo "  REPORT_OUT          Output dir for overlap report (default: ./reports/overlap)"
	@echo "  CANDIDATES_OUT      Output file for ranking (default: ./reports/top-candidates.json)"
