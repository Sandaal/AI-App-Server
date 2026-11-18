# Phase 3 Design: Future-Hardware Native

*Status: early draft · 2026-11-18 · Builds on [Phase 2](phase2.md)*

This phase targets hardware arriving in 2027–2028 (NVIDIA Rubin Ultra and Feynman, AMD MI500, CXL 4.0 memory pools). Its details will change as that hardware ships. The design commits to **capabilities**, not product names, and every feature must fall back cleanly on hardware that lacks it.

## 1. Goal and exit criteria
**Goal:** when next-generation hardware is present, the server moves work onto it automatically, so apps get faster and cheaper with no code changes.

**Exit criteria**
1. On next-generation hardware, the reference blueprints show measurable gains over Phase 2 on the same app packages: target ≥30% lower time to first token on long-context chat and ≥30% lower host CPU use per request.
2. Every Phase 3 feature has a fallback path, tested in CI with emulated hardware profiles.
3. Regulated deployments can prove, with hardware attestation, that their data and models ran only inside verified environments.

## 2. DPU offload (BlueField-class data processors)
Move data-plane work off the host CPUs so they're free for app workers and inference.

| Work | Offload target |
|---|---|
| TLS termination and inter-node encryption | DPU crypto engines |
| Storage encryption, checksums | DPU, inline on the NVMe path |
| Context memory / KV-cache tier | DPU-managed NVMe (e.g. NVIDIA's context memory storage platform) |
| Topic and log replication traffic | DPU networking (RDMA) |
| Network policy between apps | DPU-enforced isolation |

- Implemented as a **data-plane driver interface** in the HAL with two implementations: host (default) and DPU (NVIDIA DOCA first; others as they mature).
- The control plane stays on the host; only the data path moves.

## 3. Memory tiers: CXL and coherent memory
- **CXL pools** become an extended hot tier between DRAM and NVMe: large vector indexes, warm conversation memory and evicted KV cache live there.
- **Coherent CPU–GPU memory** lets app context (retrieved chunks, conversation state) hand off to inference without copies.
- **Placement engine v2:** moves data between tiers by observed access frequency, not only static policy; per-app memory quotas extend across tiers.
- Memory pooling across nodes is treated like another tier with higher latency, configured per data class.

## 4. Heterogeneous inference routing
Next-generation systems mix GPUs with specialized inference processors (LPUs) and split prefill (reading the prompt) from decode (generating tokens).

- The model gateway routes by **capability and phase**: long-prompt prefill to the hardware best at it, latency-sensitive decode to another, small classification models to CPU or low-power accelerators.
- Cost-aware routing: per-request choice between local hardware and hosted providers based on queue depth, latency target and cost budget.
- Integrated through inference engines (NVIDIA Dynamo and successors) rather than custom kernels.

## 5. Confidential computing and attestation
For regulated and sensitive workloads.

- Run app workers and inference inside confidential environments (AMD SEV-SNP, Intel TDX, NVIDIA GPU confidential computing) when available.
- **Attestation:** each node proves its hardware and software state; the control plane admits only attested nodes into "confidential" shards.
- **Key release:** data keys for confidential apps are released only to attested environments (integrating with a key service such as Azure Key Vault Managed HSM or HashiCorp Vault).
- Audit records include attestation evidence, so an auditor can verify where data was processed.
- **Compliance pack:** documented control mappings (e.g. NIST 800-53, HIPAA) for audit, encryption, isolation and attestation features.

## 6. Hardware validation program
- **Capability specs:** each hardware feature has a written spec (what the server expects, how it's detected, how it falls back).
- **Emulation:** CI runs every feature against emulated profiles.
- **Real hardware:** benchmark rounds on cloud capacity as each generation becomes available; results published in the repo.
- **Vendor neutrality check:** any feature implemented for one vendor gets an issue tracking the equivalent for others.

## 7. Milestones
| # | Milestone | Done when |
|---|---|---|
| M3.1 | Data-plane driver interface | Host and DPU drivers behind one interface; host driver passes all tests |
| M3.2 | DPU offload | TLS, storage encryption and KV-cache tier offloaded on BlueField-class hardware |
| M3.3 | CXL / coherent tiers | Placement engine v2 with access-based tiering; CXL tier benchmarks |
| M3.4 | Heterogeneous routing | Prefill/decode and GPU/LPU-aware routing through Dynamo-class engines |
| M3.5 | Confidential computing | Attested nodes, key release, attestation in audit records |
| M3.6 | Validation report | Published benchmarks meet the exit targets |

## 8. Risks
| Risk | Mitigation |
|---|---|
| Hardware roadmaps slip or change | Capability specs, not product names; phase can ship partially |
| Vendor SDK lock-in (e.g. DOCA) | Driver interface; vendor code isolated in drivers |
| Small user base for exotic hardware early on | Prioritize features that also help on standard hardware (tiering, routing) |
| Confidential computing performance overhead | Opt-in per app; benchmark and publish the overhead |
