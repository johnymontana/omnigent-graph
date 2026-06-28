# sample-app — a toy auth service for the Polly-memory demo

A deliberately small service the Polly-memory orchestrator iterates on across runs. It exists so the
memory workspace accumulates *real* entities (files, classes, dependencies) and so the seeded
prior-run knowledge has something concrete to attach to.

- `app/auth.py` — `UserAuth`, a JWT-based token issuer/verifier. Owned by the (fictional) **platform
  team**; the owner prefers **RS256 over HS256** for token signing.
- Known hazard (seeded as prior-run memory): the `pyjwt` dependency at **< 2.0** caused **incident
  #42** (an algorithm-confusion vulnerability). New work should not reintroduce it.

The demo's Run 1 task extends `UserAuth`; Run 2 (a fresh Omnigent session) starts unrelated work and
should *recall* the RS256 preference and the incident from the persistent memory workspace.
