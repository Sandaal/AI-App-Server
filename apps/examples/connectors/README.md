# Documents from other systems

A chat app over documents, with ready-to-uncomment connectors for SharePoint, Git, websites, databases, S3 and Azure Blob. The local `docs/` folder works as is.

| | |
|---|---|
| `ai-app.yaml` | the app |
| `docs/` | a local document |
| `tests/` | tests: `aiapp test` |

## Run it

With a running server ([install](https://sandaal.github.io/aiapp-server/install/)) and a model key (`aiapp secret set OPENAI_API_KEY`):

```bash
cd connectors
aiapp test      # runs with scripted models: no key or cost
aiapp deploy
```

Try it:

```bash
curl -X POST -d '{"message":"How long do I have to return an item?"}' http://127.0.0.1:8080/apps/connectors/chat
```

## Extend it

- Uncomment a connector in `ai-app.yaml`, store its secret with `aiapp secret set NAME`, and redeploy.
- `aiapp sources connectors` shows each connector's last sync; `aiapp source sync connectors` syncs now.
- Details for each connector: [Documents and connectors](https://sandaal.github.io/aiapp-server/build/documents/).

## Change it and redeploy

Copy the folder into your own repository, change it (`aiapp dev` redeploys on every save), run `aiapp test`, then `aiapp deploy` to your server. `aiapp rollback` goes back.

Guide: [Documents](https://sandaal.github.io/aiapp-server/build/documents/)
