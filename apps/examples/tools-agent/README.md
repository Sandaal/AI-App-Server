# Tools and an agent

The model calls your Python functions (stock and delivery lookups) until it can answer.

| | |
|---|---|
| `ai-app.yaml` | the app |
| `tools.py` | the tools (`@app.tool` functions) |
| `handlers.py` | the route that runs the agent |
| `tests/` | tests: `aiapp test` |

## Run it

With a running server ([install](https://sandaal.github.io/aiapp-server/install/)) and a model key (`aiapp secret set OPENAI_API_KEY`):

```bash
cd tools-agent
aiapp test      # runs with scripted models: no key or cost
aiapp deploy
```

Try it:

```bash
curl -X POST -d '{"question":"Is the grinder in stock, and how fast can you deliver to France?"}' http://127.0.0.1:8080/apps/tools-agent/ask
```

## Extend it

- Replace the examples in `tools.py` with calls to your systems; write precise docstrings, they are what the model reads.
- Add tools from MCP servers under `mcp:`.
- Make risky tools wait for a person: see the `approval-workflow` example and the `ops-agent` app.

## Change it and redeploy

Copy the folder into your own repository, change it (`aiapp dev` redeploys on every save), run `aiapp test`, then `aiapp deploy` to your server. `aiapp rollback` goes back.

Guide: [Agents](https://sandaal.github.io/aiapp-server/build/agents/)
