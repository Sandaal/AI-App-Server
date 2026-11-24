# FAQ

**Does my data leave my server?**
Only what you send to a model provider (the question, the relevant passages, the history). Use `pii-redaction` and `presidio` to remove personal data first, or a local model (Ollama, vLLM) to keep everything inside.

**Do I need a database, a vector store or Redis?**
No. Storage, vector search, conversation memory, jobs and events are built in, on the server's disk, encrypted.

**Which model should I use?**
Start with a small, cheap one (`gpt-4o-mini`, `claude-haiku`, `llama3.2` locally) and measure with [`aiapp eval`](../build/testing.md#evaluations-aiapp-eval). Change models in `ai-app.yaml` without touching code.

**Can I write apps in JavaScript instead of Python?**
App handlers are Python today. Many apps need no code at all: a blueprint plus settings. Your front ends can be anything; see [Call apps from your code](../build/clients.md).

**How many apps can one server run?**
As many as its memory allows: each app's workers are separate Python processes, so memory grows with the number of apps and `workers:`. Watch `aiapp quota APP` and the worker metrics, and see [Quotas and limits](../operate/quotas.md).

**Can I run several servers for high availability?**
Each server keeps its own data, so run one server per set of apps (a StatefulSet of one on Kubernetes) and back it up. Restarts are quick and apps come back by themselves.

**Is it free?**
The server is free to download and use. You pay your model provider for what you use; `aiapp logs` and the budgets in `aiapp quota` keep track.

**Where do I report a bug or ask a question?**
[GitHub issues](https://github.com/Sandaal/ai-app-server/issues). For security issues, see [Security](../operate/security.md#reporting-a-vulnerability).
