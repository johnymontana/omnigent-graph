# Memory capture (coder)

You share a persistent **memory workspace** with a reviewer agent (a *different* vendor's model) and
with future sessions. What you record is how they understand *what you did and why*. Use the `memory`
tools throughout the task — not only at the end. Capture is prompt-driven: if you don't call the
tools, nothing is remembered.

Your shared session id is **{SESSION_ID}** — pass it as `session_id` on every memory call.

**Before you start**
- `memory_get_context(session_id="{SESSION_ID}", query="<the task>")` — recall prior knowledge about
  this codebase (past decisions, incidents, owner preferences) before writing anything.
- `memory_start_trace(session_id="{SESSION_ID}", task="<one line: what you're implementing>")` —
  keep the returned `trace_id`.

**As you work — after each meaningful step**
- `memory_record_step(trace_id="<trace_id>", thought="<why you did it>", action="<what you did>",
  observation="<the result>")` — this is the provenance the reviewer reads. Be specific about
  trade-offs ("chose RS256 over HS256 because…").
- `memory_store_message(session_id="{SESSION_ID}", role="assistant", content="<the step>")` —
  entities (files, classes, dependencies) are extracted automatically.

**For durable decisions and known hazards** (so later sessions recall them)
- `memory_add_fact(subject="<thing>", predicate="<RELATION>", object_value="<value>",
  confidence=0.9, valid_from="<ISO date>")`. If a decision can later go stale, also set
  `valid_until` — there is no automatic expiry.

**When done**
- `memory_complete_trace(trace_id="<trace_id>", outcome="<summary>", success=true)`.
