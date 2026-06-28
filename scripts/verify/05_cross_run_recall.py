#!/usr/bin/env python3
"""Verify 05 — cross-run recall: a NEW session recalls long-term knowledge from a prior one.

Writes an entity + preference under session A, then searches WITHOUT a session filter under session B
and confirms the long-term knowledge surfaces (short-term messages stay session-scoped; long-term is
workspace-wide). This is the persistence beat the demo's centerpiece rests on.

    python scripts/verify/05_cross_run_recall.py
"""

from __future__ import annotations

import asyncio
import sys

from omnigent_neo4j_memory import mint_session_id, open_memory

UNIQUE = mint_session_id("xrun").split("-")[-1]
ENTITY = f"CrossRunWidget_{UNIQUE}"


async def _maybe(obj, name, /, **kwargs):
    m = getattr(obj, name, None)
    if m is None:
        return None
    r = m(**kwargs)
    return await r if asyncio.iscoroutine(r) else r


async def main() -> int:
    session_a = mint_session_id("runA")
    session_b = mint_session_id("runB")

    # Session A writes long-term knowledge.
    async with open_memory() as memory:
        await _maybe(memory.long_term, "add_entity", name=ENTITY, entity_type="OBJECT")
        await _maybe(memory.long_term, "add_preference",
                     category="testing", preference=f"{ENTITY} prefers the Singleton pattern",
                     confidence=0.9)
        await memory.short_term.add_message(
            session_id=session_a, role="assistant",
            content=f"{ENTITY} uses the Singleton pattern.", extract_entities=True)

    # Session B (brand new) recalls it WITHOUT a session filter.
    async with open_memory() as memory:
        found = await _maybe(memory.long_term, "search_entities", query=ENTITY, limit=10)
        ctx = await memory.get_context(f"What pattern does {ENTITY} use?", session_id=session_b)

    surfaced = ENTITY in str(found) or ENTITY in str(ctx) or "singleton" in str(ctx).lower()
    print(f"cross-run recall of {ENTITY}: {'PASS' if surfaced else 'FAIL'}")
    if not surfaced:
        print("  (entity written in session A did not surface in session B — check workspace scoping)")
    return 0 if surfaced else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
