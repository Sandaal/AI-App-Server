# A blueprint's code, copied and changed

When settings aren't enough, copy a blueprint's Python into your app and change it. Here the `knowledge-chat` blueprint's code is in `my_chat.py`, changed so answers are short and signed, and the `/chat` route points at it.

| | |
|---|---|
| `ai-app.yaml` | keeps `blueprint: knowledge-chat`; the route's handler is `my_chat:chat` |
| `my_chat.py` | the copy of `sdk/python/aiapp/blueprints/knowledge_chat.py`, with a changed system prompt |
| `docs/` | what it answers from |
| `tests/` | checks the route runs the copy: `aiapp test` |

## Do the same with any blueprint

1. Copy the file from [`sdk/python/aiapp/blueprints/`](../../../sdk/python/aiapp/blueprints/) into your app.
2. Point the route (or job) at it in `ai-app.yaml`: `handler: "my_file:function"`. List every route the app needs, because listing routes replaces the blueprint's defaults.
3. Change it, run `aiapp test`, then `aiapp deploy`.

To undo, point the handler back at `aiapp.blueprints.knowledge_chat:chat`. Your copy doesn't change when you upgrade the server; compare it with new releases now and then.

Guide: [Customize a blueprint's code](https://sandaal.github.io/aiapp-server/build/customize-blueprints/)
