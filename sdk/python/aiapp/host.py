"""Connection from a worker back to the core's Host service.

The runtime connects once at startup; handlers reach it through ``aiapp.app``.
"""

from __future__ import annotations

import contextvars
from dataclasses import dataclass

import grpc

from aiapp.v1 import worker_pb2_grpc as pbg

TOKEN_HEADER = "x-aiapp-token"
INVOCATION_HEADER = "x-aiapp-invocation"

# The invocation being served, so host calls can be traced to the request.
current_invocation: contextvars.ContextVar[str] = contextvars.ContextVar("aiapp_invocation", default="")

# The active trace (trace_id, span_id) as lower-case hex: the core's span for
# this invocation, or the innermost app.span(). Host calls carry it, so they
# nest under that span.
current_trace: contextvars.ContextVar[tuple[str, str] | None] = contextvars.ContextVar("aiapp_trace", default=None)

# Finished app.span() spans waiting to be sent; one list per invocation.
pending_spans: contextvars.ContextVar[list | None] = contextvars.ContextVar("aiapp_spans", default=None)


def parse_traceparent(tp: str) -> tuple[str, str] | None:
    """(trace_id, span_id) from a W3C traceparent, or None."""
    parts = (tp or "").split("-")
    if len(parts) < 4 or len(parts[1]) != 32 or len(parts[2]) != 16:
        return None
    try:
        int(parts[1], 16), int(parts[2], 16)
    except ValueError:
        return None
    if parts[1] == "0" * 32 or parts[2] == "0" * 16:
        return None
    return parts[1], parts[2]


# Metadata sent with the response's end event (e.g. citations); set per invocation.
current_metadata: contextvars.ContextVar[dict | None] = contextvars.ContextVar("aiapp_metadata", default=None)


def set_metadata(key: str, value) -> None:
    """Attach JSON-compatible metadata to the current response's end event."""
    md = current_metadata.get()
    if md is None:
        raise RuntimeError("set_metadata is only available inside a handler")
    md[key] = value


@dataclass
class HostClient:
    channel: grpc.aio.Channel
    token: str

    def __post_init__(self) -> None:
        self.stub = pbg.HostStub(self.channel)

    @property
    def metadata(self) -> tuple[tuple[str, str], ...]:
        md = [(TOKEN_HEADER, self.token)]
        inv = current_invocation.get()
        if inv:  # so the core can put the call in the request's trace
            md.append((INVOCATION_HEADER, inv))
        tr = current_trace.get()
        if tr:  # inside app.span(): the call nests under it
            md.append(("traceparent", f"00-{tr[0]}-{tr[1]}-01"))
        return tuple(md)


_client: HostClient | None = None


def connect(channel: grpc.aio.Channel, token: str) -> None:
    global _client
    _client = HostClient(channel, token)


def client() -> HostClient:
    if _client is None:
        raise RuntimeError("not connected to the core; handlers run inside `aiapp serve`")
    return _client
