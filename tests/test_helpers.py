from omnigent_neo4j_memory import (
    fresh_facts_for_entity,
    load_prompt,
    mint_session_id,
    reasoning_steps_for_session,
)


def test_mint_session_id_unique_and_prefixed():
    a, b = mint_session_id(), mint_session_id()
    assert a != b
    assert a.startswith("task-")
    assert mint_session_id("verify").startswith("verify-")


def test_fresh_facts_filters_staleness():
    cy = fresh_facts_for_entity("UserAuth")
    # No auto-decay exists, so the query must filter on valid_until itself (ADR-0002 caveat).
    assert "valid_until IS NULL" in cy
    assert "$name" in cy


def test_reasoning_steps_walks_trace():
    cy = reasoning_steps_for_session("s1")
    assert ":ReasoningTrace" in cy and ":HAS_STEP" in cy and ":TOUCHED" in cy
    assert "$session_id" in cy


def test_prompts_carry_session_placeholder():
    for name in ("coder", "reviewer"):
        text = load_prompt(name)
        assert "{SESSION_ID}" in text
        assert "memory_" in text  # references the memory tools
