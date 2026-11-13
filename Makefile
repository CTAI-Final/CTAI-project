PY ?= python
export PYTHONPATH := src

.DEFAULT_GOAL := help

.PHONY: help install test demo data lint clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

install: ## Install the package in editable mode
	$(PY) -m pip install -e .

test: ## Run the unit test suite
	$(PY) -m unittest discover -s tests -v

demo: ## Run all three algorithms on one practice scenario (smoke test)
	$(PY) -m ctai demo

data: ## Regenerate the committed practice scenarios
	$(PY) scripts/generate_practice_data.py

lint: ## Static checks with ruff
	$(PY) -m ruff check src tests scripts

clean: ## Remove caches and run artefacts
	rm -rf .pytest_cache .ruff_cache build dist *.egg-info
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
	find results -type f ! -name '.gitkeep' -delete
