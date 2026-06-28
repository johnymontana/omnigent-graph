# 0002 — Capture provenance via explicit memory tools; the policy recorder is experimental

**Status:** accepted

Omnigent policies are guardrails: a handler returns ALLOW / DENY / ASK. We *could* (ab)use one to
auto-record provenance on every `tool_call` / `tool_result`, but that couples us to the alpha
`PolicyEvent` shape, adds a memory round-trip to every event, and bends the guardrail contract toward
side effects the docs don't sanction. So v1 captures the `:ReasoningTrace` the robust way: the coder
agent calls the public, versioned MCP tools (`memory_start_trace` → `memory_record_step` →
`memory_complete_trace`), driven by the prompt scaffolding in `prompts/coder.md`.

The policy-based auto-recorder still ships, in `experimental/policy.py`, **off by default** and clearly
labeled, so the "memory for the control plane" idea is demonstrable without v1 depending on it.

**Consequences:** capture reliability rests on prompt adherence (the agent must choose to call the
tools); the scaffolding exists to make that reliable, and Phase-1 verification confirms traces land. If
prompt-driven capture proves flaky in practice, the experimental policy is the fallback worth hardening.
