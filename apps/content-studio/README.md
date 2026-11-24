# Content studio

Turns a brief into an outline and a draft, then sends it for human review; reviewers approve, or comment and it revises.

## Run it

You need a running server ([install](https://sandaal.github.io/ai-app-server/install/)) and a model key:

```bash
aiapp secret set OPENAI_API_KEY          # or use another provider, see below
cd content-studio
aiapp deploy
```

Open **http://127.0.0.1:8080/apps/content-studio/** for the brief form (reviews at `/apps/content-studio/_approvals/`).

Or call it:

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"brief":"Announce our new support hours: 8am-8pm, Monday to Saturday","kind":"blog","words":300}' \
  http://127.0.0.1:8080/apps/content-studio/drafts
```

## Extend it

- **House style:** edit `content.instructions`.
- **Reviewers:** give them keys or sign-in with the `approver` role.
- **Publishing:** set `content.publish_topic` and subscribe to it to push approved pieces to your CMS.

## Change it and redeploy

1. Copy this folder into your own repository (keep the folder; rename `app:` in `ai-app.yaml` if you like).
2. Make your changes. While you work, `aiapp dev` redeploys on every save and keeps the last good version if something breaks.
3. Check it: `aiapp test` (if there is a `tests/` folder) and `aiapp eval` (with `evals/`).
4. Deploy to your server: `aiapp deploy`. Every deploy is a new version with no downtime; `aiapp rollback` goes back.

**Another model provider:** change `models:` in `ai-app.yaml` (Azure OpenAI, Anthropic, Gemini, Bedrock, or a local Ollama), see [Model providers](https://sandaal.github.io/ai-app-server/install/models/).

**Before others use it:** API keys or sign-in, HTTPS and quotas, see the [security checklist](https://sandaal.github.io/ai-app-server/operate/security/).

Blueprint: `content` · [All settings](https://sandaal.github.io/ai-app-server/build/blueprints/) · [ai-app.yaml reference](https://sandaal.github.io/ai-app-server/build/manifest/)
