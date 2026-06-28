"""Integration: a real store -> recall round-trip against a backend.

Marked `integration` — runs only in the CI `integration-neo4j` job (a Neo4j service + local
sentence-transformers embeddings) or locally when you have NAM_NEO4J__* / MEMORY_API_KEY set.
"""

import os

import pytest

pytestmark = pytest.mark.integration

_HAS_BACKEND = bool(os.environ.get("MEMORY_API_KEY") or os.environ.get("NAM_NEO4J__PASSWORD"))


@pytest.mark.skipif(not _HAS_BACKEND, reason="no MEMORY_API_KEY or NAM_NEO4J__PASSWORD configured")
async def test_store_then_recall():
    from omnigent_neo4j_memory import mint_session_id, open_memory

    session_id = mint_session_id("it")
    marker = f"integration-marker-{session_id}"
    async with open_memory() as memory:
        await memory.short_term.add_message(
            session_id=session_id, role="user", content=marker, extract_entities=False
        )
        ctx = await memory.get_context(marker, session_id=session_id)
    assert marker in str(ctx)
