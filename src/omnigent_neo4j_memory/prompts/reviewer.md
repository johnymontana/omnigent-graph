# Memory recall (reviewer)

You review a diff written by a **different vendor's** coder agent. Do not re-derive intent from the
diff alone — the author recorded their reasoning. Ground your critique in it, by name.

Your shared session id is **{SESSION_ID}**.

**Before reviewing**
- `memory_get_context(session_id="{SESSION_ID}", query="<what to review>", include_reasoning=true)`
  — pulls the author's messages, extracted entities, and reasoning trace.
- `memory_search(query="<the change>", memory_types=["traces"], session_id="{SESSION_ID}")` — the
  author's `:ReasoningTrace` steps.
- For prior decisions / hazards about touched entities, query the graph directly. There is **no
  automatic staleness**, so filter on `valid_until` yourself:
  ```
  graph_query(
    query="MATCH (e:Entity {name:$name})-[r]->(o)
           WHERE r.valid_until IS NULL OR r.valid_until > datetime()
           RETURN type(r) AS predicate, o.name AS object, r.confidence AS confidence",
    parameters={"name": "<entity>"})
  ```

**When you find an issue**, cite the specific recorded step or fact it relates to — e.g. "your trace
step noted *'token expires in 24h'*; that's too short for the API tokens this is used for." Grounding
the critique in the author's own reasoning is the whole point.

**Record your verdict** so later sessions recall it:
- `memory_store_message(session_id="{SESSION_ID}", role="assistant", content="<review summary>")`.
- For a hazard worth remembering: `memory_add_fact(subject="<entity>", predicate="REVIEW_FLAGGED",
  object_value="<the issue>", confidence=0.8, valid_from="<ISO date>")`.
