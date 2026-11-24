# hr-policy-chat: notes for coding assistants

This is an **AI App Server** app (blueprint: `knowledge-chat`). The server runs it from `ai-app.yaml`;
there is no web framework, Dockerfile or database to set up.

## Layout
- `ai-app.yaml` - the manifest: routes, models, sources, guardrails, jobs, topics, auth. The source of truth.
- `*.py` - handlers named in the manifest as `module:function`; `tools.py` holds `@app.tool` functions.
- `ai-app.<env>.yaml` - optional overlays (`aiapp deploy --env prod`); maps merge, lists replace.
- `tests/` - tests run by `aiapp test` with scripted models.
- `requirements.txt` - optional extra Python packages (installed per app).

## Writing handlers
A handler is an `async def handler(req: Request)` that returns a str, dict/list (JSON) or
`Response(...)`, or yields strings to stream (Server-Sent Events).
- `req.json()`, `req.text`, `req.headers`, `req.query`, `req.session_id`, `req.principal.has_role("admin")`
- Models (names from `models:`): `await app.models.chat.complete(user, system=..., temperature=0)`,
  `async for t in app.models.chat.stream(user, system=..., history=...)`,
  `await app.models.chat.json(text, schema={...}, name="x")` (validated against the schema),
  `await app.models.chat.run(user, tools=[fn, ...])` (tool-calling agent loop), `await app.models.embedding.embed([...])`.
  Provider failures raise `ModelError` (check `.code`, e.g. `budget_exceeded`).
- Documents: `await app.vectors.search("sources", question, k=5, mode="hybrid")` - hits have `.text`, `.metadata`, `.similarity`.
- State: `app.kv` (get/put with ttl, hashes, lists, sets, sorted sets, counters, `cas`, leases), `app.memory` (chat history per session).
- Background work: `await app.jobs.enqueue("name", payload)` (durable, retried; declare under `jobs:`);
  workflows with `@app.workflow`, `await wf.step("name", fn, ...)` and `await wf.approval(...)` for a person's decision.
- Events: `await app.events.publish("topic", {...})`; consume with `subscriptions:` in the manifest. `cron:` schedules jobs.
- Response metadata (e.g. citations) for streamed answers: `set_metadata("citations", [...])`.

## Rules
- Never put API keys or connection strings in files. Use `aiapp secret set NAME` and `${NAME}` / `api_key_env` in the manifest.
- Keep handlers async and fast; move slow or retryable work to a job.
- Don't log prompts, answers or personal data; the server audits model calls (tokens, cost) without text.
- Keep guardrails on (`pii-redaction`, `prompt-injection`); use `guardrail_mode: dry-run` to tune them, not removal.
- Change behaviour through `ai-app.yaml` settings before writing code; blueprint settings are documented in the manifest comments.
- Add or update a test in `tests/` with every change.

## Testing
```python
from aiapp.testing import AppTest

class MyTest(AppTest):
    def test_something(self):
        self.models.reply("scripted answer", when="word in the user message")   # also .json({...}), .tool_call(...), .fail(503)
        r = self.client.chat("question")          # or self.client.post("/route", {...}), .upload(...)
        self.assertIn("scripted answer", r.text)
        self.assertIn("expected passage", self.models.last.system)               # what the model was sent
```
Everything except the model is real (routes, workers, search, guardrails, jobs). Run with `aiapp test`.

## Evaluations
`evals/*.yaml` holds golden cases (input, body or file, with `expect:` checks: contains, not_contains,
regex, json field paths, citations, max_latency_ms, and a `judge` criterion graded by a model).
`aiapp eval` runs them against the deployed app with its real models; add a case for every behaviour you fix.

## Commands
`aiapp dev` (hot reload) · `aiapp deploy` · `aiapp test` · `aiapp logs` (model calls, cost) ·
`aiapp trace ID` (spans of one request) · `aiapp versions` / `aiapp rollback` · `aiapp console`

## This blueprint
Answers questions from the documents under `sources:` with numbered citations; `/chat` streams. Tune the system prompt and retrieval in the manifest, add documents with `aiapp source add`, and keep answers citing `[n]`.
