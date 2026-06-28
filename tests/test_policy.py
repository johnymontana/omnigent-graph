"""The experimental policy must satisfy its safety contract WITHOUT a memory backend present:
capture never blocks, consult never DENYs, and memory errors never surface. (ADR-0002.)"""

from omnigent_neo4j_memory.experimental import policy


def _tool_call(cmd="ls"):
    return {"type": "tool_call", "target": "sys_os_shell",
            "data": {"name": "sys_os_shell", "arguments": {"command": cmd}}}


def test_capture_never_blocks():
    evaluate = policy.make_memory_policy("capture")
    assert evaluate(_tool_call()) is None
    assert evaluate({"type": "tool_result", "data": {"name": "x", "arguments": {}}}) is None
    assert evaluate({"type": "request"}) is None


def test_capture_handler_shortcut():
    # The ready-to-wire `handler: ...policy.capture` form.
    assert policy.capture(_tool_call()) is None


def test_consult_returns_none_or_ask_never_deny(monkeypatch):
    # With no backend reachable, _consult degrades to None; never DENY, never raise.
    monkeypatch.setattr(policy, "_consult", lambda event: None)
    evaluate = policy.make_memory_policy("capture_and_consult")
    out = evaluate(_tool_call())
    assert out is None


def test_consult_ask_shape(monkeypatch):
    monkeypatch.setattr(policy, "_consult", lambda event: "prior incident")
    evaluate = policy.make_memory_policy("consult")
    out = evaluate(_tool_call())
    assert out == {"result": "ASK", "reason": "prior incident"}


def test_handler_swallows_consult_errors(monkeypatch):
    def boom(event):
        raise RuntimeError("backend down")

    monkeypatch.setattr(policy, "_consult", boom)
    evaluate = policy.make_memory_policy("consult")
    assert evaluate(_tool_call()) is None  # error swallowed → abstain
