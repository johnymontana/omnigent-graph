#!/usr/bin/env python3
"""Verify 01 — the memory backend authenticates and a store→recall round-trips.

NAMS when MEMORY_API_KEY is set, else local Neo4j via NAM_NEO4J__*. Pure SDK; no Omnigent needed.

    python scripts/verify/01_backend_auth.py
"""

from __future__ import annotations

import asyncio
import sys

from omnigent_neo4j_memory import mint_session_id, open_memory


async def main() -> int:
    session_id = mint_session_id("verify")
    marker = f"verify-marker-{session_id}"
    async with open_memory() as memory:
        await memory.short_term.add_message(
            session_id=session_id, role="user", content=marker, extract_entities=False
        )
        ctx = await memory.get_context(marker, session_id=session_id)
    ok = marker in str(ctx)
    print(f"stored + recalled marker: {'PASS' if ok else 'FAIL'}")
    if not ok:
        print("  (the backend connected but the round-trip did not surface the marker — investigate)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
