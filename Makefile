UV?=uv
PY?=python
PKG_SRC=src

.PHONY: help lint test fmt run-collector load-bq run-transformations install create-external materialize e2e verify-outputs

help:
	@echo "Targets:"
	@echo "  install                Create venv (uv) & sync deps"
	@echo "  lint                   Run ruff lint"
	@echo "  test                   Run pytest (unit & integration)"
	@echo "  fmt                    Run ruff format"
	@echo "  run-collector          Execute data collection (env controls)"
	@echo "  load-bq                Load a date partition to BigQuery"
	@echo "  run-transformations    Execute transformation SQL files"
	@echo "  create-external        Create or replace BQ external tables over GCS raw Parquet"
	@echo "  materialize            Materialize daily partitions from externals into native tables"
	@echo "  e2e                    End-to-end: collect -> materialize -> transformations"
	@echo "  verify-outputs         Print BigQuery counts per date for key tables"

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

create-external:
	@# Uses env: BQ_PROJECT/BQ_DATASET/GCS_BUCKET/GCS_PREFIX
	$(UV) run python scripts/create_bq_external_tables.py --project $${PROJECT:-$$BQ_PROJECT} --dataset $${DATASET:-$$BQ_DATASET} --bucket $$GCS_BUCKET --prefix $${PREFIX:-$$GCS_PREFIX}

materialize:
	@# Required vars: START=YYYY-MM-DD END=YYYY-MM-DD DATASET (defaults to BQ_DATASET)
	$(UV) run python scripts/materialize_partitions.py --project $${PROJECT:-$$BQ_PROJECT} --dataset $${DATASET:-$$BQ_DATASET} --start $(START) --end $(END) --sources $${SOURCES:-all} --execute

e2e:
	@# Example: make e2e START=2025-09-13 END=2025-09-19 DATASET=sensors SOURCE=all SINK=gcs
	@test -n "$(START)" || (echo "START is required" && exit 1)
	@test -n "$(END)" || (echo "END is required" && exit 1)
	$(MAKE) run-collector START=$(START) END=$(END) SOURCE=$${SOURCE:-all} SINK=$${SINK:-gcs}
	$(MAKE) create-external PROJECT=$${PROJECT:-$$BQ_PROJECT} DATASET=$${DATASET:-$$BQ_DATASET}
	$(MAKE) materialize START=$(START) END=$(END) PROJECT=$${PROJECT:-$$BQ_PROJECT} DATASET=$${DATASET:-$$BQ_DATASET}
	# Run transformations for END date (use proc_date as END)
	$(MAKE) run-transformations DATE=$(END) DATASET=$${DATASET:-$$BQ_DATASET} PROJECT=$${PROJECT:-$$BQ_PROJECT}

verify-outputs:
	@# Required vars: START=YYYY-MM-DD END=YYYY-MM-DD DATASET (defaults from env)
	$(UV) run python scripts/verify_outputs.py --project $${PROJECT:-$$BQ_PROJECT} --dataset $${DATASET:-$$BQ_DATASET} --start $(START) --end $(END)
