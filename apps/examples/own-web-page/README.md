# Your own web page

A page of your own, served by the app, with the built-in `<aiapp-chat>` component and a call to your own route.

| | |
|---|---|
| `ai-app.yaml` | the app |
| `ui/index.html` | the page |
| `handlers.py` | the `/tip` route the page calls |
| `docs/` | what the chat answers from |
| `tests/` | tests: `aiapp test` |

## Run it

With a running server ([install](https://sandaal.github.io/ai-app-server/install/)) and a model key (`aiapp secret set OPENAI_API_KEY`):

```bash
cd own-web-page
aiapp test      # runs with scripted models: no key or cost
aiapp deploy
```

Try it:

```bash
open http://127.0.0.1:8080/apps/own-web-page/
```

## Extend it

- Style the components with CSS variables (`--aiapp-accent`, `--aiapp-height`…).
- Put the same components on another site: add `cors: { origins: [...] }` and load `https://YOUR-SERVER/_sdk/aiapp.js`.
- Sign people in on the page: see [Sign-in](https://sandaal.github.io/ai-app-server/operate/sign-in/).

## Change it and redeploy

Copy the folder into your own repository, change it (`aiapp dev` redeploys on every save), run `aiapp test`, then `aiapp deploy` to your server. `aiapp rollback` goes back.

Guide: [Web](https://sandaal.github.io/ai-app-server/build/web/)
