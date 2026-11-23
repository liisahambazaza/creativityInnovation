PY := .venv/bin/python

.PHONY: help setup run phone check fast collection search add refresh test fix hooks

help:
	@echo "make setup                        install everything into .venv"
	@echo "make run                          start the site on this computer:  http://127.0.0.1:8000"
	@echo "make phone                        start it so phones on the same Wi-Fi can open it"
	@echo "make check                        run every check (style, collection, all tests)"
	@echo "make fast                         the same, without the browser tests"
	@echo "make collection                   list the works and anything missing from them"
	@echo "make search SOURCE=npm Q=早春      search a museum (npm, met or cma)"
	@echo "make add SOURCE=npm IDS='47 1195'  import works by their number in that museum"
	@echo "make refresh                      re-import every work (keeps our own texts)"
	@echo "make fix                          tidy code style and formatting automatically"
	@echo "make hooks                        run 'make fast' before every git commit"

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

collection:
	$(PY) -m kanjian.works

search:
	$(PY) -m kanjian.importers search $(SOURCE) $(Q)

add:
	$(PY) -m kanjian.importers add $(SOURCE) $(IDS)

refresh:
	$(PY) -m kanjian.importers refresh

test:
	$(PY) -m pytest -q

fix:
	$(PY) -m ruff check --fix .
	$(PY) -m ruff format .

hooks:
	git config core.hooksPath .githooks
	@echo "The checks will now run before each commit."
