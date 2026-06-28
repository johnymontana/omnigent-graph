# DRAFT — upstream tracking issue for omnigent-ai/omnigent

> Do not file until reviewed. Conversation-opener, not a PR. Keep it collaborative — Omnigent is an
> integration target, not a competitor.

**Title:** Discussion: a first-class `memory:` block for agents (graph-memory integration)

**Body:**

Hi! We've been exploring giving Omnigent agents durable, cross-session, cross-agent memory backed by a
graph ([neo4j-agent-memory](https://neo4j.com/labs/agent-memory/)), and built a small reusable package
+ a Polly fork demo: <repo link>. It works today by wiring a `tools.memory` MCP entry at a host-level
sidecar plus prompt scaffolding.

Two things we ran into that shaped the design, and one proposal:

1. **Sub-agents start with an empty env** and Omnibox denies egress by default — so a per-agent
   `command:` MCP can't get its credential or reach the backend. Running **one host-level MCP server**
   that every agent references by `url:` sidesteps both. Is that the intended pattern? Is there a
   documented allow-list syntax for sandbox egress we missed?

2. **Runtime value propagation to sub-agents.** To share one memory scope, an orchestrator (e.g.
   Polly) needs the same `session_id` in each sub-agent. `${ENV}` interpolation is host/load-time; is
   there a first-class way to pass an orchestrator-generated value into a `type: agent` sub-agent at
   spawn time?

3. **Proposal:** a declarative `memory:` block that desugars to `tools` + `policies` + the I/O
   boundary you already own — making memory a declared property of an agent. Design sketch:
   <link to docs/SPEC-memory-block.md>. We're not opening a PR yet (your alpha surfaces are moving and
   so is ours) — just opening the conversation and happy to iterate.

Thanks for open-sourcing Omnigent — the uniform layer is exactly the right altitude for this.
