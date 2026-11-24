# HR policy chat

A chat assistant that answers employees' questions from your HR documents, with citations, and remembers the conversation.

## What's in this folder

| | |
|---|---|
| `ai-app.yaml` | the app: models, settings, guardrails, page |
| `policies/` | the documents it answers from (Markdown, PDF, Word, PowerPoint, Excel, HTML, email) |
| `tests/` | tests run by `aiapp test` with scripted models |
| `evals/golden.yaml` | quality checks run by `aiapp eval` with your real model |

`.github/copilot-instructions.md` teaches coding assistants this SDK.

## Run it

You need a running server ([install](https://sandaal.github.io/aiapp-server/install/)) and a model key:

```bash
aiapp secret set OPENAI_API_KEY          # or use another provider, see below
cd hr-policy-chat
aiapp deploy
```

Open **http://127.0.0.1:8080/apps/hr-policy-chat/** for the chat page.

Or call it:

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"message":"How many days of annual leave do I get?"}' \
  http://127.0.0.1:8080/apps/hr-policy-chat/chat
```

## Extend it

- **Your documents:** replace the files in `policies/` (or add folders with `aiapp source add PATH`) and redeploy; only changed files are re-indexed.
- **SharePoint, Git, websites, S3, databases:** add a connector under `sources:` ([guide](https://sandaal.github.io/aiapp-server/build/documents/)).
- **Stricter answers:** uncomment `citations-required` so it never answers without a document, and `output-pii` to redact personal data in answers.
- **Sign-in:** add `auth.oidc` so only your employees can use it ([guide](https://sandaal.github.io/aiapp-server/operate/sign-in/)).
- **Your intranet page:** embed `<aiapp-chat app="hr-policy-chat">` ([guide](https://sandaal.github.io/aiapp-server/build/web/)).

## Change it and redeploy

1. Copy this folder into your own repository (keep the folder; rename `app:` in `ai-app.yaml` if you like).
2. Make your changes. While you work, `aiapp dev` redeploys on every save and keeps the last good version if something breaks.
3. Check it: `aiapp test` (if there is a `tests/` folder) and `aiapp eval` (with `evals/`).
4. Deploy to your server: `aiapp deploy`. Every deploy is a new version with no downtime; `aiapp rollback` goes back.

**Another model provider:** change `models:` in `ai-app.yaml` (Azure OpenAI, Anthropic, Gemini, Bedrock, or a local Ollama), see [Model providers](https://sandaal.github.io/aiapp-server/install/models/).

**Before others use it:** API keys or sign-in, HTTPS and quotas, see the [security checklist](https://sandaal.github.io/aiapp-server/operate/security/).

Blueprint: `knowledge-chat` · [All settings](https://sandaal.github.io/aiapp-server/build/blueprints/) · [ai-app.yaml reference](https://sandaal.github.io/aiapp-server/build/manifest/)
