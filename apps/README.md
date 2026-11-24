# Example apps

Complete apps you can deploy as they are, then change and redeploy to your own server. Each folder has a README on how to run it, extend it and redeploy it.

## Use cases

| App | What it does | Blueprint |
|---|---|---|
| [hr-policy-chat](hr-policy-chat/) | answers employees' questions from HR documents, with citations | `knowledge-chat` |
| [customer-support](customer-support/) | support chat with order lookup tools, refund approvals and handoff to a person | `customer-support` |
| [invoice-extraction](invoice-extraction/) | fields from invoices (PDF, scans, photos) as JSON with page evidence | `document-extraction` |
| [document-summary](document-summary/) | summaries and key points of long documents | `summarization` |
| [ticket-triage](ticket-triage/) | sorts support tickets into your labels | `classification` |
| [meeting-notes](meeting-notes/) | recordings or transcripts to decisions and action items | `meeting-notes` |
| [content-studio](content-studio/) | brief to draft, with human review and revisions | `content` |
| [sales-insights](sales-insights/) | questions about your data, answered with SQL you can see | `insights` |
| [code-assistant](code-assistant/) | questions about a codebase, with file and line citations | `code-assistant` |
| [ops-agent](ops-agent/) | an agent that uses your tools, with approval for risky ones | `workflow-agent` |

## How to add…

| Example | Shows |
|---|---|
| [custom-routes](examples/custom-routes/) | your own routes in Python: JSON, a model call, streaming with memory |
| [tools-agent](examples/tools-agent/) | the model calling your functions |
| [approval-workflow](examples/approval-workflow/) | a durable workflow where a manager approves large refunds |
| [guardrail-plugin](examples/guardrail-plugin/) | your own safety rule next to the built-in guardrails |
| [scheduled-report](examples/scheduled-report/) | a nightly job, events and a subscriber |
| [connectors](examples/connectors/) | SharePoint, Git, websites, databases, S3, Azure Blob |
| [own-web-page](examples/own-web-page/) | your own page with the chat component and your own route |
| [customized-blueprint](examples/customized-blueprint/) | a blueprint's code copied into the app and changed |

## The usual loop

```bash
cp -r apps/customer-support ~/my-support      # start from the closest example
cd ~/my-support
aiapp dev                                     # change files; every save redeploys
aiapp test                                    # tests with scripted models (no cost)
aiapp deploy                                  # to your server; aiapp rollback goes back
```

These apps use OpenAI (`aiapp secret set OPENAI_API_KEY`). To use Azure OpenAI, Anthropic, Gemini, Bedrock or a local Ollama, change `models:` in `ai-app.yaml`: see [Model providers](https://sandaal.github.io/ai-app-server/install/models/).

How the built-in blueprints work inside: their Python source is in [`sdk/python/aiapp/blueprints/`](../sdk/python/aiapp/blueprints/). To change one beyond its settings, copy its logic into your own handlers.
