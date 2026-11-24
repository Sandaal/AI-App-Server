# Python handlers

A handler is a Python function named in `ai-app.yaml` as `module:function`. It can be `async` (recommended) or plain.

```yaml
routes:
  - { path: /ask, handler: "handlers:ask", stream: true }
  - { path: /refund, handler: "handlers:refund", roles: [refunds] }   # callers need this role
```

## The request

```python
async def ask(req):
    req.method          # "POST"
    req.json()          # parsed JSON body (None if empty)
    req.text            # body as text;  req.body is the raw bytes
    req.query           # {"page": "2"} from ?page=2
    req.headers         # lower-case names
    req.session_id      # from the X-Session-Id header (conversation key)
    req.invocation_id   # the id shown in aiapp trace and the X-Invocation-Id header
    p = req.principal   # who is calling (keys, sign-in)
    p.subject, p.roles, p.claims, p.has_role("approver"), p.tenant
```

## The answer

| Return | The caller gets |
|---|---|
| a `dict` or `list` | JSON |
| a `str` or `bytes` | text or bytes |
| `Response(body, status=201, headers={...}, content_type=...)` | full control |
| `yield` values (generator) | a stream (Server-Sent Events) |

```python
from aiapp import app, Response, set_metadata

async def ask(req):
    hits = await app.vectors.search("sources", req.json()["message"], k=4)
    set_metadata("citations", [{"n": i + 1, "source": h.metadata["source"]} for i, h in enumerate(hits)])
    context = "\n\n".join(h.text for h in hits)
    async for t in app.models.chat.stream(req.json()["message"], system="Answer from:\n" + context):
        yield t

async def create(req):
    return Response({"id": 42}, status=201)
```

`set_metadata` adds data to the stream's final `end` event (the built-in pages show `citations`).

## Models

`app.models.NAME` is a model from `models:` in `ai-app.yaml`.

```python
text = await app.models.chat.complete("Summarize: ...", system="Be brief.", temperature=0.2)

async for t in app.models.chat.stream("Explain ...", history=[{"role": "user", "content": "..."}]):
    ...

data = await app.models.chat.json("Extract the invoice fields", schema={
    "type": "object", "properties": {"total": {"type": "number"}, "due": {"type": "string"}}, "required": ["total"]})
# schema can also be a Pydantic model class

vectors = await app.models.embedding.embed(["first text", "second text"])
transcript = await app.models.speech.transcribe(audio_bytes)        # a speech-to-text model
answer = await app.models.chat.complete("What is in this picture?", images=[png_bytes])
```

Errors: a failed call (after the server's retries and fallback) raises `ModelError` with `.code` and `.retryable`.

```python
from aiapp import ModelError
try:
    text = await app.models.chat.complete(q)
except ModelError as e:
    return Response({"error": "the model is unavailable, try again"}, status=503)
```

## Dependencies

Put a `requirements.txt` in the app folder; the server installs it into the app's own environment on deploy.

## The manifest from code

`app.manifest` is the parsed `ai-app.yaml`, handy for your own settings.
