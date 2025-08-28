UV?=uv
PY?=python
PKG_SRC=src

.PHONY: help lint test fmt run-collector load-bq run-transformations install

help:
	@echo "Targets:"
	@echo "  install                Create venv (uv) & sync deps"
	@echo "  lint                   Run ruff lint"
	@echo "  test                   Run pytest (unit & integration)"
	@echo "  fmt                    Run ruff format"
	@echo "  run-collector          Execute data collection (env controls)"
	@echo "  load-bq                Load a date partition to BigQuery"
	@echo "  run-transformations    Execute transformation SQL files"

install:
	$(UV) venv
	$(UV) pip sync requirements.txt
	@if [ -f requirements-dev.txt ]; then $(UV) pip sync requirements-dev.txt; fi

lint:
	$(UV) run ruff check $(PKG_SRC) scripts

fmt:
	$(UV) run ruff format $(PKG_SRC) scripts

test:
	PYTHONPATH=$(PWD)/src $(UV) run pytest -q tests/unit tests/integration

run-collector:
	@# Example: make run-collector START=2025-08-01 END=2025-08-01 SOURCE=all SINK=gcs
	$(UV) run python -m src.data_collection.daily_data_collector --start $(START) --end $(END) --source $(SOURCE) --sink $(SINK) $(if $(AGG),--aggregate,) $(if $(AGG_INTERVAL),--agg-interval $(AGG_INTERVAL),)

load-bq:
	@# Required vars: DATE=YYYY-MM-DD SOURCE=all|WU|TSI AGG=raw|h
	$(UV) run python scripts/load_to_bigquery.py --date $(DATE) --source $(SOURCE) --agg $(AGG) --dataset $$BQ_DATASET --project $$BQ_PROJECT --bucket $$GCS_BUCKET --prefix $$GCS_PREFIX

run-transformations:
	@# Required vars: DATE=YYYY-MM-DD DATASET=sensors PROJECT overrides BQ_PROJECT if set
	$(UV) run python scripts/run_transformations.py --date $(DATE) --dataset $(DATASET) --project $${PROJECT:-$$BQ_PROJECT} --execute
