.PHONY: install test lint fmt docs build clean

PY ?= python3

install:
	$(PY) -m pip install -e .[all]
	$(PY) -m pip install pytest pytest-asyncio ruff

test:
	$(PY) -m pytest tests -q

lint:
	$(PY) -m ruff check src

fmt:
	$(PY) -m ruff format src

docs:
	$(PY) -m mkdocs serve

build:
	$(PY) -m build

clean:
	rm -rf dist build *.egg-info src/*.egg-info site
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
