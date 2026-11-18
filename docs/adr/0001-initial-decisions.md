# ADR 0001: Initial architecture decisions

Date: 2026-11-18 · Status: Accepted

| # | Decision | Rationale |
|---|---|---|
| 1 | Position as an **AI App Server** (Apache/Tomcat as internal analogy only) | The product hosts apps and provides shared runtime services |
| 2 | Server core in **Go** | Single cross-platform binary; strong concurrency for streaming; Caddy/Traefik precedent |
| 3 | Server-side apps in **Python** (v1), isolated worker processes over a language-neutral protocol | AI ecosystem lives in Python; crash isolation; Node workers can be added in v2 |
| 4 | Front end in **JavaScript/TypeScript** | Developer preference; client SDK + UI components |
| 5 | **No dependency** on Microsoft Agent Framework, Semantic Kernel or .NET | Keep the product independent and distinctive |
| 6 | **Built-in tiered storage** (memory → disk → optional external) | Faster serving; fewer moving parts; external stores optional |
| 7 | **Redis-like + Kafka-like data plane** on one storage foundation, scoped to AI-app needs | Consolidation; shared quotas, encryption, backup |
| 8 | **Standard hardware baseline**, Vera Rubin → Rubin Ultra → Feynman as reference target, AMD secondary | Runs anywhere; uses future hardware via a HAL |
| 9 | **Single-node v1**; clustering in Phase 2 | Contains v1 scope |
| 10 | **Top-10 blueprints** as the Phase 1 headline | "Deploy an AI use case in minutes" |

Open: audience (general vs regulated), local model hosting in Phase 2, product name.
