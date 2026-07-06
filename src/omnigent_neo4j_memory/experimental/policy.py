"""EXPERIMENTAL — a memory-backed Omnigent policy (capture + optional consult).

OFF BY DEFAULT and not part of supported v1 (ADR-0002). It demonstrates "memory for the control
plane": a policy handler that records tool-call provenance into the memory workspace (capture) and
can surface a prior hazard as an ASK (consult).

Why experimental: it couples to the alpha Omnigent ``PolicyEvent`` shape and (ab)uses the guardrail
contract for side effects. The supported capture path is the explicit ``memory_*_trace`` MCP tools
driven by ``prompts/coder.md``.

Wire it (at your own risk) in an agent YAML — the simple form references an evaluator directly:

    policies:
      memory_capture:
        type: function
        handler: omnigent_neo4j_memory.experimental.policy.capture

…or the factory form, which the Omnigent ``factory_params`` mechanism calls at build time:

    policies:
      memory_control:
        type: function
        handler: omnigent_neo4j_memory.experimental.policy.make_memory_policy
        factory_params: { mode: capture_and_consult }

Safety contract: in capture mode the handler ALWAYS returns ``None`` (never blocks). In consult mode
it may return ``ASK`` but never ``DENY``, so a slow/flaky memory backend can't wedge an agent. Every
path is wrapped so memory errors never surface to the agent.

The Omnigent policy contract this assumes (from Omnigent's UPSTREAM docs/POLICIES.md; alpha and
unverified against a running server — see ADR-0002):
  event  = {"type": "tool_call"|"tool_result"|"request"|"response", "target": str,
            "data": {"name": str, "arguments": dict}, "context": {...},
            "session_state": dict, "request_data": ...}
  return = {"result": "ALLOW"|"DENY"|"ASK", "reason": str, "state_updates": [...]} | None
"""

from __future__ import annotations

import asyncio
import os
import queue
import threading
from typing import Any, Callable, Optional

PolicyEvent = dict
PolicyResponse = dict

_CONSULT_TIMEOUT_S = 2.0


class _Recorder:
    """A daemon thread owning an asyncio loop, for fire-and-forget capture writes."""

    def __init__(self) -> None:
        self._q: "queue.Queue[Optional[Callable[[Any], Any]]]" = queue.Queue(maxsize=1000)
        self._thread = threading.Thread(
            target=self._run, name="omnigent-memory-recorder", daemon=True
        )
        self._started = False

    def start(self) -> None:
        if not self._started:
            self._started = True
            self._thread.start()

    def submit(self, coro_factory: Callable[[Any], Any]) -> None:
        try:
            self._q.put_nowait(coro_factory)
        except queue.Full:
            pass  # drop under overload — capture is best-effort

    async def _process(self, coro_factory) -> None:
        try:
            from ..helpers import open_memory

            async with open_memory() as memory:
                await coro_factory(memory)
        except Exception:
            pass  # never let capture errors surface

    def _run(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            while True:
                # Block in THIS daemon thread (not a non-daemon executor thread, which would keep the
                # process alive at exit). The thread is a daemon, so a blocking get() is safe.
                coro_factory = self._q.get()
                if coro_factory is None:
                    return
                loop.run_until_complete(self._process(coro_factory))
        finally:
            loop.close()


_recorder = _Recorder()


def _session_id() -> str:
    return os.environ.get("SESSION_ID") or "omnigent-policy"


async def _capture_step(memory, event: PolicyEvent) -> None:
    data = event.get("data") or {}
    name = data.get("name") or event.get("target") or "tool"
    content = f"[policy:{event.get('type')}] {name} args={data.get('arguments')!r}"
    await memory.short_term.add_message(
        session_id=_session_id(), role="assistant", content=content, extract_entities=True
    )


def _run_sync(coro, timeout: float = _CONSULT_TIMEOUT_S):
    """Run a coroutine to completion on a throwaway loop in a worker thread, time-boxed."""
    box: dict[str, Any] = {}

    def runner() -> None:
        loop = asyncio.new_event_loop()
        try:
            box["value"] = loop.run_until_complete(asyncio.wait_for(coro, timeout))
        except Exception:
            box["value"] = None
        finally:
            loop.close()

    t = threading.Thread(target=runner, daemon=True)
    t.start()
    t.join(timeout + 0.5)
    return box.get("value")


async def _consult_coro(target: str) -> Optional[str]:
    from ..helpers import open_memory

    async with open_memory() as memory:
        ctx = await memory.get_context(
            f"known hazards, incidents, or prior review flags related to: {target}",
            session_id=_session_id(),
        )
        text = str(ctx).lower()
    for flag in ("incident", "review_flagged", "deprecated", "cve", "do not", "do-not"):
        if flag in text:
            return (
                f"Memory recalls a prior hazard ('{flag}') related to this action. "
                "Review before proceeding."
            )
    return None


def _consult(event: PolicyEvent) -> Optional[str]:
    data = event.get("data") or {}
    target = str(data.get("arguments") or data.get("name") or "").strip()
    if not target:
        return None
    return _run_sync(_consult_coro(target))


def make_memory_policy(mode: str = "capture") -> Callable[[PolicyEvent], Optional[PolicyResponse]]:
    """Return a policy evaluator. ``mode`` ∈ {"capture", "consult", "capture_and_consult"}."""
    _recorder.start()
    do_capture = mode in ("capture", "capture_and_consult")
    do_consult = mode in ("consult", "capture_and_consult")

    def evaluate(event: PolicyEvent) -> Optional[PolicyResponse]:
        try:
            etype = event.get("type")
            if do_capture and etype in ("tool_call", "tool_result"):
                _recorder.submit(lambda m: _capture_step(m, event))
            if do_consult and etype == "tool_call":
                hazard = _consult(event)
                if hazard:
                    return {"result": "ASK", "reason": hazard}
        except Exception:
            return None  # never break the agent
        return None

    return evaluate


# Lazy default evaluator for the simple `handler: ...policy.capture` form. Building it on first call
# (not import) keeps importing this module side-effect-free (no recorder thread) for tests.
_default_eval: Optional[Callable[[PolicyEvent], Optional[PolicyResponse]]] = None


def capture(event: PolicyEvent) -> Optional[PolicyResponse]:
    """Ready-to-wire capture-only handler (see module docstring)."""
    global _default_eval
    if _default_eval is None:
        _default_eval = make_memory_policy("capture")
    return _default_eval(event)
