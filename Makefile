PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)

.PHONY: install lint format test

install:
	$(PYTHON) -m pip install -r requirements-dev.txt

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .
	$(PYTHON) -m pyright --pythonpath $(PYTHON)

format:
	$(PYTHON) -m ruff check --select I --fix .
	$(PYTHON) -m ruff format .

test:
	$(PYTHON) -m pytest
