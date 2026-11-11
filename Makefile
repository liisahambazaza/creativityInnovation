PY := .venv/bin/python

.PHONY: help setup run phone check fast audit test fix hooks

help:
	@echo "make setup   install everything into .venv"
	@echo "make run     start the app on this computer:  http://127.0.0.1:8000"
	@echo "make phone   start it so phones on the same Wi-Fi can open it"
	@echo "make check   run every check (style, corpus audit, all tests)"
	@echo "make fast    the same, without the browser tests"
	@echo "make audit   show how much of each work's description is verified"
	@echo "make fix     tidy code style and formatting automatically"
	@echo "make hooks   run 'make fast' before every git commit"

setup:
	python3 -m venv .venv
	$(PY) -m pip install -r requirements-dev.txt

run:
	$(PY) app.py

phone:
	$(PY) app.py --lan

check:
	$(PY) scripts/check.py

fast:
	$(PY) scripts/check.py --fast

audit:
	$(PY) -m kanjian.corpus

test:
	$(PY) -m pytest -q

fix:
	$(PY) -m ruff check --fix .
	$(PY) -m ruff format .

hooks:
	git config core.hooksPath .githooks
	@echo "The checks will now run before each commit."
