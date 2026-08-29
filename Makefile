.DEFAULT_GOAL := help
.PHONY: help setup run resume watch eval test lint

TICKET ?= QA-101
DECISION ?= approve
NOTES ?=

help: ## list targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-10s %s\n", $$1, $$2}'

setup: ## install deps (uv) and create .env from template if missing
	uv sync
	@test -f .env || (cp .env.example .env && echo "created .env — fill in your API keys")

run: ## open a QA episode: make run TICKET=QA-103
	uv run python -m qa_agent.cli run $(TICKET)

resume: ## resume an interrupted episode: make resume TICKET=QA-103 DECISION=approve|revise|abort NOTES="..."
	uv run python -m qa_agent.cli resume $(TICKET) --decision $(DECISION) --notes "$(NOTES)"

watch: ## poll the board; open episodes as cards hit ready-for-qa (ctrl-c to stop)
	uv run python -m qa_agent.cli watch

eval: ## push the LangSmith dataset and run the eval experiment
	uv run python -m evals.dataset
	uv run python -m evals.run_evals

test: ## run unit tests
	uv run pytest

lint: ## ruff check
	uv run ruff check src tests evals
