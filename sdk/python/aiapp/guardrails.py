"""Write guardrails in Python.

A guardrail is a handler named in ``ai-app.yaml``::

    guardrails:
      - no-competitors: { handler: "guards:competitors", stage: both }

The core calls it with the texts to check and sends its decision on::

    from aiapp import guardrails

    async def competitors(req):
        check = guardrails.Check.from_request(req)
        if any("fabrikam" in t.lower() for t in check.texts):
            return guardrails.block("mentions a competitor", message="I can only talk about Contoso.")
        return guardrails.allow()

On input, ``texts`` are the request's text fields; on output, the one
response text, with the handler's end ``metadata`` (``citations`` ...).
A plugin can call ``app.models`` too, to use a model as a classifier.
If it fails or times out (10 s), the request is refused unless the entry
sets ``on_error: allow``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Check:
    stage: str  # "input" or "output"
    route: str
    texts: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_request(cls, req) -> "Check":
        d = json.loads(req.body or b"{}")
        return cls(stage=d.get("stage", ""), route=d.get("route", ""), texts=list(d.get("texts") or []),
                   metadata=dict(d.get("metadata") or {}))


def allow() -> dict:
    return {"action": "allow"}


def redact(texts: list[str], reason: str = "") -> dict:
    """Continue with these texts instead (same number as Check.texts)."""
    return {"action": "redact", "texts": list(texts), "reason": reason}


def block(reason: str = "", message: str | None = None) -> dict:
    """Stop. reason goes to the audit log; message, if given, is what the caller sees."""
    out = {"action": "block", "reason": reason}
    if message:
        out["message"] = message
    return out
