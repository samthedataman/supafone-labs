.PHONY: install test test-provider-contracts test-live-injection lint fmt docs build clean

PY ?= python3

install:
	$(PY) -m pip install -e .[all]
	$(PY) -m pip install pytest pytest-asyncio ruff

test:
	PYTHONPATH=src $(PY) -m pytest tests -q

test-provider-contracts:
	PYTHONPATH=src $(PY) -m pytest tests/test_adapters.py tests/test_facade_all_providers.py tests/test_provider_injection_e2e.py -q

test-live-injection:
	PYTHONPATH=src $(PY) -m pytest tests -q -m live_injection

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
