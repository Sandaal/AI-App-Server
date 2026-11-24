"""POST /refund starts a workflow; small refunds are paid at once, larger
ones wait for someone with the approver role:
  aiapp approvals approval-workflow      then   aiapp approve approval-workflow ID
or the page /apps/approval-workflow/_approvals/."""

from aiapp import app

ORDERS = {"A-1001": {"customer": "Ada", "total": 249.0}, "A-1002": {"customer": "Alan", "total": 35.0}}


def lookup_order(order_id: str) -> dict:
    return ORDERS[order_id]                 # replace with your order system


def pay_refund(order: dict) -> str:
    return f"refund-{order['customer'].lower()}"   # replace with your payment API; returns a reference


@app.workflow
async def refund(wf, input):
    order = await wf.step("lookup", lookup_order, input["order_id"])
    if order["total"] > 100:
        decision = await wf.approval("refund", f"Refund {order['total']:.2f} to {order['customer']}?", order)
        if not decision.approved:
            return {"refunded": False, "reason": decision.comment or decision.state}
    ref = await wf.step("pay", pay_refund, order)
    return {"refunded": True, "reference": ref}


async def start(req):
    job = await app.jobs.enqueue("refund", {"order_id": req.json()["order_id"]})
    return {"job": job.id}


async def status(req):
    job = await app.jobs.get(req.json()["job"])
    return {"state": job.state, "result": job.result}
