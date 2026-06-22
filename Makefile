# CricNepal Developer Makefile

.PHONY: help refresh test dashboard clean

help:
	@echo "CricNepal Developer Commands:"
	@echo "  make refresh    - Run end-to-end data pipeline refresh"
	@echo "  make test       - Run all unit and integration tests"
	@echo "  make dashboard  - Launch Streamlit interactive dashboard locally"
	@echo "  make clean      - Clean temporary python, cache, and coverage files"

refresh:
	.venv/Scripts/python.exe refresh_all.py

test:
	.venv/Scripts/python.exe -m pytest tests/ -v

dashboard:
	.venv/Scripts/streamlit.exe run src/dashboard/app.py

clean:
	rm -rf .pytest_cache .coverage htmlcov
	find . -type d -name "__pycache__" -exec rm -rf {} +
