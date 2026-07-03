#!/usr/bin/env python3
"""Seed the memory workspace with synthetic *prior-run* knowledge.

This makes the demo's cross-run recall beat deterministic and quotable for the writeup: a fresh
Omnigent session (which by design remembers nothing) recalls these because the memory workspace
persists. It is honestly labeled as seeded — see docs/WRITEUP.md §5.

What it writes (to whichever backend the env selects — NAMS or local Neo4j):
  - entities:    UserAuth (OBJECT), pyjwt (OBJECT), "incident #42" (EVENT)
  - preference:  the auth module prefers RS256 over HS256
  - facts:       pyjwt CAUSED_INCIDENT incident #42; UserAuth SIGNS_WITH RS256  (best-effort)
  - messages:    human-readable versions so semantic recall surfaces them regardless of the fact API

Usage:
    python scripts/seed.py                      # default prior-run session
    python scripts/seed.py --session-id prior-run-001
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as _dt

from omnigent_neo4j_memory import open_memory

TODAY = _dt.date.today().isoformat()


async def _maybe(obj, method_name: str, /, **kwargs):
    """Call obj.<method_name>(**kwargs) if it exists; report what happened. Some SDK method names
    beyond the core set are version-dependent, so we degrade gracefully rather than crash a seed."""
    method = getattr(obj, method_name, None)
    if method is None:
        print(f"  · skip {method_name} (not available in this SDK build)")
        return None
    try:
        result = method(**kwargs)
        if asyncio.iscoroutine(result):
            result = await result
    except Exception as exc:  # signature drift / backend error — stay best-effort
        print(f"  · skip {method_name} ({type(exc).__name__}: {exc})")
        return None
    print(f"  ✓ {method_name}({', '.join(f'{k}={v!r}' for k, v in list(kwargs.items())[:2])}…)")
    return result


async def seed(session_id: str) -> None:
    async with open_memory() as memory:
        print("Seeding entities…")
        await _maybe(memory.long_term, "add_entity", name="UserAuth", entity_type="OBJECT")
        await _maybe(memory.long_term, "add_entity", name="pyjwt", entity_type="OBJECT")
        await _maybe(memory.long_term, "add_entity", name="incident #42", entity_type="EVENT")

        print("Seeding the owner's preference…")
        await _maybe(
            memory.long_term,
            "add_preference",
            category="auth",
            preference="Sign tokens with RS256 (asymmetric); HS256 is not allowed.",
            confidence=0.95,
        )

        print("Seeding facts (best-effort)…")
        await _maybe(
            memory.long_term, "add_fact",
            subject="pyjwt", predicate="CAUSED_INCIDENT",
            object_value="incident #42 — algorithm confusion in versions < 2.0",
            confidence=0.95, valid_from=TODAY,
        )
        await _maybe(
            memory.long_term, "add_fact",
            subject="UserAuth", predicate="SIGNS_WITH", object_value="RS256",
            confidence=0.95, valid_from=TODAY,
        )

        print("Seeding human-readable messages (so semantic recall always surfaces them)…")
        for content in (
            "Decision on record: the auth module signs tokens with RS256 (asymmetric). HS256 is not "
            "allowed. Owner: platform team.",
            "Incident #42: pyjwt < 2.0 was vulnerable to algorithm confusion. Keep pyjwt >= 2.0 and "
            "always pin the expected alg when verifying tokens.",
        ):
            await _maybe(
                memory.short_term, "add_message",
                session_id=session_id, role="assistant", content=content, extract_entities=True,
            )

        print(f"\nDone. Prior-run knowledge seeded under session '{session_id}'.")
        print("Long-term entities/preferences/facts are workspace-wide and will surface in a fresh "
              "session via cross-run recall (memory_search without a session filter).")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-id", default="prior-run-001",
                        help="Session the prior-run messages are recorded under.")
    args = parser.parse_args()
    asyncio.run(seed(args.session_id))


if __name__ == "__main__":
    main()
