# 0001 — One host-level shared MCP server, not per-agent `command:` MCP

**Status:** accepted

Omnigent sub-agents run in Omnibox sandboxes that (a) start with a fresh, empty environment — a
parent's `MEMORY_API_KEY` does **not** propagate — and (b) deny network egress by default, with an
allow-list syntax that is undocumented at the time of writing. The brief's per-agent
`tools.memory { type: mcp, command: uvx … }` pattern therefore can't reliably get the credential into
each sandbox or reach NAMS from inside it.

So we run **one shared MCP server at the host level** (the *sidecar*), exposed over SSE, and every
agent and sub-agent references it with `tools.memory { type: mcp, url: http://host:8000 }`. The
`MEMORY_API_KEY` lives only on the host process; the only egress a sandbox needs is to the sidecar.
This also makes the shared **memory workspace** automatic — all sub-agents point at the same endpoint.

**Consequences:** adopters run one extra process (documented via `docker-compose`). The remote NAMS MCP
endpoint (`https://memory.neo4jlabs.com/mcp`) would remove even that, but its `nams_…`→bearer token
exchange is undocumented; we treat it as a "drop the sidecar" upgrade pending Phase-1 verification
(see `scripts/verify/`).
