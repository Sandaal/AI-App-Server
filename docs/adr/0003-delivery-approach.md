# ADR 0003: Delivery approach and default decisions

Date: 2026-11-18 · Status: Accepted

## Decision
1. Ship a **v0.5** with 3 blueprints (Knowledge chat, Document extraction, Workflow agent) before the full Phase 1 set of 10.
2. Recruit **5–10 design partners** before building full Phase 1; their feedback orders the remaining blueprints and features.
3. **Assemble proven libraries** for storage, search, consensus and PII; do not write new engines.
4. Make the repository **public when Phase 0 works end to end**, with a demo video.
5. Treat **Phase 2 clustering as conditional** on users needing more than one node.

## Default answers to open design questions
| Question (source) | Decision |
|---|---|
| Admin console scope in v1 (Phase 1) | Read-only dashboards; management through the CLI |
| Default embedding model (Phase 1) | None built in; `aiapp new` asks once and writes it to the manifest |
| Telemetry default (Phase 1) | Off by default; opt-in only |
| Minimum cluster size (Phase 2) | 3 nodes; 2 nodes + witness considered later |
| Kubernetes operator timing (Phase 2) | Phase 2.x, after core clustering |
| Default local models (Phase 2) | Only open-weight models under permissive licenses |

## Rationale
The full plan is several products' worth of work. Proving the core claim with real users early limits the risk of building features nobody needs, and keeps the plan achievable for a small team.
