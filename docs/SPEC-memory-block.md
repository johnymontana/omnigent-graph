# Proposal: a first-class `memory:` block for Omnigent agents

**Status:** draft / design-only. Not implemented. Intended as the basis for an upstream conversation
with `omnigent-ai/omnigent` — *no PR until the alpha surfaces settle* (see plan §D6, ADR-0001/0002).

## Motivation

Today, giving an Omnigent agent durable graph memory means wiring two things by hand: a `tools.memory`
MCP entry pointing at a host-level sidecar, and (optionally) an `experimental` capture policy — plus
prompt scaffolding that tells the agent which tools to call. That's three coordinated edits for a
capability that Omnigent's "one-line-change" ethos says should be one. And because capture is
prompt-driven, two authors wire it two different ways.

A first-class `memory:` block would make memory a declared *property* of an agent, the way `executor:`
declares its model — captured automatically at the uniform I/O boundary, inherited by sub-agents,
consistent across harnesses.

## Proposed shape

```yaml
memory:
  provider: neo4j-agent-memory        # pluggable; this proposal implements one provider
  endpoint: ${OMNIGENT_MEMORY_URL}    # the host-level sidecar / NAMS MCP endpoint
  workspace: ${MEMORY_API_KEY}        # tenancy = key (a "memory workspace"); never enters a sandbox
  session: ${SESSION_ID}              # shared scope for an orchestrator + its sub-agents
  capture: [short_term, long_term, reasoning]   # what to record automatically
  recall: on_request                  # auto-inject relevant context at the start of each turn
  scope: inherit                      # sub-agents share the parent's session by default
```

## Semantics

- **`capture`** — the server records on the uniform boundary: each turn's messages (`short_term`,
  POLE+O entities auto-extracted), durable facts/decisions (`long_term`), and a `:ReasoningTrace`
  built from the turn's tool calls/results (`reasoning`). No per-agent prompt scaffolding required.
- **`recall: on_request`** — before each model turn, the server recalls workspace-relevant context for
  the current prompt and injects it (bounded, with provenance), so the agent starts informed.
- **`scope: inherit`** — sub-agents declared as `type: agent` adopt the parent's `session`, so an
  orchestrator and its workers share one memory scope without threading an id through prompts. This is
  the piece that needs a runtime value to reach sub-agents — see "Open questions."
- **`workspace`** is the tenancy boundary and is resolved on the server/host, never injected into a
  sandbox's environment.

## How it desugars (today's building blocks)

The block is sugar over what already works, so it can ship as a server hook *or* as a local plugin
that expands to:

```yaml
tools:
  memory: { type: mcp, url: <endpoint> }     # from `endpoint`
policies:
  _memory_capture:                            # from `capture` (the experimental recorder, hardened)
    type: function
    handler: omnigent_neo4j_memory.experimental.policy.make_memory_policy
    factory_params: { mode: capture }
# + prompt scaffolding injected for recall, from prompts/{coder,reviewer}.md
```

This is deliberate: the proposal asks upstream for a **declaration**, not new runtime machinery — it
maps onto `tools` + `policies` + the I/O boundary Omnigent already owns.

## Open questions (for the upstream discussion)

1. **Runtime session propagation.** `scope: inherit` needs a runtime-generated `session` to reach
   sub-agents. Omnigent's documented `${ENV}` interpolation is load-time/host-side; is there (or
   should there be) a first-class way for an orchestrator to set a sub-agent param at spawn time?
2. **Recall budget + provenance.** Where does injected context go in the prompt, and how is its
   provenance surfaced so policies/audit can see what memory contributed?
3. **Capture at the boundary vs. in a policy.** Is a dedicated server hook preferable to a policy that
   (ab)uses the guardrail contract for side effects? (We believe yes — hence proposing this.)
4. **Staleness.** Should the block expose a recency/`valid_until` policy, given the backend has no
   automatic decay?

## Non-goals (for this proposal)

Multi-provider abstraction beyond a clean interface, a skills-distillation loop, and any NAMS-specific
hosting concerns. This proposal is just: *make memory a declared property of an Omnigent agent.*
