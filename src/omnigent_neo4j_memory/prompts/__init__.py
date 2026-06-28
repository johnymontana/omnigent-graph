"""Prompt scaffolding for memory capture (coder) and recall (reviewer).

These fragments are the source of truth for what each agent should do with the `memory` tools. The
demo embeds them into `agents/polly-memory.yaml`; you can also load them at runtime and inject them
into your own agent prompts (substitute `{SESSION_ID}`).
"""

from importlib import resources


def load_prompt(name: str) -> str:
    """Load a bundled prompt fragment by stem, e.g. ``load_prompt("coder")``."""
    return resources.files(__package__).joinpath(f"{name}.md").read_text(encoding="utf-8")


__all__ = ["load_prompt"]
