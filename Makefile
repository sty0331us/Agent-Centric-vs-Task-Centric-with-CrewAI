.PHONY: install pdf test chat chat-agent compare doctor lint

PYTHON ?= python3.12

install:
	$(PYTHON) -m venv .venv
	.venv/bin/pip install -U pip
	.venv/bin/pip install -e ".[dev,pdf]"

pdf:
	.venv/bin/python scripts/generate_faq_pdf.py

test:
	.venv/bin/pytest

chat:
	.venv/bin/python -m daily_dish --mode task_centric

chat-agent:
	.venv/bin/python -m daily_dish --mode agent_centric

compare:
	.venv/bin/python -m daily_dish --mode compare -q "What are the timings?"

doctor:
	.venv/bin/python -m daily_dish --doctor

lint:
	.venv/bin/ruff check src tests scripts
	.venv/bin/mypy src/daily_dish
