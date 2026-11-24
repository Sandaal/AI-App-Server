"""Durable workflows with checkpointed steps and human approvals.

    @app.workflow
    async def refund(wf, input):
        order = await wf.step("lookup", lookup_order, input["order_id"])
        decision = await wf.approval("refund", f"Refund {order['total']} to {order['customer']}?", order)
        if not decision.approved:
            return {"refunded": False, "reason": decision.comment or decision.state}
        await wf.step("pay", issue_refund, order)
        return {"refunded": True}

Declare it as a job in ai-app.yaml (``jobs: [{name: refund, handler: "handlers:refund"}]``)
and start it with ``app.jobs.enqueue("refund", {...})``.

A workflow runs as a durable job. Every ``wf.step`` saves its result, so when
the workflow runs again (after a restart, a retry, or an approval) completed
steps return their saved results instead of running twice. ``wf.approval``
waits for a person: while the decision is pending the job is parked (it uses no
worker and no attempts) and the workflow runs again once someone decides or the
approval expires. Code between steps must therefore be deterministic, and step
results must be JSON-serialisable.
"""

from __future__ import annotations

import asyncio
import inspect
import json
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from aiapp import host
from aiapp.v1 import worker_pb2 as pb

CHECKPOINTS = "_workflows"
CHECKPOINT_TTL = 30 * 24 * 3600


class Suspended(Exception):
    """Raised inside a workflow that must wait (for an approval). The runtime
    reports it to the core, which parks the job until it is resumed."""

    code = "workflow_suspended"


@dataclass(frozen=True)
class Decision:
    approved: bool
    state: str  # approved | rejected | expired
    by: str
    comment: str


class Workflow:
    def __init__(self, job_id: str, input: Any, attempt: int = 1) -> None:
        self.job_id = job_id
        self.input = input
        self.attempt = attempt

    async def step(self, name: str, fn: Callable[..., Any], *args, timeout: float | None = None, **kwargs) -> Any:
        """Run fn once for this workflow and save its result; on later runs
        return the saved result. Names must be unique within a workflow run."""
        from aiapp.app import app  # late import: aiapp.app imports this module's users

        key = f"{self.job_id}/{name}"
        saved = await app.kv.get(key, namespace=CHECKPOINTS)
        if saved is not None:
            return json.loads(saved)["value"]
        result = fn(*args, **kwargs)
        if inspect.isawaitable(result):
            result = await (asyncio.wait_for(result, timeout) if timeout else result)
        await app.kv.put(key, json.dumps({"value": result}), namespace=CHECKPOINTS, ttl=CHECKPOINT_TTL)
        return result

    async def approval(self, key: str, title: str, details: Any = None, *, timeout: float = 7 * 24 * 3600) -> Decision:
        """Ask a person to approve. Returns their decision; while it is pending
        the workflow stops here and runs again once it is decided or expires."""
        c = host.client()
        info = await c.stub.ApprovalRequest(
            pb.ApprovalRequestMsg(
                job_id=self.job_id, key=key, title=title,
                details_json=json.dumps(details) if details is not None else "",
                timeout_s=int(timeout),
            ),
            metadata=c.metadata,
        )
        if info.state == "pending":
            raise Suspended(f"waiting for approval {info.id}: {title}")
        return Decision(info.state == "approved", info.state, info.by, info.comment)


def workflow(fn: Callable[[Workflow, Any], Awaitable[Any]]):
    """Decorator: turn ``async def name(wf, input)`` into a job handler."""

    async def handler(req):
        job_id = req.headers.get("x-aiapp-job-id")
        if not job_id:
            raise RuntimeError(f"{fn.__name__} is a workflow: run it as a job (app.jobs.enqueue), not as a route")
        wf = Workflow(job_id, req.json(), int(req.headers.get("x-aiapp-job-attempt", "1")))
        return await fn(wf, wf.input)

    handler.__name__ = fn.__name__
    handler.__doc__ = fn.__doc__
    handler.__wrapped__ = fn
    return handler
