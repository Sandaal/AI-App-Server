"""Request and Response types handed to developer handlers."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from urllib.parse import parse_qs
from typing import Any


@dataclass(frozen=True)
class Principal:
    """The authenticated caller, as established by the core."""

    subject: str = ""
    roles: tuple[str, ...] = ()
    claims: dict[str, str] = field(default_factory=dict)

    @property
    def authenticated(self) -> bool:
        return bool(self.subject)

    @property
    def tenant(self) -> str:
        """The caller's tenant when the app keeps tenants apart (auth.oidc.tenant_isolation), else ""."""
        return self.claims.get("aiapp_tenant", "")

    def has_role(self, *roles: str) -> bool:
        """True if the caller has one of roles; admin has them all."""
        return "admin" in self.roles or any(r in self.roles for r in roles)


@dataclass(frozen=True)
class Request:
    """One HTTP request routed to a handler. Header names are lower-case."""

    method: str
    route: str
    headers: dict[str, str]
    body: bytes
    session_id: str = ""
    invocation_id: str = ""
    principal: Principal = field(default_factory=Principal)
    query: dict[str, str] = field(default_factory=dict)  # URL query parameters (first value of each)
    traceparent: str = ""  # W3C trace context of the core's span for this call

    @property
    def text(self) -> str:
        """The body decoded as UTF-8."""
        return self.body.decode("utf-8", errors="replace")

    def json(self) -> Any:
        """The body parsed as JSON (None for an empty body)."""
        return json.loads(self.body) if self.body else None

    @property
    def event(self) -> "Event | None":
        """For a subscription handler: the delivered record's topic, offset,
        key, time and headers (the value is the body: ``req.json()``)."""
        h = self.headers
        if "x-aiapp-topic" not in h:
            return None
        return Event(
            topic=h["x-aiapp-topic"],
            offset=int(h.get("x-aiapp-offset", "0")),
            key=h.get("x-aiapp-key", ""),
            time=h.get("x-aiapp-time", ""),
            headers={k[len("x-aiapp-header-"):]: v for k, v in h.items() if k.startswith("x-aiapp-header-")},
            delivery=int(h.get("x-aiapp-delivery", "1") or 1),
            partition=int(h.get("x-aiapp-partition", "0") or 0),
            value=self.body,
        )

    @classmethod
    def from_proto(cls, msg: Any) -> "Request":
        p = msg.principal
        return cls(
            method=msg.method,
            route=msg.route,
            headers={k.lower(): v for k, v in msg.headers.items()},
            body=bytes(msg.body),
            session_id=msg.session_id,
            invocation_id=msg.invocation_id,
            principal=Principal(subject=p.subject, roles=tuple(p.roles), claims=dict(p.claims)),
            query={k: v[0] for k, v in parse_qs(msg.query, keep_blank_values=True).items()},
            traceparent=getattr(msg, "traceparent", ""),
        )


@dataclass(frozen=True)
class Event:
    """One topic record. ``delivery`` counts attempts for subscription
    handlers (1 the first time; delivery is at least once, so handle repeats)."""

    topic: str
    offset: int
    key: str
    time: str
    headers: dict[str, str]
    value: bytes
    delivery: int = 1
    partition: int = 0

    def json(self) -> Any:
        return json.loads(self.value) if self.value else None

    @property
    def text(self) -> str:
        return self.value.decode("utf-8", errors="replace")


@dataclass
class Response:
    """Return this from a handler to control status code and headers."""

    body: bytes | str = b""
    status: int = 200
    headers: dict[str, str] = field(default_factory=dict)
    content_type: str | None = None
