# Customize a blueprint's code

Most changes to a blueprint app are settings in `ai-app.yaml`, plus your own tools, handlers and guardrails. When you need to change how a blueprint itself works (how it searches, what it sends the model, the shape of its answer), copy its code into your app.

## Where the code is

Each blueprint is a Python file in the SDK, published in the [`sdk/python/aiapp/blueprints/`](https://github.com/Sandaal/aiapp-server/tree/main/sdk/python/aiapp/blueprints) folder:

| Blueprint | File | Routes → functions |
|---|---|---|
| `knowledge-chat` | `knowledge_chat.py` | `/chat` → `chat` |
| `customer-support` | `customer_support.py` | `/chat` → `chat`; job `support_action` → `action` |
| `document-extraction` | `document_extraction.py` | `/extract` → `extract`, `/result` → `result`; job `extract` → `run` |
| `summarization` | `summarization.py` | `/summarize` → `summarize`, `/result` → `result`; job `summarize` → `run` |
| `classification` | `classification.py` | `/classify` → `classify`; topic events → `on_event` |
| `meeting-notes` | `meeting_notes.py` | `/notes` → `notes`, `/result` → `result`; job `notes` → `run` |
| `content` | `content_studio.py` | `/drafts` → `drafts`; job `draft` → `run` |
| `insights` | `insights.py` | `/ask` → `ask` |
| `code-assistant` | `code_assistant.py` | `/chat` → `chat` |
| `workflow-agent` | `workflow_agent.py` | `/run` → `run`; job `agent` → `agent` |

The app manifest shows the exact handler names: a blueprint route's handler is `aiapp.blueprints.FILE:FUNCTION`.

## Copy and change it

Example: change how `knowledge-chat` answers.

1. **Copy** `knowledge_chat.py` into your app folder as `my_chat.py`.
2. **Point the route at your copy** in `ai-app.yaml`, keeping `blueprint:` for its settings, page and model checks:

    ```yaml
    blueprint: knowledge-chat
    routes:
      - { path: /chat, handler: "my_chat:chat", stream: true }
    ```

3. **Change** `my_chat.py`: the search (`k`, `mode="hybrid"`, filters), the system prompt, the citations, extra steps (`app.span()` for each). It uses the same SDK as your own handlers (`from aiapp import app`).
4. **Test and deploy:** `aiapp test`, then `aiapp deploy`. To go back, point the route at `aiapp.blueprints.knowledge_chat:chat` again (or `aiapp rollback`).

!!! note "Listing routes replaces the blueprint's defaults"
    When an app lists `routes:`, the blueprint's routes are not added for it. List every route the app needs; a route with only a `path` (such as `- { path: /result }`) keeps the blueprint's handler for it.

!!! tip "Keep up with releases"
    Your copy no longer changes when you upgrade the server. Compare it with the new release's file now and then, or keep the built-in handler and add behaviour around it with your own routes, tools and guardrails instead.

## The SDK source

The Python SDK (`sdk/python`) and the JavaScript client and web components (`sdk/js`) are published under the Apache 2.0 license. Read them to see exactly what each call does; they are the same code your app runs.
