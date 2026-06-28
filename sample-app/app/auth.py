"""Minimal JWT auth — the surface the demo's coder agent extends.

Owner: platform team. Decision on record: tokens are signed with RS256 (asymmetric), never HS256.
Hazard on record: pyjwt < 2.0 caused incident #42 (algorithm-confusion). Keep pyjwt >= 2.0.

This is intentionally tiny and dependency-light (no real `pyjwt` import) so the demo runs anywhere;
the agents reason about the *design*, and memory records the decisions.
"""

from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass

ALGORITHM = "RS256"  # decision on record — see module docstring
ACCESS_TOKEN_TTL_SECONDS = 24 * 60 * 60  # 24h


@dataclass
class UserAuth:
    """Issues and verifies access tokens for a user.

    A stand-in for a real JWT handler. `issue_token` / `verify_token` model the shape; the demo's
    Run 1 task is to add refresh-token support without weakening the RS256 decision.
    """

    issuer: str = "sample-app"

    def issue_token(self, subject: str, ttl_seconds: int = ACCESS_TOKEN_TTL_SECONDS) -> str:
        header = {"alg": ALGORITHM, "typ": "JWT"}
        now = int(time.time())
        payload = {"iss": self.issuer, "sub": subject, "iat": now, "exp": now + ttl_seconds}
        return f"{_b64(header)}.{_b64(payload)}.<signature:{ALGORITHM}>"

    def verify_token(self, token: str) -> dict:
        try:
            header_b64, payload_b64, _sig = token.split(".")
        except ValueError as exc:  # pragma: no cover - defensive
            raise ValueError("malformed token") from exc
        header = _unb64(header_b64)
        if header.get("alg") != ALGORITHM:
            # Rejecting unexpected algorithms is exactly the incident-#42 lesson.
            raise ValueError(f"unexpected alg {header.get('alg')!r}; expected {ALGORITHM}")
        payload = _unb64(payload_b64)
        if payload.get("exp", 0) < int(time.time()):
            raise ValueError("token expired")
        return payload


def _b64(obj: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(obj).encode()).decode().rstrip("=")


def _unb64(s: str) -> dict:
    pad = "=" * (-len(s) % 4)
    return json.loads(base64.urlsafe_b64decode(s + pad))
