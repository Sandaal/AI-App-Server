# Workflows and approvals

A **workflow** is a durable, multi-step job. Each step's result is saved, so after a restart, a retry or an approval it continues where it left off. A step can wait for a **person's approval** for as long as needed, without holding a worker.

## Write a workflow

`handlers.py`:

```python
from aiapp import app

@app.workflow
async def refund(wf, input):
    order = await wf.step("lookup", lookup_order, input["order_id"])
    decision = await wf.approval("refund", f"Refund {order['total']} to {order['customer']}?", order)
    if not decision.approved:
        return {"refunded": False, "reason": decision.comment or decision.state}
    await wf.step("pay", issue_refund, order)
    return {"refunded": True}
```

`ai-app.yaml`:

```yaml
jobs:
  - { name: refund, handler: "handlers:refund" }
```

Start it from a route or anywhere in your code:

```python
job = await app.jobs.enqueue("refund", {"order_id": "A-1001"})
```

**Rules:**

- Step results must be JSON-serialisable.
- Code between steps must be deterministic (it runs again when the workflow resumes); put anything with side effects in a `wf.step`.
- `decision.state` is `approved`, `rejected` or `expired`; `decision.by` and `decision.comment` say who and why.

## Decide approvals

People need the `approver` role (an [API key](../operate/keys.md) with `--role approver`, or a sign-in role mapped to it).

| Where | How |
|---|---|
| The built-in page | `http://SERVER:8080/apps/APP/_approvals/` |
| The command line | `aiapp approvals APP`, then `aiapp approve APP ID` or `aiapp reject APP ID` |
| Your own page | the `<aiapp-approvals app="APP">` [web component](web.md) |
| Your code | the JS client: `client.approvals.pending()` and `client.approvals.decide(id, true, "ok")` |

## Approvals without writing a workflow

The `customer-support` and `workflow-agent` blueprints turn chosen tools into approvals by configuration:

```yaml
support:      # or agent:
  approval_required: [refund_order]
  approval_timeout: 24h
```

## Follow a workflow

`aiapp jobs APP` and `aiapp jobs show APP ID` show its state (`waiting` while an approval is pending), and `aiapp trace ID` shows its steps.
