"""Launch the host-level shared MCP sidecar (ADR-0001).

This is a thin, opinionated wrapper around ``neo4j-agent-memory mcp serve``. It picks the backend
from the environment (NAMS when ``MEMORY_API_KEY`` is set, else local Neo4j), exposes the server over
SSE so every Omnigent agent can reach it at ``http://host:<port>``, and keeps the memory credential
on this one host process so sandboxes never see it.

    omnigent-neo4j-memory serve                 # launch (NAMS or local, per env)
    omnigent-neo4j-memory serve --print-cmd     # show the resolved command (secrets redacted)

Flag support varies across neo4j-agent-memory versions; pass extras through after ``--`` and override
``--host``/``--transport`` if your build differs (set ``--host ''`` to omit it on older builds).
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from typing import List, Sequence

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = "8000"
DEFAULT_TRANSPORT = "sse"
DEFAULT_PROFILE = "extended"

_PASSWORD_PLACEHOLDER = "$NAM_NEO4J__PASSWORD"


def resolve_backend() -> str:
    """``"nams"`` when MEMORY_API_KEY is set, else ``"local"``."""
    return "nams" if os.environ.get("MEMORY_API_KEY") else "local"


def _underlying_cmd() -> List[str]:
    exe = shutil.which("neo4j-agent-memory")
    if exe:
        return [exe]
    uvx = shutil.which("uvx")
    if uvx:
        return [uvx, "neo4j-agent-memory[mcp]"]
    raise SystemExit(
        "Could not find `neo4j-agent-memory` or `uvx` on PATH.\n"
        "Install with:  pip install 'neo4j-agent-memory[mcp]'"
    )


def build_serve_command(args: argparse.Namespace, *, strict: bool = True) -> List[str]:
    """Build the underlying `mcp serve` command. With ``strict=False`` (used by --print-cmd) a
    missing local password is shown as a placeholder instead of erroring."""
    cmd = _underlying_cmd() + [
        "mcp",
        "serve",
        "--transport",
        args.transport,
        "--port",
        str(args.port),
    ]
    if args.host:
        cmd += ["--host", args.host]
    if args.profile:
        cmd += ["--profile", args.profile]

    if resolve_backend() == "local":
        password = os.environ.get("NAM_NEO4J__PASSWORD")
        if password:
            cmd += ["--password", password]
        elif strict:
            raise SystemExit(
                "No MEMORY_API_KEY (NAMS) and no NAM_NEO4J__PASSWORD (local Neo4j) set.\n"
                "Set one — see .env.example."
            )
        else:
            cmd += ["--password", _PASSWORD_PLACEHOLDER]

    if args.extra:
        # argparse.REMAINDER keeps a leading "--"; drop it.
        extra = list(args.extra)
        if extra and extra[0] == "--":
            extra = extra[1:]
        cmd += extra
    return cmd


def _redact(cmd: Sequence[str]) -> List[str]:
    out: List[str] = []
    redact_next = False
    for tok in cmd:
        if redact_next:
            out.append("***" if tok != _PASSWORD_PLACEHOLDER else tok)
            redact_next = False
            continue
        out.append(tok)
        if tok == "--password":
            redact_next = True
    return out


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="omnigent-neo4j-memory",
        description="Graph memory for Omnigent agents (neo4j-agent-memory / NAMS).",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    s = sub.add_parser("serve", help="Launch the host-level shared MCP sidecar (ADR-0001).")
    s.add_argument("--host", default=os.environ.get("OMNIGENT_MEMORY_HOST", DEFAULT_HOST),
                   help="Bind host. Set '' to omit --host on builds that don't accept it.")
    s.add_argument("--port", default=os.environ.get("OMNIGENT_MEMORY_PORT", DEFAULT_PORT))
    s.add_argument("--transport", default=os.environ.get("OMNIGENT_MEMORY_TRANSPORT", DEFAULT_TRANSPORT))
    s.add_argument("--profile", default=os.environ.get("OMNIGENT_MEMORY_PROFILE", DEFAULT_PROFILE),
                   choices=["core", "extended"])
    s.add_argument("--print-cmd", action="store_true",
                   help="Print the resolved command (secrets redacted) and exit. No server started.")
    s.add_argument("extra", nargs=argparse.REMAINDER,
                   help="Extra args passed through to `neo4j-agent-memory mcp serve` (after --).")

    args = parser.parse_args(argv)

    if args.command == "serve":
        backend = resolve_backend()
        if args.print_cmd:
            cmd = build_serve_command(args, strict=False)
            print(f"# backend: {backend}")
            print(" ".join(_redact(cmd)))
            return 0
        cmd = build_serve_command(args, strict=True)
        print(f"[omnigent-neo4j-memory] backend={backend} → {' '.join(_redact(cmd))}", file=sys.stderr)
        os.execvp(cmd[0], cmd)  # replace this process with the server
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
