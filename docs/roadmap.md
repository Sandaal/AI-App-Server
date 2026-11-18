# Roadmap

*Last updated 2026-11-18. Planning assumption: one experienced developer working with AI coding tools. Estimates are planning guesses, not commitments; revisit when team size changes.*

## Approach
1. **Prove the core claim early:** "deploy an AI use case in minutes, no other infrastructure." Everything before v0.5 serves that claim.
2. **Narrow first release:** 3 blueprints, not 10.
3. **Let design partners reorder the plan** before full Phase 1 is built.
4. **Assemble, don't invent:** proven libraries for every hard part; our value is integration and developer experience.
5. **Measure one number publicly:** time from install to a working app, compared with the usual stack.
6. **Clustering (Phase 2) is conditional** on real users needing more than one node.

## Stages
| Stage | Scope | Estimate | Gate to move on |
|---|---|---|---|
| **Phase 0** | Core, worker protocol, model gateway, minimal storage, Knowledge chat | 6–10 weeks | Knowledge chat deploys in < 5 min on a clean VM |
| **Public launch** | Repo goes public with a 2-minute demo video and benchmark | 1–2 weeks | Demo reproducible by an outside developer |
| **v0.5** | Blueprints: Knowledge chat, Document extraction, Workflow agent; storage v1 core (data structures, HNSW + hybrid, encryption, backup); jobs; tools + MCP client; approvals | +3–4 months | 5–10 design partners using it on real problems |
| **Phase 1 (v1.0)** | Remaining 7 blueprints, ordered by partner feedback; full pipeline, gateway v2, lifecycle, SDKs, VS Code, connectors, observability, Windows | Small team (3–5), 6–9 months | All Phase 1 exit criteria |
| **Phase 1.x** | Consumer groups, MCP gateway, evals, Key Vault, hardening | Ongoing | Production feedback |
| **Phase 2** | Clustering, HAL v1, local inference, context memory, Node runtime, compatibility | 6–12 months | Only when users need multi-node |
| **Phase 3** | DPU, CXL, heterogeneous routing, confidential computing | Tracks hardware availability | Hardware access |

## Why these 3 blueprints for v0.5
Together they exercise almost every building block, so the other 7 become mostly templates:

| Building block | Knowledge chat | Document extraction | Workflow agent |
|---|---|---|---|
| Ingestion, vectors, hybrid search | ● | | |
| Conversation memory, streaming | ● | | ● |
| File store, durable jobs | ● | ● | |
| Structured output + validation | | ● | ● |
| Tool calling, MCP client | | | ● |
| Checkpointed workflows, approvals | | | ● |

## Design partners
- **Who:** 5–10 developers or teams in the Microsoft ecosystem (Python/TypeScript) with a real AI use case to ship.
- **What they get:** early access, direct support, influence on the roadmap.
- **What we learn:** whether "deploy in minutes" is the reason to choose it; whether built-in storage matters to them or they already run Redis/Postgres; which blueprint and connector matter most; what blocks production use.
- **How:** a short feedback session after first deploy, then monthly.

## Success metrics
| Metric | Target at v0.5 |
|---|---|
| Install → working Knowledge chat | < 5 minutes |
| Lines of code a developer writes for a blueprint | 0 to customize via YAML; < 50 for a custom handler |
| Design partners using it on real data | ≥ 5 |
| External infrastructure required | None |

## Libraries (assemble, don't invent)
| Need | Candidate |
|---|---|
| KV storage | Pebble |
| Vectors | Existing Go HNSW library (evaluate `coder/hnsw` and alternatives in M0.4) |
| Full-text search | Bleve |
| Metadata | SQLite (pure-Go driver) |
| Worker protocol | gRPC-Go, grpcio (Python) |
| PII detection | Microsoft Presidio (system worker) |
| Python environments | uv |
| Consensus (Phase 2) | hashicorp/raft or etcd/raft |
| Telemetry | OpenTelemetry |
