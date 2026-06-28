"""omnigent-neo4j-memory — graph-native, cross-session, cross-agent memory for Omnigent agents.

Backed by neo4j-agent-memory / NAMS. See ADR-0001 (host-level shared MCP sidecar) and
ADR-0002 (explicit capture; policy is experimental).
"""

from .helpers import (
    fresh_facts_for_entity,
    mint_session_id,
    open_memory,
    reasoning_steps_for_session,
)
from .prompts import load_prompt

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "mint_session_id",
    "open_memory",
    "fresh_facts_for_entity",
    "reasoning_steps_for_session",
    "load_prompt",
]
