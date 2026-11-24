# Your own guardrail

A guardrail written in Python (no competitor names in questions or answers), together with built-in ones (prompt injection, personal data in answers).

| | |
|---|---|
| `ai-app.yaml` | the app |
| `guards.py` | the guardrail |
| `handlers.py` | the route it protects |
| `tests/` | tests: `aiapp test` |

## Run it

With a running server ([install](https://sandaal.github.io/aiapp-server/install/)) and a model key (`aiapp secret set OPENAI_API_KEY`):

```bash
cd guardrail-plugin
aiapp test      # runs with scripted models: no key or cost
aiapp deploy
```

Try it:

```bash
curl -X POST -d '{"question":"Is Fabrikam cheaper?"}' http://127.0.0.1:8080/apps/guardrail-plugin/ask     # refused
```

## Extend it

- Write your rule in `guards.py`: return `allow()`, `redact(texts)` or `block(reason, message)`.
- Use a model as a classifier inside the guardrail with `app.models`.
- Add `presidio` (names, addresses) or `azure-content-safety`: see [Guardrails](https://sandaal.github.io/aiapp-server/build/guardrails/).
- Tune safely with `guardrail_mode: dry-run`.

## Change it and redeploy

Copy the folder into your own repository, change it (`aiapp dev` redeploys on every save), run `aiapp test`, then `aiapp deploy` to your server. `aiapp rollback` goes back.

Guide: [Guardrails](https://sandaal.github.io/aiapp-server/build/guardrails/)
