# Workflow with a human approval

A durable refund workflow: small refunds are paid at once, larger ones wait for a manager's approval, for as long as it takes, without holding a worker. Every step's result is saved, so restarts and retries continue where they left off.

| | |
|---|---|
| `ai-app.yaml` | the app |
| `handlers.py` | the workflow (`@app.workflow`) and the routes that start it and report on it |
| `tests/` | tests: `aiapp test` |

## Run it

With a running server ([install](https://sandaal.github.io/ai-app-server/install/)) and a model key (`aiapp secret set OPENAI_API_KEY`):

```bash
cd approval-workflow
aiapp test      # runs with scripted models: no key or cost
aiapp deploy
```

Try it:

```bash
curl -X POST -d '{"order_id":"A-1001"}' http://127.0.0.1:8080/apps/approval-workflow/refund
aiapp approvals approval-workflow            # the waiting refund
aiapp approve approval-workflow APPROVAL_ID
```

## Extend it

- Replace `lookup_order` and `pay_refund` with your systems; anything with side effects belongs in a `wf.step`.
- Approve from the page `/apps/approval-workflow/_approvals/` (role `approver`), or put `<aiapp-approvals>` on your own page.
- Add more approval steps, or different approvers by role.

## Change it and redeploy

Copy the folder into your own repository, change it (`aiapp dev` redeploys on every save), run `aiapp test`, then `aiapp deploy` to your server. `aiapp rollback` goes back.

Guide: [Workflows](https://sandaal.github.io/ai-app-server/build/workflows/)
