# Omnigent × Neo4j Agent Memory

Glossary for `omnigent-neo4j-memory` — the integration that gives Omnigent (a memoryless
meta-harness) durable, cross-session, cross-agent graph memory backed by neo4j-agent-memory / NAMS.

## Omnigent

**Meta-harness**:
The category Omnigent occupies — a uniform control layer above coding agents and agent SDKs that
normalizes every one to "messages + files in, text streams + tool calls out."
_Avoid_: framework, wrapper, orchestrator (orchestrator is a role inside it, not the layer)

**Harness**:
One underlying coding agent wrapped by Omnigent (Claude Code, Codex, Pi, …).
_Avoid_: backend, model, provider

**Runner**:
The component that wraps one harness in a sandboxed (Omnibox) session behind the uniform API.
_Avoid_: executor (the `executor` YAML block selects harness + model; it is not the runner)

**Server**:
The multi-user coordinator: policies, session sharing, MCP proxy, persistence, web/mobile/HTTP.

**Session**:
A transcript plus a filesystem. Forking copies the transcript; nothing durable survives it.
_Avoid_: conversation (the conversation is the message list inside a session)

**Policy**:
A handler evaluated on request / response / tool_call / tool_result that returns ALLOW, DENY, or ASK.
_Avoid_: guardrail (the goal), hook (too generic)

**Omnibox**:
Omnigent's OS-level sandbox: default-deny network egress, credential injection, filesystem isolation.

## Neo4j Agent Memory

**Memory workspace**:
The tenancy boundary for stored memory, selected by API key. Our canonical term for what NAMS calls a
"workspace" — deliberately disambiguated from an Omnigent session's filesystem.
_Avoid_: workspace (ambiguous — collides with Omnigent's session filesystem), namespace, tenant

**POLE+O**:
The long-term entity ontology: Person, Organization, Location, Event, + Object.
_Avoid_: schema, entity types

**Reasoning trace**:
The provenance layer — a `:ReasoningTrace` with ordered `:ReasoningStep`s recording what an agent did
and why. It is a trace, not a single decision node.
_Avoid_: decision, `:Decision`, audit log

**NAMS**:
Neo4j Agent Memory Service — the hosted, Aura-backed, API-key-authenticated memory backend.
_Avoid_: the database, the server (collides with Omnigent's Server)

## This integration

**Capture**:
What the author / coder agent does — recording messages, entities, and a reasoning trace into the
memory workspace.
_Avoid_: write, log, persist

**Recall**:
What a later agent (the reviewer, or a fresh session) does — reading prior capture back out via
search / context / Cypher.
_Avoid_: read, fetch, retrieve (use "recall" for the memory act specifically)

**Sidecar**:
The single host-level MCP server process that every agent talks to over SSE; it holds the memory
credential so sandboxes never see it.
_Avoid_: bridge, proxy, gateway
