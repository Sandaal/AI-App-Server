# Custom routes in Python

Your own HTTP routes: JSON in and out with status codes, one model call, and a streamed chat with conversation memory.

| | |
|---|---|
| `ai-app.yaml` | the app |
| `handlers.py` | the three routes |
| `tests/` | tests: `aiapp test` |

## Run it

With a running server ([install](https://sandaal.github.io/ai-app-server/install/)) and a model key (`aiapp secret set OPENAI_API_KEY`):

```bash
cd custom-routes
aiapp test      # runs with scripted models: no key or cost
aiapp deploy
```

Try it:

```bash
curl -X POST -d '{"name":"Ada"}' http://127.0.0.1:8080/apps/custom-routes/hello
curl -N -X POST -H "X-Session-Id: s1" -d '{"message":"Hi, I am Ada"}' http://127.0.0.1:8080/apps/custom-routes/chat
```

## Extend it

- Add a route: a line under `routes:` and a function in `handlers.py`.
- Require a role: `roles: [staff]` on the route, and keys with `aiapp key create custom-routes --role staff`.
- Use storage, search and jobs: see [Storage](https://sandaal.github.io/ai-app-server/build/storage/) and [Jobs](https://sandaal.github.io/ai-app-server/build/jobs-events/).

## Change it and redeploy

Copy the folder into your own repository, change it (`aiapp dev` redeploys on every save), run `aiapp test`, then `aiapp deploy` to your server. `aiapp rollback` goes back.

Guide: [Handlers](https://sandaal.github.io/ai-app-server/build/handlers/)
