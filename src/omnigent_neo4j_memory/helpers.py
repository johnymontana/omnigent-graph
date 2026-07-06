"""Helpers shared by the demo, the seed script, the verify scripts, and the experimental policy.

Two things live here:
  1. `mint_session_id` + the Cypher builders — pure, no dependencies, safe to import anywhere.
  2. `open_memory` — a `MemoryClient` from the environment (NAMS if MEMORY_API_KEY is set,
     else local Neo4j via NAM_NEO4J__*). The heavy `neo4j_agent_memory` import is lazy so that
     importing this module (e.g. in tests) stays cheap.
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager


def mint_session_id(prefix: str = "task") -> str:
    """Mint a unique memory session id.

    The coder and the reviewer must use the SAME value so they share one memory scope. Omnigent has
    no verified way to push a runtime-generated value into a sub-agent's `params`, so the demo mints
    this on the host and exports it as ``SESSION_ID`` before ``omnigent run`` — the runner
    substitutes ``${SESSION_ID}`` at load time (host-side), which sidesteps the sandbox's empty
    runtime env. That prompt-body interpolation is unverified — confirm with
    scripts/verify/agents/session_check.yaml (VERIFY.md Check 03).
    """
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


# --- Read-only Cypher run by the reviewer / verify scripts via the `graph_query` MCP tool ---------

def fresh_facts_for_entity(entity_name: str) -> str:
    """Non-stale facts about an entity.

    There is no automatic decay/TTL in the memory backend, so we filter on ``valid_until`` ourselves
    (see ADR-0002 and the writeup's honest-caveats section). Parameter: ``$name``.
    """
    # valid_until may be stored as an ISO string or a temporal; toString()+date() handles both.
    return (
        "MATCH (e:Entity {name: $name})-[r]->(o) "
        "WHERE r.valid_until IS NULL OR date(toString(r.valid_until)) >= date() "
        "RETURN type(r) AS predicate, o.name AS object, "
        "r.valid_from AS valid_from, r.confidence AS confidence "
        "ORDER BY r.confidence DESC"
    )


def reasoning_steps_for_session(session_id: str) -> str:
    """The author's reasoning trace for a shared session — what the reviewer grounds critique in.

    Parameter: ``$session_id``. Walks ``(:ReasoningTrace)-[:HAS_STEP]->(:ReasoningStep)`` and the
    optional ``(:ReasoningStep)-[:TOUCHED]->(:Entity)`` provenance edges. This targets the documented
    schema; confirm it against your build's live labels/rels via VERIFY.md Check 04. Ordering falls
    back to element id (insertion-ish) — use a stored step ordinal if your build provides one.
    """
    return (
        "MATCH (t:ReasoningTrace {session_id: $session_id})-[:HAS_STEP]->(s:ReasoningStep) "
        "OPTIONAL MATCH (s)-[:TOUCHED]->(e:Entity) "
        "RETURN t.task AS task, s.thought AS thought, s.action AS action, "
        "s.observation AS observation, collect(e.name) AS touched "
        "ORDER BY elementId(s)"
    )


@asynccontextmanager
async def open_memory():
    """Open a `MemoryClient` from the environment (env-driven, exactly like the sidecar).

    NAMS when ``MEMORY_API_KEY`` is set; otherwise local Neo4j via ``NAM_NEO4J__*`` (auto-resolved
    when no key is present). Embedding + extraction config is read from the environment too — e.g.
    ``NAM_EMBEDDING__PROVIDER=sentence_transformers`` for the offline local path, which needs the
    local backend installed (``pip install '.[local]'``; the base ``[mcp]`` extra ships no embedder,
    so the client would otherwise fall back to the OpenAI embedder and require a key).

    We deliberately do NOT pass an explicit ``MemorySettings`` here: doing so bypasses this env-based
    config and silently reinstates the OpenAI embedder default.
    """
    from neo4j_agent_memory import MemoryClient  # lazy: heavy import

    async with MemoryClient() as memory:
        yield memory
