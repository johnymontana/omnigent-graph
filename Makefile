# omnigent-neo4j-memory — developer commands.
# Run `make` (or `make help`) to see everything.
#
# Two processes are involved (see ADR-0001):
#   1. the memory SIDECAR — this package's host-level MCP server (`make serve`)
#   2. the Omnigent RUNNER — the separate `omnigent` CLI (`make install-omnigent`)
# The MEMORY_API_KEY lives only with (1); the demo agents reach it by URL.

VENV := .venv
PY   := $(VENV)/bin/python
BIN  := $(VENV)/bin

# Load .env (if present) and export its vars to every recipe's environment. This is how the sidecar,
# seed, and verify commands see MEMORY_API_KEY / MEMORY_ENDPOINT / NAM_NEO4J__*.
-include .env
export

.DEFAULT_GOAL := help

# ── Help ─────────────────────────────────────────────────────────────────────
.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: prereqs
prereqs: ## Print the external prerequisites checklist
	@echo "Omnigent needs: Python 3.12+, uv, git, Node 22 LTS (harnesses), tmux, bwrap (Linux only),"
	@echo "and model creds (ANTHROPIC_API_KEY / OPENAI_API_KEY, or a logged-in claude/codex CLI)."

# ── Setup ────────────────────────────────────────────────────────────────────
.PHONY: setup
setup: init install install-omnigent ## One-shot: .env + package venv + Omnigent CLI
	@echo "Setup done. Edit .env (MEMORY_API_KEY / MEMORY_ENDPOINT), then: make serve"

.PHONY: init
init: ## Create .env from .env.example (if missing)
	@test -f .env || (cp .env.example .env && echo "Created .env — fill in MEMORY_API_KEY.")
	@test -f .env && echo ".env present."

.PHONY: install
install: ## Create .venv and install this package (editable) + dev deps
	uv venv $(VENV)
	uv pip install --python $(PY) -e ".[dev]"
	@echo "Installed. (neo4j-agent-memory[mcp] is heavy — spaCy/GLiNER/embeddings — this is expected.)"

.PHONY: install-omnigent
install-omnigent: ## Install the Omnigent CLI (separate tool, on PATH)
	uv tool install omnigent
	@echo "Then run 'omnigent setup' once to configure model providers."

# ── Run the sidecar ──────────────────────────────────────────────────────────
.PHONY: serve
serve: ## Start the host-level memory sidecar over SSE :8000 (reads .env)
	$(BIN)/omnigent-neo4j-memory serve

.PHONY: print-cmd
print-cmd: ## Show the resolved sidecar command + backend (secrets redacted), no server started
	$(BIN)/omnigent-neo4j-memory serve --print-cmd

# ── The Polly-memory demo ────────────────────────────────────────────────────
# Needs the sidecar running (make serve, in another shell) and Omnigent installed.
.PHONY: demo
demo: ## Run 1: coder records a :ReasoningTrace; cross-vendor reviewer grounds critique in it
	@SESSION_ID=$$($(PY) -c 'from omnigent_neo4j_memory import mint_session_id; print(mint_session_id())'); \
	echo "SESSION_ID=$$SESSION_ID"; \
	SESSION_ID=$$SESSION_ID omnigent run agents/polly-memory.yaml

.PHONY: seed
seed: ## Seed synthetic prior-run knowledge (deterministic cross-run recall)
	$(PY) scripts/seed.py

.PHONY: demo-cross-run
demo-cross-run: seed ## Seed, then run a FRESH session that recalls the prior-run knowledge
	@SESSION_ID=$$($(PY) -c 'from omnigent_neo4j_memory import mint_session_id; print(mint_session_id())'); \
	echo "SESSION_ID=$$SESSION_ID (fresh session)"; \
	SESSION_ID=$$SESSION_ID omnigent run agents/polly-memory.yaml

# ── Phase-1 verification (GATING — see scripts/verify/VERIFY.md) ──────────────
.PHONY: verify
verify: ## Scriptable checks: backend auth (01) + cross-run recall (05)
	$(PY) scripts/verify/01_backend_auth.py
	$(PY) scripts/verify/05_cross_run_recall.py

.PHONY: verify-omnigent
verify-omnigent: ## Omnigent checks: sandbox egress (02) + session_id propagation (03)
	omnigent run scripts/verify/agents/egress_check.yaml
	@SESSION_ID=$$($(PY) -c 'from omnigent_neo4j_memory import mint_session_id; print(mint_session_id())'); \
	echo "SESSION_ID=$$SESSION_ID"; \
	SESSION_ID=$$SESSION_ID omnigent run scripts/verify/agents/session_check.yaml

# ── Tests ────────────────────────────────────────────────────────────────────
.PHONY: test
test: ## Unit tests (no backend)
	$(BIN)/pytest -m "not integration" -q

.PHONY: test-integration
test-integration: ## Integration tests (needs a backend: NAMS key or local Neo4j)
	$(BIN)/pytest -m integration -q

# ── Docker (containerized sidecar / local Neo4j) ─────────────────────────────
.PHONY: docker-up
docker-up: ## Start the sidecar in Docker (NAMS backend, reads .env)
	docker compose up memory-mcp

.PHONY: docker-local
docker-local: ## Start local Neo4j + the sidecar pointed at it (self-host path)
	docker compose --profile local up

.PHONY: docker-down
docker-down: ## Stop and remove the compose stack
	docker compose --profile local down

# ── Housekeeping ─────────────────────────────────────────────────────────────
.PHONY: clean
clean: ## Remove caches and build artifacts (keeps .venv and .env)
	rm -rf .pytest_cache build dist *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
