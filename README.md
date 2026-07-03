# omnigent-neo4j-memory

**Graph-native, cross-session, cross-agent memory for [Omnigent](https://omnigent.ai/) agents** —
backed by [neo4j-agent-memory / NAMS](https://neo4j.com/labs/agent-memory/).

> 🧪 **Neo4j Labs · experimental.** Community-supported and exploratory, not a supported product.
> Omnigent is a third-party Apache-2.0 project we integrate *with*. Both sides are alpha; interfaces
> will move. See [`docs/WRITEUP.md`](docs/WRITEUP.md) for the why.

Omnigent is a *meta-harness* — a uniform layer above coding agents (Claude Code, Codex, Pi, …) — but
it ships **no durable memory**: a session is a transcript that vanishes when you fork or start over.
This package gives that layer a shared brain. A coder agent records *what it did and why* as a
`:ReasoningTrace`; a cross-vendor reviewer grounds its critique in that trace instead of re-deriving
it from the diff; and a brand-new session recalls what prior runs learned, because the memory
workspace persists.

---

## How it's wired (the one important idea)

On alpha Omnigent, sub-agents start with an **empty environment** and the **Omnibox sandbox denies
egress by default**, so a per-agent `command:` MCP can't get its credential or reach the backend.
So we run **one host-level MCP sidecar** and every agent points at it by URL. The memory credential
lives only on that host process; sandboxes need egress to exactly one endpoint; and "everyone points
at the same endpoint" *is* the shared memory workspace. (See [ADR-0001](docs/adr/0001-host-level-mcp-server.md).)

```yaml
# drop this into any Omnigent agent (also in agents/_includes/memory-tool.yaml)
tools:
  memory:
    type: mcp
    url: http://host.docker.internal:8000   # the sidecar; the secret is NOT in here
```

## Quickstart

Prerequisites (`make prereqs`): Python 3.12+, [uv](https://docs.astral.sh/uv/), Node 22 LTS, `tmux`,
and model creds (`ANTHROPIC_API_KEY`/`OPENAI_API_KEY` or a logged-in `claude`/`codex` CLI). Then:

```bash
make setup            # .env + package venv + the Omnigent CLI (uv tool install omnigent)
$EDITOR .env          # set MEMORY_API_KEY=nams_… and MEMORY_ENDPOINT (NAMS path)
make serve            # start the host-level memory sidecar on :8000 — leave running
```

`make` targets wrap everything (`make help` to list them). Prefer to wire it by hand?

```bash
pip install omnigent-neo4j-memory          # the sidecar + helpers (pulls neo4j-agent-memory[mcp])
uv tool install omnigent                    # the Omnigent runner — a SEPARATE CLI, not our dep
cp .env.example .env                        # then edit; MEMORY_API_KEY lives here, on the host only
omnigent-neo4j-memory serve                 # host-level sidecar over SSE on :8000
```

**Backend selection is by environment:**

- **NAMS (default, hosted, zero infra):** set `MEMORY_API_KEY=nams_…` and (optionally)
  `MEMORY_ENDPOINT` in `.env`.
- **Local Neo4j (no signup):** leave `MEMORY_API_KEY` unset — `make docker-local` brings up Neo4j +
  the sidecar, using local sentence-transformers embeddings so you **don't need an OpenAI key**.

Inspect the resolved command + backend without starting anything: `make print-cmd`.

## The demo: a Polly fork with a shared brain

[`agents/polly-memory.yaml`](agents/polly-memory.yaml) is a fork of Omnigent's Polly where the coder
(vendor A) and reviewer (vendor B) share one persistent memory workspace. With the sidecar running:

```bash
make demo             # Run 1 — coder records a :ReasoningTrace; reviewer grounds critique in it
make demo-cross-run   # seed prior-run knowledge, then a FRESH session recalls it
```

Each target mints a fresh `SESSION_ID` and passes it to both sub-agents. The manual equivalent:

```bash
export SESSION_ID="$(python -c 'from omnigent_neo4j_memory import mint_session_id; print(mint_session_id())')"
omnigent run agents/polly-memory.yaml                    # Run 1
python scripts/seed.py                                    # seed prior-run knowledge
export SESSION_ID="$(python -c 'from omnigent_neo4j_memory import mint_session_id; print(mint_session_id())')"
omnigent run agents/polly-memory.yaml                    # Run 2 recalls RS256 + pyjwt incident #42
```

The cross-run recall is **seeded for reproducibility** (`scripts/seed.py`) so the demo behaves the
same every time; the recall query itself is the real one. See [`docs/WRITEUP.md`](docs/WRITEUP.md) §5.

## Verify the alpha surfaces first (recommended)

Some Omnigent alpha mechanics need hands-on confirmation before you rely on them — egress to the
sidecar, and runtime `session_id` propagation to sub-agents (the highest-risk piece). Run the gated
checks in [`scripts/verify/VERIFY.md`](scripts/verify/VERIFY.md):

```bash
make verify            # scriptable: backend auth + store/recall (01) and cross-run recall (05)
make verify-omnigent   # Omnigent-dependent: sandbox → sidecar egress (02) and session propagation (03)
```

## What's in the box

| Path | What |
|------|------|
| `src/omnigent_neo4j_memory/serve.py` | the host-level sidecar launcher (`omnigent-neo4j-memory serve`) |
| `src/omnigent_neo4j_memory/prompts/` | capture (coder) + recall (reviewer) prompt scaffolding |
| `src/omnigent_neo4j_memory/helpers.py` | session-id mint, staleness-filtering Cypher, `open_memory()` |
| `src/omnigent_neo4j_memory/experimental/policy.py` | **off-by-default** memory-backed Omnigent policy |
| `agents/polly-memory.yaml` + `agents/_includes/` | the demo + the copy-paste `tools.memory` include |
| `sample-app/` | the toy service the demo iterates on |
| `scripts/seed.py`, `scripts/verify/` | seed prior-run knowledge; the Phase-1 verification harness |
| `Makefile` | `make help` — setup, serve, demo, verify, test, docker targets |
| `docs/` | the [writeup](docs/WRITEUP.md), the [`memory:` block spec](docs/SPEC-memory-block.md), [ADRs](docs/adr/) |
| [`CONTEXT.md`](CONTEXT.md) | the project glossary (e.g. why we say "memory workspace") |

## Experimental: memory for the control plane

[`experimental/policy.py`](src/omnigent_neo4j_memory/experimental/policy.py) is an Omnigent *policy*
that records provenance and can surface prior hazards as an `ASK`. It's the most differentiated idea
here and the least settled, so it's **off by default** and never blocks an agent
([ADR-0002](docs/adr/0002-explicit-capture-policy-experimental.md)). The supported capture path is the
explicit `memory_*_trace` tools driven by the prompt scaffolding.

## Honest caveats

No automatic staleness (use `valid_until` + reviewer-side filtering); extraction is generic POLE+O (no
software-engineering schema yet); multi-tenant isolation is "different key → different workspace." See
[`docs/WRITEUP.md`](docs/WRITEUP.md) §6.

## License

[Apache-2.0](LICENSE).
