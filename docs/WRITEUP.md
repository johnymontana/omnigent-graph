# Graph-Native Memory for Omnigent

> **Neo4j Labs · experimental.** This is a Labs project: community-supported, exploratory, and not a
> supported product. Omnigent is a third-party, Apache-2.0 project we integrate *with*, not a Neo4j
> product. Interfaces here are alpha on both sides and will move.

*Venue-agnostic draft — pick Neo4j Developer Blog / `lyonwj.com` / both at publish time.*

---

## 1. The gap: a meta-harness with no memory

[Omnigent](https://omnigent.ai/) is a *meta-harness* — a uniform control layer above coding agents
(Claude Code, Codex, Pi, and more) and agent SDKs. It normalizes every harness to one interface,
"messages and files in, text streams and tool calls out," and adds composition, control, and
collaboration on top. Integrate something once at that layer and every harness inherits it.

But Omnigent ships **no durable memory**. A session is a transcript plus a workspace; forking a
session branches the transcript; nothing extracts structured, cross-session or cross-agent knowledge.
That's not an oversight — it's on their own roadmap ("an Omnigent Server MCP so agents can work across
your sessions"). Today, when you switch harnesses or start a new session, what was *learned* is gone;
only what was *said* in the current transcript remains.

When an orchestrator like Omnigent's flagship **Polly** fans work out to coding sub-agents in parallel
git worktrees — and routes each diff to a reviewer from a *different vendor* than the author — those
sub-agents share nothing but what the orchestrator threads through its own context window. The reviewer
re-derives the author's intent from the diff, because it has no other way to know it.

That gap is exactly the shape of [neo4j-agent-memory](https://neo4j.com/labs/agent-memory/).

## 2. Why a graph, not a vector store

neo4j-agent-memory gives agents three memory types in one graph:

- **short-term** — the conversation, as `:Message` nodes;
- **long-term** — a POLE+O knowledge graph (Person, Organization, Location, Event, + Object),
  auto-extracted from messages;
- **reasoning** — a `:ReasoningTrace` of ordered `:ReasoningStep`s recording *what an agent did and
  why*, with `:TOUCHED` edges from steps to the entities they involved.

The reasoning layer is the point. Omnigent's whole value proposition is *control* and *provenance* —
policies that track what agents do, sessions you can share and audit, cross-vendor review. Those are
relationship-and-provenance surfaces: "this step touched that entity," "this decision supersedes that
one," "another session already flagged this dependency." A graph owns those queries natively. We're
not going to argue the vector-vs-graph point in the abstract — we're going to show the reviewer
walking `(:ReasoningTrace)-[:HAS_STEP]->(:ReasoningStep)-[:TOUCHED]->(:Entity)` to ground a critique,
and let that speak.

## 3. The wiring (and the alpha constraints we hit)

The obvious approach — declare a per-agent MCP tool with `command: uvx neo4j-agent-memory[mcp] …` in
each agent's YAML — doesn't survive contact with alpha Omnigent:

- Omnigent sub-agents run in **Omnibox** sandboxes that start with a **fresh, empty environment** —
  a parent's `MEMORY_API_KEY` does not propagate in.
- Omnibox **denies network egress by default**, and the allow-list syntax isn't documented yet.

So instead of N memory servers fighting the sandbox, we run **one**. The
[`omnigent-neo4j-memory`](https://github.com/johnymontana/omnigent-graph) package launches a single
**host-level MCP sidecar** over SSE; every agent and sub-agent references it with
`tools.memory { type: mcp, url: http://host:8000 }`. The memory credential lives only on that host
process, so sandboxes never see it and need egress to exactly one endpoint. As a bonus, "all
sub-agents point at the same endpoint" *is* the shared memory workspace — sharing falls out for free.
(There's a hosted remote MCP endpoint at `memory.neo4jlabs.com/mcp` too; once its token exchange is
documented you can drop the sidecar entirely.)

```yaml
tools:
  memory:
    type: mcp
    url: http://host.docker.internal:8000   # the one sidecar; the secret lives here, not in sandboxes
```

```bash
omnigent-neo4j-memory serve           # NAMS by default; local Neo4j fallback with no MEMORY_API_KEY
```

## 4. Intra-run: the reviewer grounds critique in the author's reasoning

In the Polly-memory fork, the coder (vendor A) doesn't just write code — it records its reasoning:

```
memory_start_trace(session_id=S, task="add refresh-token support to UserAuth")
memory_record_step(trace_id=…, thought="chose RS256 over HS256 to keep verification asymmetric",
                   action="added rotate_refresh()", observation="access TTL stays 24h")
memory_complete_trace(trace_id=…, outcome="refresh added; RS256 preserved", success=true)
```

The reviewer (vendor B) reads it back before critiquing:

```
memory_get_context(session_id=S, include_reasoning=true)
memory_search(query="refresh token", memory_types=["traces"], session_id=S)
```

and grounds its critique in the author's own words — "your trace step noted the access TTL stays 24h;
for the new refresh path, that's worth revisiting" — instead of guessing intent from the diff. A
shared brain across two vendors' models.

## 5. Cross-run: a fresh session that remembers

Here's the beat Omnigent can't do alone. Start a **brand-new** Omnigent session — no transcript, no
memory of the last run — and ask it to add a token-issuing endpoint. Because the memory *workspace*
persists in NAMS, the agents recall what prior runs learned:

- the platform team's standing decision to **sign with RS256, never HS256**;
- that **`pyjwt < 2.0` caused incident #42** (algorithm confusion) and must not be reintroduced.

```
memory_search(query="auth signing decisions and known incidents")   # no session filter → workspace-wide
```

> **Reproducibility note (honest labeling):** for the writeup the prior-run knowledge is *seeded*
> (`scripts/seed.py`) so the recall is deterministic and quotable. In real use it accumulates from
> actual runs. We seed it so the screenshot is the same every time, not to fake the capability — the
> recall query is the real one.

## 6. Honest caveats

This is alpha on both sides. Specifically:

- **No automatic staleness.** Nothing decays or expires; a six-month-old fact and a fresh one rank by
  similarity alone. We mitigate with `valid_until` on facts and reviewer-side filtering
  (`WHERE r.valid_until IS NULL OR r.valid_until > datetime()`), and we say so out loud.
- **Generic ontology.** Extraction is POLE+O; there's no built-in software-engineering schema, so
  "files/classes/deps" land as `OBJECT`s. Fine for v1; a custom schema is future work.
- **Multi-tenancy via keys.** The MCP tools don't take a per-user identifier, so isolation between
  teams is "different API key → different workspace," not a per-call parameter.
- **The session-id mechanic** that makes intra-run sharing work is the one piece most exposed to
  Omnigent's alpha surfaces; the repo ships a verification for it and a documented fallback.

## 7. What's next

- **A first-class `memory:` block.** Wiring a tool + (optionally) a policy by hand is fine, but it
  should be one declarative block. We've drafted a [spec](./SPEC-memory-block.md) and opened the
  conversation upstream — no PR until the alpha surfaces settle.
- **Memory for the control plane.** An experimental Omnigent *policy* that records provenance and
  consults the graph for guardrails ships in the repo, off by default. It's the most differentiated
  idea here and the least settled — hence experimental.
- **Experience → skill.** Once sessions accumulate experience in the graph, distilling portable skills
  from it is the natural next loop. That's aspirational today; we're flagging the direction, not
  claiming the feature.

---

**Try it:** [`github.com/johnymontana/omnigent-graph`](https://github.com/johnymontana/omnigent-graph)
— `pip install omnigent-neo4j-memory`, start the sidecar, and run the Polly-memory demo.
