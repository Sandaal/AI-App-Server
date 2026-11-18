# Phase 1 Design: v1 Product (Single Node, Standard Hardware)

*Status: draft for review · 2026-11-18 · Builds on [Phase 0](phase0.md)*

## 1. Goal and exit criteria
Turn the Phase 0 prototype into a product a team can run in production on one standard server.

**Exit criteria**
1. All 10 blueprints deploy with `aiapp new` → `aiapp deploy` in minutes on a 16 vCPU / 64 GB VM with no GPU and no external stores.
2. Each blueprint can be customized through `ai-app.yaml` or Python handlers without forking the server.
3. A node restart loses no acknowledged data; `aiapp backup` / `aiapp restore` round-trips a full server.
4. One misbehaving app can't exhaust memory, disk, model budget or workers of other apps.
5. Linux, macOS and Windows builds pass CI.

**Not in Phase 1:** clustering, local model hosting, Node workers, Redis/Kafka wire protocols, hardware-specific tiers (all Phase 2+).

## 2. What each blueprint needs (drives sequencing)
| Capability | Chat | Support | Summ. | Extract | Insights | Content | Code | Workflow | Classify | Meeting |
|---|---|---|---|---|---|---|---|---|---|---|
| Model gateway + streaming | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● |
| Vectors + hybrid search | ● | ● | | | | | ● | | | |
| Conversation memory | ● | ● | | | ● | | ● | ● | | |
| File store + ingestion | ● | ● | ● | ● | | | ● | | | ● |
| Job queue | | | ● | ● | | | | ● | ● | ● |
| Event topics | | ● | | | | | | ● | ● | |
| Structured output | | | | ● | ● | | | ● | ● | ● |
| Tool calling / MCP client | | ● | | | ● | | ● | ● | | |
| Agent workflows + approvals | | ● | | | | ● | | ● | | |
| Connectors | ● | ● | | | ● | | ● | ● | ● | |
| Speech-to-text | | | | | | | | | | ● |

Order follows coverage: gateway → storage → jobs → structured output → tools → workflows → topics → speech.

## 3. Request pipeline
Pipeline stages are ordered, configurable per app, and run in the Go core unless marked *(system worker)*.

| Stage | Phase 1 behavior |
|---|---|
| **Authentication** | API keys (hashed, scoped to app + routes); OIDC/JWT validation with Entra ID as the first-class issuer; anonymous only if a route allows it |
| **Authorization** | RBAC: roles per app (`invoke`, `admin`, `read-logs`) and per route; claims passed to handlers as `Principal` |
| **Rate limiting** | Token bucket per key and per app (requests/s); daily/monthly **token and cost budgets** per app and per key |
| **Input guardrails** | PII detection and redaction *(system worker, Presidio)*; prompt-injection heuristics plus optional classifier model; blocked-topic lists; max input size |
| **Handler** | App code in its worker pool |
| **Output guardrails** | PII re-check; JSON-schema validation for structured routes (retry once with the error); citation-required check for RAG routes; optional content-safety provider (e.g. Azure AI Content Safety) |
| **Audit** | Request, prompt, response, model, tokens, cost, latency, guardrail decisions; redaction applied before write |

Guardrails are plugins with one interface (`Check(ctx, Payload) → Allow | Redact(payload) | Block(reason)`), so organizations can add their own in Python.

## 4. Model gateway v2
- **Providers:** Azure OpenAI, OpenAI, Anthropic, Google Gemini, AWS Bedrock, and any OpenAI-compatible endpoint.
- **Logical models:** apps reference names (`chat`, `fast`, `embedding`); the server maps names to provider deployments.
- **Routing:** weighted load balancing across deployments; fallback chains; circuit breaker per deployment (open on error rate or 429s).
- **Normalization:** one request/response shape for chat, tool calls, structured output (JSON schema), vision input and embeddings, regardless of provider.
- **Caching:** exact-match cache (default on for temperature 0); semantic cache (embedding similarity above a per-app threshold, opt-in).
- **Accounting:** per-call tokens and cost from a price table the operator can update; budgets enforced before the call.
- **Secrets:** provider keys stored encrypted (section 5.5); Azure managed identity supported when running on Azure.

## 5. Storage v1
All engines sit behind the Phase 0 interfaces. One data directory per server, one namespace per app.

### 5.1 Key-value and data structures (Redis-like)
- Built on Pebble. Keys encoded as `app/namespace/type/key[/member]`, so each data type maps to ordered key ranges.
- Types: strings, hashes, lists, sets, sorted sets; TTL on any key (expiry index + background sweeper); atomic counters; compare-and-set; leases/locks with fencing tokens.
- In-memory hot cache (size-capped LRU) in front of Pebble for reads.
- In-memory pub/sub channels (fire-and-forget) for UI updates.

### 5.2 Vectors
- HNSW index per collection, memory-mapped from disk; incremental inserts; tombstone deletes with periodic compaction.
- Metadata filtering (pre-filter for selective filters, post-filter otherwise).
- **Hybrid search:** Bleve full-text index alongside; results merged with reciprocal rank fusion; optional reranker model call.
- Quantization (int8) option for large collections to cut RAM.

### 5.3 Files, ingestion and metadata
- Content-addressed blob store (SHA-256), deduplicated, with per-app reference counting.
- Ingestion pipeline as durable jobs: load → parse *(system worker)* → chunk → embed (batched) → index. Re-ingest only changed files (hash comparison).
- Loaders: PDF, DOCX, PPTX, XLSX, HTML, Markdown, TXT, CSV, email (EML/MSG), images (OCR via model).
- SQLite (pure Go) for structured metadata: apps, versions, sources, documents, jobs, keys, audit index.

### 5.4 Durability, backup and restore
- Pebble WAL with fsync on acknowledged writes (configurable to batched for throughput).
- Consistent snapshots via Pebble checkpoints + SQLite online backup + blob manifest.
- `aiapp backup --to <dir|s3|azure-blob>` and `aiapp restore`; scheduled backups through the cron scheduler.
- Startup integrity check; corrupted-segment recovery for logs and topics.

### 5.5 Security of data at rest
- AES-256-GCM envelope encryption: per-app data keys, wrapped by a master key from a file, environment variable, or (Phase 1.x) Azure Key Vault / HashiCorp Vault.
- Per-app isolation: separate key ranges, separate data keys, no cross-app queries.

### 5.6 Quotas
Per app: storage bytes, vector count, hot-cache memory, worker count, max concurrent requests, token/cost budgets. Writes over quota fail with a clear error; reads continue.

## 6. Data plane: events, jobs and scheduling (Kafka-like)
| Feature | Design |
|---|---|
| **Topics** | Append-only segment files per topic (single partition in Phase 1); records carry offset, timestamp, key, headers |
| **Consumers** | Named consumers with stored offsets; at-least-once delivery; replay from offset or timestamp |
| **Retention** | By age and by size per topic |
| **Job queue** | Built on topics + KV: visibility timeout, retries with exponential backoff, delayed jobs, max attempts, dead-letter queue |
| **Scheduler** | Cron expressions per app; runs a handler or enqueues a job; missed-run policy (skip / run once) |
| **SDK** | `app.events.publish/subscribe`, `app.jobs.enqueue`, `@app.job`, `@app.cron("0 * * * *")` |

Consumer groups and multi-partition topics are Phase 1.x.

## 7. Tools, MCP and agent workflows
- **Tool calling:** Python functions decorated with `@app.tool` are exposed to models with generated JSON schemas.
- **MCP client:** apps declare MCP servers in the manifest (stdio or HTTP); the server manages connections, auth and per-app allow-lists.
- **Agent workflows:** a small step engine. Each step's input/output is checkpointed to KV, so a workflow survives worker restarts and can resume. Supports retries, timeouts, parallel branches and compensation steps.
- **Human approval:** a step can pause the workflow, create an approval task, and resume when approved through the admin console, API or a webhook (e.g. Teams message action).

The strategy listed the MCP/tool gateway under Phase 1.x. This design moves the **MCP client and tool calling into Phase 1**, because blueprints 2, 5, 7 and 8 need them. The central **MCP gateway** (exposing tools to outside agents) stays in Phase 1.x.

## 8. App lifecycle
- **Versions:** every deploy creates an immutable version (manifest + code + dependency lock hash).
- **Zero-downtime deploy:** new workers start and pass health, then traffic switches; old workers drain.
- **Rollback:** `aiapp rollback hr-bot [--to 0.3.1]`.
- **Environments:** `dev`, `test`, `prod` on one server or separate servers, with per-environment config overlays.
- **Dependencies:** per-app virtualenv via `uv`, cached by lockfile hash; offline wheelhouse support for air-gapped installs.
- **Secrets:** `aiapp secret set`, injected into workers as environment variables, never written to logs.

## 9. SDKs
**Python SDK (`aiapp`)**: routes, streaming, `models`, `memory`, `kv`, `vectors`, `files`, `events`, `jobs`, `tools`, `workflows`, typed request/response models, and a local test harness (`aiapp test`) that runs handlers against a mock host.

**JavaScript/TypeScript SDK (`@aiapp/client`, `@aiapp/ui`)**:
- Client: typed calls, SSE streaming, auth (API key or MSAL token), retries.
- UI: framework-agnostic web components (`<aiapp-chat>`, `<aiapp-upload>`, `<aiapp-approvals>`) with thin React wrappers.
- Apps may ship their own front end in `ui/`; the server hosts it as static files with SPA routing.

## 10. Developer experience
- **CLI:** `new`, `dev` (hot reload), `deploy`, `rollback`, `logs`, `trace`, `source`, `secret`, `apps`, `backup`, `restore`.
- **Blueprint gallery:** 10 blueprints, each with a sample dataset, tests and a README.
- **VS Code extension:** create from blueprint, run locally, view logs and traces, deploy.
- **GitHub Copilot instructions** shipped in each blueprint (`.github/copilot-instructions.md`).
- **Packaging:** single binaries (Linux/macOS/Windows, x86 and ARM), Docker image, Helm chart, `azd` templates for App Service, Container Apps and AKS.

## 11. Connectors (starter set)
Local filesystem, SharePoint/OneDrive (Microsoft Graph), Azure Blob, Amazon S3, Git (GitHub/Azure DevOps/any git URL), PostgreSQL, SQL Server, generic HTTP/OpenAPI. Connectors run as source plugins with incremental sync (delta tokens or modified-time), on a schedule.

## 12. Observability and admin
- **Telemetry:** OpenTelemetry traces (request → pipeline → handler → model/tool/storage spans) and metrics; Prometheus `/metrics`; structured JSON logs.
- **AI metrics:** tokens, cost, latency, cache hit rate, guardrail blocks, error rate per app, route and model.
- **Admin console:** a small built-in web UI for apps, versions, logs, traces, usage and budgets, approvals, sources and ingestion status. Built with the JS SDK.

## 13. Milestones
| # | Milestone | Done when |
|---|---|---|
| M1.1 | Pipeline | API keys + Entra ID auth, RBAC, rate limits and budgets enforced; audit records written |
| M1.2 | Gateway v2 | 5 providers, fallback, circuit breaker, exact + semantic cache, structured output |
| M1.3 | Storage v1 | Data structures with TTL, HNSW + hybrid search, encryption, quotas, backup/restore |
| M1.4 | Jobs, topics, cron | Ingestion runs as durable jobs; blueprints 3, 4, 9, 10 work |
| M1.5 | Tools + workflows | Tool calling, MCP client, checkpointed workflows, approvals; blueprints 2, 5, 7, 8 work |
| M1.6 | Lifecycle + DX | Versions, rollback, `aiapp dev`, VS Code extension, Docker/Helm/azd |
| M1.7 | Guardrails + observability | PII, injection, schema checks; OTel traces; admin console |
| M1.8 | Release hardening | Windows build, load tests, docs; all 10 blueprints pass the exit criteria |

## 14. Phase 1.x: hardening
- Consumer groups and multi-partition topics; dead-letter tooling in the console.
- MCP gateway: publish app tools as MCP servers for outside agents, with auth and audit.
- Evaluation hooks: golden datasets per app, offline eval runs, quality metrics on dashboards, regression gates in CI.
- Key Vault / Vault integration; SSO for the admin console; audit export (SIEM).
- Performance work from production feedback.

## 15. Risks
| Risk | Mitigation |
|---|---|
| Scope: storage + data plane + gateway + agents is large | Strict milestone order by blueprint coverage; cut features, not quality |
| HNSW and Pebble tuning on memory-limited VMs | Quantization, mmap, quotas; publish sizing guidance from load tests |
| Python dependency installs slow down "minutes" deploys | Lockfile-hash venv cache; prebuilt blueprint environments |
| Guardrail false positives frustrate developers | Per-app tuning, dry-run mode that logs without blocking |
| Windows differences (sockets, process control) | Windows CI from M1.1, not at the end |

## 16. Open questions
1. Admin console scope in v1: read-only dashboards, or full management?
2. Default embedding model when an app doesn't specify one.
3. Telemetry default: off by default, or opt-out anonymous usage metrics?
