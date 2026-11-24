# Traces in your code

Every request, job and event is traced: the server records each step (guardrails, your handler, model calls, storage, tools) with timings. See them with:

```bash
aiapp trace                # recent requests and jobs
aiapp trace ID             # one, as a tree; ID from the X-Invocation-Id header
```

or in the [console](../operate/console.md), or in your OpenTelemetry backend ([Monitoring](../operate/monitoring.md)).

## Add your own steps: `app.span()`

```python
from aiapp import app

async def ask(req):
    with app.span("retrieve", k=8) as s:            # async with works too
        hits = await app.vectors.search("sources", req.text, k=8)
        s.set("found", len(hits))
    with app.span("rerank"):
        hits = rerank(hits)[:4]
    async for t in app.models.chat.stream(req.text, system=context(hits)):
        yield t
```

```
POST /apps/hr-bot/ask                       820 ms
  handler handlers:ask                      812 ms
    retrieve                                 45 ms
      host.VectorSearch                      41 ms
    rerank                                    3 ms
    host.ChatStream   model chat (gpt-4o-mini)  750 ms   310 → 120 tokens
```

- Spans nest; model, storage and tool calls made inside a span appear as its children.
- An exception inside a span marks it failed (and still propagates). `s.fail("reason")` marks it without raising.
- Put names, counts and ids in attributes, **not prompts or personal data**.
- Spans are sent after the response, so they never slow it down.

## Join traces across services

Pass the trace context to services you call, so their spans join the same trace:

```python
import httpx
r = await httpx.AsyncClient().get("https://inventory.internal/api/stock", headers=app.trace_headers())
```

`req.traceparent` is the incoming trace context.
