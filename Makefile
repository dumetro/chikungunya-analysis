VENV ?= .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
FILE ?=

.PHONY: help venv install test pipeline dry-run app check-db clean

help:
	@echo "make install   - create venv and install dependencies"
	@echo "make test      - run unit tests"
	@echo "make dry-run   - run pipeline without writing to DB (FILE=path optional)"
	@echo "make pipeline  - run full pipeline incl. DB load (FILE=path optional)"
	@echo "make check-db  - verify database connectivity"
	@echo "make app       - launch the Streamlit dashboard"

venv:
	python3 -m venv $(VENV)

install: venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install -e .

test:
	$(PY) -m pytest -q

dry-run:
	$(PY) -m chikungunya_pipeline.pipeline run $(if $(FILE),--file $(FILE),) --dry-run

pipeline:
	$(PY) -m chikungunya_pipeline.pipeline run $(if $(FILE),--file $(FILE),)

check-db:
	$(PY) -m chikungunya_pipeline.pipeline check-db

app:
	$(VENV)/bin/streamlit run app/Home.py

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache build *.egg-info src/*.egg-info
