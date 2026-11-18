# AI App Server: Product Strategy

*Status: working draft. Last updated 2026-11-18.*

**License:** open source under Apache License 2.0 (see ADR 0002). Possible future business model: open core.

## 1. Vision
**An application server for AI.** Developers build AI apps in Python and JavaScript and deploy them the way they deploy web apps. The server provides every runtime service those apps need: model access, memory, cache, events, vectors, security, guardrails, observability and deployment, in one binary that runs on any hardware.

**Initial goal:** deploy the top 10 AI use cases in minutes.

**Design analogy (internal only):** a Tomcat/IIS-style app server, Tomcat-simple rather than WebSphere-heavy. The project started from an Apache web server analogy; "app server" replaced it on 2026-11-18.

## 2. Core principles
1. **Developers write only business logic.** The server provides everything common to every AI project.
2. **Built-in first.** Memory, disk storage, cache, events and vectors live inside the server. External systems are optional adapters.
3. **Runs anywhere, uses the best hardware available.** Runs fully on standard servers; uses next-generation hardware automatically when present.
4. **Independent and neutral.** Own runtime, SDK and blueprints. No dependency on any vendor's agent framework. Neutral across model providers and hardware vendors.
5. **Lightweight.** One binary, starts in seconds, YAML config, runs on a laptop.

## 3. Positioning
- **Target community:** Microsoft-ecosystem developers working in Python and JavaScript/TypeScript (VS Code, GitHub, Azure).
- **Microsoft integrations, not dependencies:** VS Code extension, GitHub/Copilot support, azd/Azure deployment targets, Entra ID auth, Azure OpenAI as one provider among many.
- **Not built on** Microsoft Agent Framework, Semantic Kernel or .NET. Keeping Python + JavaScript is deliberate, so the product doesn't become "another Microsoft product."
- **Complements Microsoft Foundry:** Foundry Hosted Agents is Azure-managed. The AI App Server runs anywhere (on-prem, air-gapped, edge, any cloud) with a built-in data plane and predictable cost.
- **Framework- and provider-neutral:** apps may use any Python/JS library (LangGraph, plain code, etc.) and any model provider (Azure OpenAI, Anthropic, OpenAI, Gemini, local models).
- **Value story for customers:** consolidation. One runtime replaces web server + Redis + Kafka + vector DB + AI gateway + glue code.

## 4. App server services and their AI equivalents
| Classic app server | AI App Server |
|---|---|
| Deployable unit (WAR/EAR, IIS app) | AI app package + `ai-app.yaml` manifest |
| Container lifecycle | Versioned deploys, hot reload, rollback, per-app isolation |
| Servlet/handler container | Python app workers; JS front end (Node workers in v2) |
| JDBC connection pools | Model connection pools: routing, failover, token budgets |
| JNDI | Service registry: models, tools/MCP, data sources by name |
| JMS | Built-in Kafka-like topics, job queues, pub/sub |
| Sessions + distributed cache | Conversation memory, Redis-like cache, semantic cache |
| Transactions (JTA) | Agent workflows with checkpoints, retries, compensation |
| Security realms | Entra ID / OIDC, RBAC per app, guardrails, PII redaction |
| Schedulers | Cron jobs, long-running agent tasks |
| Admin console + monitoring | Admin console, traces, token/cost metrics, evals |
| Clustering | Phase 2 clustering on the shared storage foundation |
| *(none)* | Vectors/RAG, model inference, hardware-aware tiers |

## 5. Technology decisions
| Area | Decision |
|---|---|
| Server core | **Go**: single cross-platform binary, not exposed to app developers |
| Server-side apps | **Python** (v1), isolated worker processes (PHP-FPM / mod_wsgi daemon pattern) |
| Front end | **JavaScript/TypeScript** client SDK + UI components |
| Server-side JS | Node.js worker runtime in **v2** |
| Core ↔ app protocol | gRPC / Unix socket, language-neutral by design |
| Other languages (incl. C#) | Consume apps through standard HTTP APIs (OpenAI-compatible where sensible) |
| Deployment | Bare metal, VM, containers/Kubernetes, or behind Apache/Nginx/IIS as reverse proxy; Windows and Linux |

## 6. Built-in storage and data plane
**Tiers:** memory (hot) → local disk (persistent) → external adapters (optional).

| Data type | Built-in engine |
|---|---|
| Key-value, sessions, state | Embedded LSM store (e.g. Pebble/Badger) |
| Cache (exact + semantic) | In-memory, backed by KV |
| Vectors (RAG) | In-process HNSW index, memory-mapped from disk |
| Full-text search | Embedded index (e.g. Bleve) |
| Structured metadata | Embedded SQLite (pure Go) |
| Files and documents | Local content-addressed object store |
| Logs, audit, event topics | Append-only segment files |

**Redis-like:** strings, hashes, lists, sets, sorted sets, TTL, atomic ops, locks, pub/sub.
**Kafka-like:** durable topics, consumer groups, offsets, replay, retention; job queues with retries, delays, DLQ, scheduling.

- One storage foundation powers all data services; all share quotas, encryption, backup, isolation and observability.
- Scoped to AI-app needs, not full Redis/Kafka clones.
- Wire compatibility: Redis protocol (RESP) in v2; Kafka via connectors, not protocol.
- External stores are selected per app by config; the SDK API is the same regardless of backend.
- v1 must include: per-app quotas and isolation, WAL + snapshots, backup/restore, encryption at rest.

## 7. Hardware strategy
- **Baseline:** runs fully on standard web-server hardware (x86/ARM, DRAM, SSD). Only large local models need a GPU; without one, apps route to hosted models. Future hardware improves speed and scale, never functionality.
- **Hardware Abstraction Layer (HAL):** detects capabilities at startup (coherent CPU–GPU memory, CXL pools, HBM, NVMe, DPUs, LPUs, confidential computing) and maps storage tiers, offload and routing onto them. Same app package everywhere.
- **Reference target:** NVIDIA Vera Rubin (2026) → Rubin Ultra (2027) → Feynman (2028).
- **Secondary target:** AMD Instinct rack-scale (MI455X / MI500).
- **Dev/edge target:** unified-memory workstations (DGX Spark class, AMD Ryzen AI Max).
- **Layer mapping:** CPU = server core + app workers; coherent memory = hot tier; GPU/LPU = local inference; DPU = context memory, event log, storage, encryption; confidential computing = isolation/audit.
- Design against capabilities, not product names. Vendor-neutral.
- **Local inference:** integrate engines (vLLM, NVIDIA Dynamo, LMCache) rather than build one. Phase 2 (to be confirmed).

### Rough sizing on standard hardware (starting points, not benchmarks)
| Tier | Machine | Good for |
|---|---|---|
| Small | 4–8 vCPU, 16–32 GB RAM, SSD | Dev/test, a few apps, hosted models |
| Medium | 16–32 vCPU, 64–128 GB RAM, NVMe | Production apps, mid-size RAG, event pipelines |
| Large | + mid-range GPU (L4/L40S class) | Local embeddings, small-to-mid local models |

## 8. Top 10 blueprints (initial goal)
| # | Blueprint | Key server capabilities |
|---|---|---|
| 1 | Knowledge chat (Q&A over documents, with citations) | Ingestion, vectors, hybrid search, memory, streaming |
| 2 | Customer support assistant | Knowledge chat + tools/MCP + handoff events |
| 3 | Document summarizer | File store, jobs, models |
| 4 | Document extraction (forms, invoices, contracts → JSON) | File store, jobs, structured output |
| 5 | Data insights (natural-language questions over data) | DB connectors, SQL tool, guardrails |
| 6 | Content generator | Prompt templates, cache, review workflow |
| 7 | Code assistant | Git connector, vectors, models |
| 8 | Workflow agent | Agent runtime, tools/MCP, events, approvals |
| 9 | Classifier / router | Event topics, small/local models, KV |
| 10 | Meeting and voice notes | File store, speech model, jobs |

Developer flow: `aiapp new <blueprint> <name>` → `aiapp source add <data>` → `aiapp deploy`. Customize via `ai-app.yaml` or Python handlers.

**What "minutes" doesn't cover:** production readiness (SSO, quality testing, approvals), large-volume data ingestion, and custom enterprise connectors take longer.

## 9. Phases
**Phase 0: Foundation and prototype**
- Go core, request pipeline, config, Python worker protocol; one app against a hosted model.
- Exit: Knowledge chat blueprint deploys in under 5 minutes on a standard VM.

**Phase 1: v1 product (single node, standard hardware)**
- Model routing/failover, auth, rate limiting, guardrails, streaming.
- Built-in storage: KV/data structures, cache, vectors, search, files, audit logs; topics and job queues.
- Quotas, isolation, backup/restore, encryption.
- Python SDK + JS front-end SDK; versioned deploys, hot reload, rollback.
- Blueprint gallery, `aiapp` CLI, starter connectors, VS Code extension, Entra ID, azd templates.
- Tool calling and MCP client (needed by blueprints 2, 5, 7, 8); Windows support.
- Exit: all 10 blueprints deploy in minutes on standard hardware with no external stores.

**Phase 1.x: Hardening**
- Consumer groups, multi-partition topics, DLQ tooling; MCP gateway (publishing app tools to outside agents); evaluation hooks; Key Vault integration.

**Phase 2: Scale and first hardware leap (Vera Rubin)**
- Clustering and replication; HAL v1; local model hosting via vLLM/Dynamo; Context Memory service.
- Node.js worker runtime; RESP compatibility; Kafka connectors.
- Exit: the same app package runs unchanged on a VM and on Vera Rubin, faster on the latter.

**Phase 3: Future-hardware native (Rubin Ultra 2027 → Feynman 2028)**
- DPU offload; CXL memory tiers; GPU/LPU-aware routing; confidential computing and attestation.
- Exit: measurable gains on next-generation hardware with no app code changes.

Detailed designs: [Phase 0](design/phase0.md) · [Phase 1](design/phase1.md) · [Phase 2](design/phase2.md) · [Phase 3](design/phase3.md).

## 10. Cost strategy
- **Don't buy racks.** A Vera Rubin NVL72 rack is estimated at $7.8M–$9.1M (Morgan Stanley / Bernstein), draws ~190–230 kW and needs liquid cooling. Owning only beats renting at sustained >60–70% utilization in an existing facility.
- **Build:** developer workstations (~$5K–$7K each), integration testing on hourly cloud GPUs (~$190K/yr at moderate use; less with spot).
- **Production:** customers run on their own infrastructure.
- Rising memory prices strengthen the case for tiered built-in storage.

## 11. Known risks
- **Scope:** Redis + Kafka + vector DB + app server in one binary is several products. Keep features scoped to AI-app needs and phase them strictly.
- **Single-node v1:** local state makes scale-out hard until Phase 2 replication.
- **Durability ownership:** the server now owns WAL, snapshots, backup and recovery.
- **Competition:** Microsoft Foundry Hosted Agents and AI gateways (LiteLLM, Portkey, Kong, Azure APIM). Differentiation = runs anywhere + built-in data plane + independence.
- **"App server" perception:** may suggest legacy heaviness; message "one binary, starts in seconds."
- **Hardware access:** validate future hardware on cloud early access and emulation; roadmaps slip.

## 12. Open questions
1. **Use cases:** to be provided; they validate the Phase 1 scope and the blueprint list.
2. **Audience:** open source is decided; still open is whether regulated clients are a priority (decides whether compliance features move earlier).
3. **Local model hosting in Phase 2:** confirm.
4. **Product name:** "AI App Server" is a working name.
