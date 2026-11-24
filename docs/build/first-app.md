# Your first app

## Part 1: a blueprint app

```bash
aiapp new knowledge-chat hr-bot --provider openai
cd hr-bot
```

You get a folder like this:

```
hr-bot/
  ai-app.yaml          # the app: models, sources, routes, guardrails, page
  policies/            # documents it answers from (a sample is included)
  tests/               # tests run by `aiapp test`
  evals/               # quality checks run by `aiapp eval`
  .github/copilot-instructions.md   # explains the SDK to coding assistants
```

Add your documents and deploy:

```bash
aiapp source add ./policies/
aiapp deploy
```

Open `http://127.0.0.1:8080/apps/hr-bot/`. That's a complete app: chat page, citations, conversation memory, guardrails.

## Part 2: an app with your own Python

Create a folder `greeter` with two files.

`ai-app.yaml`:

```yaml
app: greeter
version: "1"
models:
  chat: { provider: openai, model: gpt-4o-mini }
routes:
  - { path: /hello, handler: "handlers:hello" }
  - { path: /story, handler: "handlers:story", stream: true }
```

`handlers.py`:

```python
from aiapp import app

async def hello(req):
    name = (req.json() or {}).get("name", "world")
    return {"greeting": f"Hello, {name}!"}

async def story(req):
    topic = req.json()["topic"]
    async for text in app.models.chat.stream(f"Tell a three-sentence story about {topic}."):
        yield text            # streamed to the caller as it arrives
```

Deploy and call it:

```bash
cd greeter && aiapp deploy
curl -X POST -d '{"name":"Ada"}' http://127.0.0.1:8080/apps/greeter/hello
curl -N -X POST -d '{"topic":"a lighthouse"}' http://127.0.0.1:8080/apps/greeter/story
```

- A handler **returns** a value (dict and list become JSON, strings become text), or **yields** to stream.
- `req` has the request: `req.json()`, `req.text`, `req.query`, `req.headers`, `req.principal` (who is calling). See [Python handlers](handlers.md).
- `app.models.chat` is the model named `chat` in `ai-app.yaml`.

## Part 3: develop with hot reload

```bash
aiapp dev
```

Every time you save a file, the app redeploys. If you save broken code, the last good version keeps serving and the error is shown.

Next: [the ai-app.yaml file](manifest.md) or [the ten blueprints](blueprints.md).
