# Phase 1 — hands-on verification (GATING)

These five checks de-risk the alpha Omnigent + neo4j-agent-memory surfaces the demo depends on. The
plan treats them as a gate: confirm them (or adopt the documented fallback) before relying on the
Polly-memory demo. They can't run in CI — they need a real `MEMORY_API_KEY` (or local Neo4j) and, for
checks 02–03, an Omnigent install.

Set up your env first: `cp .env.example .env` and fill it in, then `set -a; . ./.env; set +a`.

| # | Check | How | Pass criteria |
|---|-------|-----|---------------|
| 01 | Local MCP / SDK → backend auth | `python scripts/verify/01_backend_auth.py` | store + recall round-trips against your backend |
| 02 | Sandbox → host MCP egress | `omnigent run scripts/verify/agents/egress_check.yaml` | the agent calls a memory tool via `url:` with no "connection refused / blocked by proxy" |
| 03 | `session_id` propagation (HIGHEST RISK) | `omnigent run scripts/verify/agents/session_check.yaml` | both sub-agents print the SAME `${SESSION_ID}`, and agent B recalls agent A's message |
| 04 | Reviewer reads `:ReasoningTrace` | see "Check 04" below | the trace + `:HAS_STEP`/`:TOUCHED` edges are queryable by a second reader |
| 05 | Cross-run workspace recall | `python scripts/verify/05_cross_run_recall.py` | a new session (no session filter) recalls entities written by a prior session |

---

## Check 02 — sandbox egress

`scripts/verify/agents/egress_check.yaml` declares the `memory` tool via `url:` and asks the agent to
call one memory tool. The Omnibox sandbox denies egress by default, so this tells you which hostname
the sandbox can use to reach the host-level sidecar:

- host process + host agent → `http://localhost:8000`
- containerized sandbox → `http://host.docker.internal:8000`

If it's blocked, find the allow-list syntax for your Omnigent build (or move the sidecar to a host the
sandbox can reach) and record the resolution in an ADR. **The whole demo depends on this working.**

## Check 03 — session_id propagation (highest risk)

`scripts/verify/agents/session_check.yaml` defines two sub-agents that both interpolate `${SESSION_ID}`
into their prompts. Export a value first:

```bash
export SESSION_ID="$(python -c 'from omnigent_neo4j_memory import mint_session_id; print(mint_session_id())')"
omnigent run scripts/verify/agents/session_check.yaml
```

PASS if both agents echo the same id **and** agent B's `memory_get_context` returns agent A's message.
If `${SESSION_ID}` is not substituted, fall back to hard-coding a `--session-id` you pass to both
sub-agents, and record that the runtime-dynamic case is unsupported.

## Check 04 — reviewer reads the reasoning trace

The trace tools are MCP-only. With the sidecar running, have any MCP client (or an agent) record a
trace and then read it back:

1. record: `memory_start_trace(session_id="verify-trace", task="t")` → `memory_record_step(trace_id=…,
   thought="why", action="do", observation="ok")` → `memory_complete_trace(trace_id=…, success=true)`.
2. read it back as a *different* reader via `memory_search(memory_types=["traces"],
   session_id="verify-trace")`, and traverse the graph:

```cypher
// local Neo4j: cypher-shell -u neo4j -p "$NAM_NEO4J__PASSWORD"
MATCH (t:ReasoningTrace {session_id: 'verify-trace'})-[:HAS_STEP]->(s:ReasoningStep)
OPTIONAL MATCH (s)-[:TOUCHED]->(e:Entity)
RETURN t.task, s.thought, s.action, s.observation, collect(e.name);
```

PASS if the steps come back and `:TOUCHED` links steps to entities. (The exact Cypher mirrors
`omnigent_neo4j_memory.reasoning_steps_for_session`.)
