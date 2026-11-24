# Example apps

The [`apps/` folder](https://github.com/Sandaal/aiapp-server/tree/main/apps) of the public repository has complete, tested apps you can deploy as they are, then change and redeploy to your own server.

```bash
git clone https://github.com/Sandaal/aiapp-server.git
cp -r aiapp-server/apps/customer-support my-support
cd my-support
aiapp test          # the app's tests, with scripted models (no cost)
aiapp deploy        # to your server
```

## Use cases

| App | What it does |
|---|---|
| [hr-policy-chat](https://github.com/Sandaal/aiapp-server/tree/main/apps/hr-policy-chat) | answers employees' questions from HR documents, with citations |
| [customer-support](https://github.com/Sandaal/aiapp-server/tree/main/apps/customer-support) | support chat with order tools, refund approvals and handoff |
| [invoice-extraction](https://github.com/Sandaal/aiapp-server/tree/main/apps/invoice-extraction) | invoice fields as JSON with page evidence |
| [document-summary](https://github.com/Sandaal/aiapp-server/tree/main/apps/document-summary) | summaries of long documents |
| [ticket-triage](https://github.com/Sandaal/aiapp-server/tree/main/apps/ticket-triage) | sorts tickets into your labels |
| [meeting-notes](https://github.com/Sandaal/aiapp-server/tree/main/apps/meeting-notes) | recordings or transcripts to action items |
| [content-studio](https://github.com/Sandaal/aiapp-server/tree/main/apps/content-studio) | brief to draft, with human review |
| [sales-insights](https://github.com/Sandaal/aiapp-server/tree/main/apps/sales-insights) | questions about data, answered with SQL |
| [code-assistant](https://github.com/Sandaal/aiapp-server/tree/main/apps/code-assistant) | questions about a codebase |
| [ops-agent](https://github.com/Sandaal/aiapp-server/tree/main/apps/ops-agent) | an agent with tools and approvals |

## How to add…

| Example | Shows |
|---|---|
| [custom-routes](https://github.com/Sandaal/aiapp-server/tree/main/apps/examples/custom-routes) | routes in Python: JSON, a model call, streaming with memory |
| [tools-agent](https://github.com/Sandaal/aiapp-server/tree/main/apps/examples/tools-agent) | the model calling your functions |
| [approval-workflow](https://github.com/Sandaal/aiapp-server/tree/main/apps/examples/approval-workflow) | a durable workflow with a manager's approval |
| [guardrail-plugin](https://github.com/Sandaal/aiapp-server/tree/main/apps/examples/guardrail-plugin) | your own safety rule |
| [scheduled-report](https://github.com/Sandaal/aiapp-server/tree/main/apps/examples/scheduled-report) | a nightly job, events and a subscriber |
| [connectors](https://github.com/Sandaal/aiapp-server/tree/main/apps/examples/connectors) | SharePoint, Git, websites, databases, S3, Azure Blob |
| [own-web-page](https://github.com/Sandaal/aiapp-server/tree/main/apps/examples/own-web-page) | your own page with the chat component |
| [customized-blueprint](https://github.com/Sandaal/aiapp-server/tree/main/apps/examples/customized-blueprint) | a blueprint's code copied into the app and changed |

Every app's README explains how to run it, what to change, and how to redeploy. All of them pass their tests and deploy on the current release.
