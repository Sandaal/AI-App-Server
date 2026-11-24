# Build apps

An app is a folder with an `ai-app.yaml` file. Start from a blueprint, then change settings or add your own Python.

## Learn the basics

1. [Your first app](first-app.md): a blueprint app, then an app with your own Python handler.
2. [The ten blueprints](blueprints.md): what each ready-made app does.
3. [The ai-app.yaml file](manifest.md): every section, in one page.

## Add features

| I want to… | Guide |
|---|---|
| answer from documents, websites, SharePoint, databases | [Documents and connectors](documents.md) |
| write my own routes in Python | [Python handlers](handlers.md) |
| remember conversations, store data, search | [Storage, memory and search](storage.md) |
| let the model call my functions or MCP servers | [Agents, tools and MCP](agents.md) |
| have a person approve a step (refunds, publishing) | [Workflows and approvals](workflows.md) |
| run work in the background, on a schedule, or on events | [Jobs, schedules and events](jobs-events.md) |
| block or redact unsafe content | [Guardrails](guardrails.md) |
| put a chat box or upload on my web page | [Pages and web components](web.md) |
| call an app from my code (JS, Python, curl, OpenAI SDKs) | [Call apps from your code](clients.md) |
| let Claude, Copilot or IDE agents use my app | [Publish apps to AI agents (MCP)](mcp-server.md) |
| test my app and check answer quality | [Test and evaluate](testing.md) |
| see my own steps in traces | [Traces in your code](tracing.md) |
| work in VS Code | [VS Code](vscode.md) |

## The development loop

```bash
aiapp new knowledge-chat my-app --provider openai   # start from a blueprint
cd my-app
aiapp dev          # serve this folder; every save redeploys (a broken save keeps the last good code)
aiapp test         # run tests/ with scripted models
aiapp deploy       # a new immutable version, zero downtime
aiapp logs         # model calls: tokens, cost, latency
aiapp trace        # requests, step by step
```
