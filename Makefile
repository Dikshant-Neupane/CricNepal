# CricNepal Developer Makefile
# Cross-platform (plan task 8.1): PYTHON is the project virtualenv's
# interpreter — override it on the command line, e.g.
#   make test PYTHON=~/workspace/.scratch/cric-audit-venv/bin/python
# The wrapped commands are the canonical ones in README.md.

PYTHON ?= python

.PHONY: help refresh test dashboard clean

help:
	@echo "CricNepal Developer Commands:"
	@echo "  make refresh    - Run end-to-end data pipeline refresh"
	@echo "  make test       - Run all unit and integration tests"
	@echo "  make dashboard  - Launch Streamlit interactive dashboard locally"
	@echo "  make clean      - Clean temporary python, cache, and coverage files"

refresh:
	$(PYTHON) refresh_all.py

test:
	$(PYTHON) -m pytest tests/

dashboard:
	$(PYTHON) -m streamlit run src/dashboard/app.py

clean:
	rm -rf .pytest_cache .coverage htmlcov
	find . -type d -name "__pycache__" -exec rm -rf {} +
