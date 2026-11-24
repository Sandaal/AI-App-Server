---
hide:
  - navigation
---

# AI App Server

**Run AI applications from one small configuration file.** Chat over your documents, document extraction, agents with tools, workflows with human approval, classification, meeting notes and more. There is no web framework, database or vector store to set up: the server includes all of them, and keeps everything on its own disk, encrypted.

```bash
aiapp new knowledge-chat hr-bot --provider openai
cd hr-bot && aiapp source add ./policies/ && aiapp deploy
# open http://127.0.0.1:8080/apps/hr-bot/  →  a chat page that answers from your documents, with citations
```

<div class="grid cards" markdown>

-   **New here?**

    ---

    What the server is, and a working app in ten minutes.

    [Get started](get-started/index.md)

-   **Install and run**

    ---

    Windows, macOS, Linux, Docker, Kubernetes and Azure. Connect OpenAI, Azure OpenAI, Anthropic, Gemini, Bedrock or a local Ollama.

    [Install](install/index.md)

-   **Build apps**

    ---

    Ten ready-made blueprints, Python handlers, agents and tools, workflows, guardrails, web pages, tests.

    [Build apps](build/index.md)

-   **Operate**

    ---

    Security, sign-in, secrets, the console, audit and SIEM export, monitoring, quotas, backups.

    [Operate](operate/index.md)

</div>

## What you get

| | |
|---|---|
| **Ready-made app types** | knowledge chat, customer support, document extraction, summarization, classification, meeting notes, content review, data insights (SQL), code assistant, workflow agent |
| **Your documents** | PDF, Word, PowerPoint, Excel, HTML, Markdown, CSV, email; plus Git, websites, S3, Azure Blob, SQL databases, SharePoint and OneDrive |
| **Any model** | OpenAI, Azure OpenAI, Anthropic, Google Gemini, AWS Bedrock, Ollama, vLLM and other OpenAI-compatible servers, with fallbacks, budgets and cost tracking |
| **Safety** | guardrails for personal data, prompt injection, blocked topics, citations, Microsoft Presidio and Azure AI Content Safety |
| **Enterprise sign-in** | API keys with roles, Entra ID and any OIDC provider, multi-tenant isolation, audit log export to your SIEM |
| **Operations** | zero-downtime deploys and rollback, quotas per app, traces, Prometheus and OpenTelemetry, encrypted backups |

[Download the latest release](download.md){ .md-button .md-button--primary } [Read the quickstart](get-started/quickstart.md){ .md-button }
