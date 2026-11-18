# Phase 2 Design: Scale-Out and the First Hardware Leap

*Status: draft for review · 2026-11-18 · Builds on [Phase 1](phase1.md)*

## 1. Goal and exit criteria
Run the same apps across many nodes and take advantage of GPU and memory-rich hardware, without app code changes.

**Exit criteria**
1. A 3-node cluster survives losing any one node with no acknowledged-data loss and no manual steps; apps keep serving.
2. The same app package runs unchanged on a single VM and on a Vera Rubin-class system, measurably faster on the latter.
3. Apps can use locally hosted models through the same logical model names they use for hosted ones.
4. Node.js handlers run alongside Python handlers through the same worker protocol.
5. Existing Redis clients and Kafka pipelines can connect to the server.

## 2. Clustering
### 2.1 Topology
- **Control plane:** a Raft group (3 or 5 voters) holds cluster metadata: nodes, apps, versions, shard map, secrets index, quotas. Library: `hashicorp/raft` or `etcd/raft` (decide in M2.1 spike).
- **Data plane:** data is split into **shards**. Each app namespace is assigned to a shard; large apps can be split across several shards by key hash. Each shard is a Raft group of 3 replicas on different nodes.
- **Workers:** any node can run any app's workers. The scheduler places worker pools by app demand, node capacity and data locality (prefer nodes that lead the app's shard).

### 2.2 What gets replicated, and how
| Data | Replication |
|---|---|
| KV / data structures | Raft log per shard; Pebble applies committed entries |
| Vectors | Records replicated through the shard log; each replica builds its own HNSW index |
| Full-text index | Same as vectors: derived locally from replicated records |
| Blobs | Content-addressed; replicated to N nodes by background copy, tracked in shard metadata |
| Topics | One Raft group per topic partition (Kafka-style ISR replaced by Raft quorum) |
| Audit logs | Written to the shard log of the app; compacted into segment files |

Reads go to the shard leader by default; apps can opt into follower reads (bounded staleness) for search-heavy routes.

### 2.3 Routing and sessions
- Any node accepts requests; it forwards to a node running the target app's workers.
- **Session affinity:** requests with the same `session_id` prefer the same node, so hot conversation memory stays local (falls back cleanly if the node goes away).
- Membership and failure detection through the control plane, with health probes between nodes.

### 2.4 Operations
- `aiapp cluster init / join / leave / status`.
- Rolling upgrades one node at a time; protocol versioning between nodes.
- Rebalancing: moving a shard replica copies a snapshot, then catches up from the log.
- Kubernetes operator for automated deployment and scaling (Phase 2.x if time is short).

## 3. Hardware Abstraction Layer (HAL) v1
At startup, each node builds a **capability profile** and reports it to the control plane.

| Capability | Detection (Linux) | Used for |
|---|---|---|
| CPU cores, ISA features (AVX-512, AMX, SVE, NEON) | `/proc/cpuinfo`, cpuid | Vector distance kernels, worker counts |
| Memory per NUMA node | `/sys/devices/system/node` | Hot-tier sizing, NUMA-pinned workers |
| CXL-attached memory | NUMA nodes without CPUs; CXL sysfs | Extended hot tier (Phase 3 tuning) |
| NVMe devices and their speed | `/sys/block`, quick probe | Warm-tier placement, WAL device choice |
| GPUs, memory, interconnect | NVML (NVIDIA), ROCm SMI (AMD) | Inference placement, GPU vector search |
| Coherent CPU–GPU memory | Driver attributes (e.g. NVLink-C2C, unified memory APUs) | Zero-copy context handoff |

**Tier placement policy:** each data class (sessions, hot vectors, cold vectors, blobs, logs) has a preferred tier list. The HAL maps it to what the node has, for example `hot vectors → GPU memory | coherent memory | DRAM | NVMe(mmap)`.

**Vector search acceleration:** optional GPU index (e.g. CAGRA via cuVS on NVIDIA) for large collections; falls back to CPU HNSW.

The HAL has an **emulated profile mode**, so CI and laptops can test placement decisions for hardware they don't have.

## 4. Local inference
The server integrates inference engines; it doesn't implement one.

| Engine | Use |
|---|---|
| vLLM | Default for GPU servers (NVIDIA and AMD) |
| NVIDIA Dynamo | Large multi-GPU / disaggregated prefill-decode deployments |
| llama.cpp | CPU-only, edge and unified-memory workstations |

- **Inference workers:** engines run as supervised processes managed like app workers, with health checks and restarts. They expose OpenAI-compatible endpoints that the model gateway already speaks.
- **Model registry:** `aiapp model pull <name>`, checksum-verified, stored in the blob store; offline import for air-gapped sites.
- **GPU scheduling:** the scheduler assigns models to GPUs by memory need; one model per GPU set in Phase 2 (fractional sharing later).
- **Logical names unchanged:** an app's `chat` model can point to a hosted provider today and a local model tomorrow, by config only.

## 5. Context Memory service
Connects application memory (sessions, conversation history, retrieved context) with the inference engine's KV cache.

- **Prefix-aware routing:** requests that share a long prompt prefix (system prompt + retrieved context + history) are routed to the same engine instance, so its KV cache is reused instead of recomputed.
- **KV-cache tiering:** integrate LMCache (or the engine's native offload) to keep evicted KV cache in DRAM or NVMe and reload it, instead of recomputing long contexts.
- **Session lifecycle:** when a session ends or goes idle, its KV cache is released; when it resumes, the server pre-warms it if the tier still holds it.
- **Metrics:** cache hit rate, recompute tokens avoided, time to first token.

## 6. Node.js worker runtime
- Implements the same `Worker` and `Host` gRPC services as the Python runtime.
- SDK `@aiapp/server` mirrors the Python SDK (`app.route`, `app.models`, `app.vectors`, ...).
- `runtime: node22` in the manifest; per-app `node_modules` cached by lockfile hash.
- One app can mix runtimes per route (e.g. Python for RAG, Node for an API adapter).

## 7. Compatibility layers
- **Redis protocol (RESP3):** a listener that speaks the Redis wire protocol for the supported data structures, mapped to an app namespace by an auth token. Supported commands are documented; unsupported ones return a clear error. Not a full Redis (no Lua, no modules).
- **Kafka connectors:** source and sink connectors that bridge external Kafka (or Azure Event Hubs, which speaks the Kafka protocol) topics to built-in topics. No Kafka wire-protocol server.
- **External store adapters:** Redis, PostgreSQL/pgvector, Azure AI Search, Azure Blob/S3, selected per app in config, for teams that want an existing system of record.

## 8. Milestones
| # | Milestone | Done when |
|---|---|---|
| M2.1 | Raft spike + control plane | 3-node control plane survives leader loss; library chosen |
| M2.2 | Sharded data plane | KV, vectors, topics replicated; node-loss test passes with zero acknowledged-write loss |
| M2.3 | Cluster routing + scheduling | Requests served from any node; worker placement and session affinity work |
| M2.4 | HAL v1 | Capability profiles on real and emulated hardware; tier placement applied |
| M2.5 | Local inference | vLLM and llama.cpp managed; logical models switch hosted ↔ local by config |
| M2.6 | Context Memory | Prefix-aware routing and KV-cache tiering show measured TTFT gains |
| M2.7 | Node runtime | Node handlers pass the same conformance suite as Python |
| M2.8 | Compatibility | RESP listener and Kafka/Event Hubs connectors; external store adapters |
| M2.9 | Hardware validation | Benchmarks on standard VM vs GPU server vs Vera Rubin-class cloud capacity |

## 9. Risks
| Risk | Mitigation |
|---|---|
| Distributed storage is the hardest part of the whole product | Proven Raft library; Jepsen-style fault-injection tests from M2.2; keep single-node mode first-class |
| GPU vendor differences | Use engines that already support NVIDIA and AMD; HAL reports capabilities, not vendors |
| Access to Vera Rubin-class hardware | Cloud early access for M2.9; emulated profiles for everything before it |
| RESP compatibility expectations | Publish the supported command list; conformance tests against common clients |

## 10. Open questions
1. Minimum cluster size: allow 2 nodes plus a witness, or require 3?
2. Should the Kubernetes operator be part of M2.3 or a separate Phase 2.x deliverable?
3. Local inference licensing: which open-weight models to list in the registry by default.
