# Phase 0 Design: Core, Worker Protocol and First Blueprint

*Status: draft for review · 2026-11-18*

## 1. Goal and exit criteria
Prove the core architecture end to end with the smallest useful slice.

**Exit criteria:** on a standard VM (4 vCPU, 16 GB RAM, no GPU), a developer runs:

```bash
aiws new knowledge-chat hr-bot
cd hr-bot && aiws source add ./policies/
aiws deploy
```

…and within 5 minutes has a working chat UI and API that answer questions from their documents, with citations and streaming, using a hosted model. No external database, cache or queue.

**Out of scope for Phase 0:** guardrails beyond basic PII redaction, Kafka-like topics, multi-tenancy quotas, clustering, hardware abstraction, Node workers, the other 9 blueprints.

## 2. Process model
One Go binary, `aiws`, with subcommands:

| Command | Role |
|---|---|
| `aiws serve` | Runs the server (core process) |
| `aiws new / source / deploy / logs / apps` | Developer CLI; talks to a running server through its admin API |

Shipping the CLI and server as one binary keeps installation to a single download.

```
                 ┌──────────────────────── aiws serve (Go) ────────────────────────┐
 HTTP/SSE  ───►  │ Listener → Router → Pipeline (auth, rate limit, PII) → App call │
 (apps, UI,      │                                         │                       │
  admin API)     │   Model gateway   Storage (KV, vectors, files)   Supervisor     │
                 └──────────▲──────────────────▲─────────────────────────┬─────────┘
                            │  host calls (gRPC)                          │ spawns, health-checks
                            │                                             ▼
                 ┌──────────┴──────────── Python worker (per app) ──────────────────┐
                 │  aiws SDK runtime  →  developer handler code (handlers.py)        │
                 └───────────────────────────────────────────────────────────────────┘
```

- The **core** owns connections, auth, routing, streaming, models, storage and logging.
- Each **app** runs in its own pool of Python worker processes (default 2). A crash or hang in one app can't affect the core or other apps.
- Workers never talk to models or storage directly. They call back into the core ("host calls"), so quotas, logging, caching and key management live in one place.

## 3. Request lifecycle
1. Client sends `POST /apps/hr-bot/chat` (or the OpenAI-compatible `POST /apps/hr-bot/v1/chat/completions`).
2. Router resolves the app and version; pipeline runs auth (API key in Phase 0, Entra ID/OIDC in Phase 1), rate limit and request logging.
3. Core sends `Invoke` to an idle worker of that app over the worker protocol.
4. The handler runs. When it needs a model, vectors or KV, it makes host calls back to the core.
5. Model output streams worker → core → client as SSE chunks.
6. Core writes the audit record (prompt, response, tokens, latency, cost) to the log store.

## 4. Worker protocol
- **Transport:** gRPC over a Unix domain socket per worker (Linux/macOS); localhost TCP with a per-worker token on Windows.
- **Direction:** two services. `Worker` is served by the Python process (core calls it). `Host` is served by the core (workers call it).
- **Streaming:** `Invoke` is server-streaming, so handlers can `yield` tokens.
- **Language-neutral:** nothing Python-specific in the contract, so a Node runtime can implement the same `Worker` service in Phase 2.

Contract: [`core/proto/aiws/v1/worker.proto`](../../core/proto/aiws/v1/worker.proto).

### Worker lifecycle
| Stage | Behavior |
|---|---|
| Spawn | Supervisor starts `python -m aiws.runtime --socket … --app …` in the app's virtualenv |
| Ready | Worker calls `Host.Register`; core marks it idle |
| Health | Core calls `Worker.Health` every 5 s; 3 failures → kill and respawn |
| Timeout | Per-invoke deadline (default 120 s) → cancel; repeated timeouts → respawn |
| Deploy | New version's workers start and pass health before old ones drain (zero-downtime swap) |

## 5. App package and manifest
```
hr-bot/
  ai-app.yaml        # manifest
  handlers.py        # developer code (optional for blueprints)
  requirements.txt   # extra Python deps (optional)
  ui/                # optional static front end (JS)
```

```yaml
# ai-app.yaml
app: hr-bot
version: 0.1.0
blueprint: knowledge-chat        # optional; supplies default handlers
runtime: python3.12

models:
  chat:      { provider: azure-openai, deployment: gpt-chat, fallback: openai/gpt-mini }
  embedding: { provider: azure-openai, deployment: text-embedding }

sources:
  - path: ./policies/
    chunking: { size: 800, overlap: 100 }

routes:
  - path: /chat
    handler: handlers:chat        # or blueprint default
    stream: true

guardrails: [pii-redaction]
ui: chat-widget                   # built-in JS widget, or ./ui
workers: 2
```

Secrets (API keys) are never in the manifest. They're set with `aiws secret set AZURE_OPENAI_KEY` and stored encrypted by the core.

## 6. Python SDK (developer view)
```python
from aiws import app, Request

@app.route("/chat", stream=True)
async def chat(req: Request):
    hits = await app.vectors.search("sources", req.text, k=5)
    history = await app.memory.history(req.session_id, last=10)
    async for token in app.models.chat.stream(
        system="Answer only from the context. Cite sources.",
        context=hits, history=history, user=req.text,
    ):
        yield token
    await app.memory.append(req.session_id, req.text, app.last_response)
```

Every `app.*` call is a host call to the core. The same code runs unchanged whether storage is built-in or external.

## 7. Model gateway (Phase 0)
- Providers: Azure OpenAI, OpenAI, Anthropic, and any OpenAI-compatible endpoint (covers Ollama/vLLM for local models).
- Features: streaming, one fallback model, retry with backoff, token and cost accounting per call.
- Deferred to Phase 1: load balancing across deployments, semantic cache, budgets.

## 8. Storage (Phase 0 minimum)
| Need | Phase 0 implementation | Phase 1 upgrade |
|---|---|---|
| KV, sessions, conversation memory | Pebble (embedded LSM) | Data structures, TTL, quotas |
| Vectors | Flat (exact) index in memory, persisted to Pebble; fine up to ~100K chunks | HNSW, memory-mapped, hybrid search |
| Files / sources | Local content-addressed store | Same, plus encryption at rest |
| Audit / request log | Append-only JSON-lines segments with rotation | Segment format shared with event topics |
| Ingestion jobs | In-process goroutine queue | Durable job queue |

Everything sits behind Go interfaces (`KV`, `VectorIndex`, `BlobStore`, `LogStore`) from day one, so the Phase 1 engines and external adapters slot in without touching the pipeline.

Data directory: `./data/` by default, `--data-dir` to override.

## 9. Go code layout
```
core/
  cmd/aiws/            # main: serve + CLI subcommands
  internal/server/     # listener, router, SSE
  internal/pipeline/   # auth, rate limit, PII, logging stages
  internal/apps/       # manifest parsing, registry, deploy/versioning
  internal/workers/    # supervisor, pool, gRPC client
  internal/host/       # Host service implementation
  internal/models/     # provider adapters, fallback, accounting
  internal/storage/    # interfaces + pebble, flatvec, blob, logstore
  internal/ingest/     # loaders (pdf, docx, md, txt), chunking, embedding
  proto/aiws/v1/       # worker.proto
sdk/python/aiws/       # runtime + developer SDK
blueprints/knowledge-chat/
sdk/js/chat-widget/    # minimal streaming chat UI
```

Go module: `github.com/Sandaal/AI-App-Server`.

## 10. Milestones
| # | Milestone | Done when |
|---|---|---|
| M0.1 | Skeleton | `aiws serve` starts, serves `/health`, loads one manifest. **Done 2026-11-18** except YAML manifest loading (M0.1b), which needs the first external Go dependency |
| M0.2 | Worker protocol | Echo handler in Python streams through core to an SSE client; crash → respawn works |
| M0.3 | Model gateway | Handler streams a real Azure OpenAI / OpenAI response with token logging |
| M0.4 | Storage + ingestion | `aiws source add` chunks and embeds PDFs/DOCX/MD into the built-in vector index |
| M0.5 | Knowledge-chat blueprint | Chat widget answers with citations; full flow under 5 minutes on a clean VM |

## 11. Decisions (2026-11-18)
1. **Python environments:** one virtualenv per app, cached by `requirements.txt` hash, created with `uv`.
2. **Document parsing:** done in a built-in Python "system worker" in Phase 0.
3. **Platforms:** Linux and macOS in Phase 0; Windows support in Phase 1.
4. **Admin API auth:** local Unix socket only in Phase 0; token auth in Phase 1.
