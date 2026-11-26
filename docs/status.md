# Project status and help wanted

*Updated 2026-11-25 for v3.0.0.*

AI App Server is built and tested by a very small team. Much of it runs on any computer and has been tested for real. Some of it is for hardware and paid services we don't have yet, such as GPU servers, DPUs, CXL memory and confidential VMs. Those parts are built and tested against **emulated hardware or fakes of the services**, and this page says exactly which ones. If you have access to that hardware, [you can help](#how-you-can-help).

## Where the project is

| Phase | Version | What it adds | Status |
|---|---|---|---|
| 0 | v0.5.0 | The single-server runtime: apps from `ai-app.yaml`, Python handlers, embedded storage | Released |
| 1 | v1.0.0 | Ten blueprints, the model gateway, agents and workflows, security, the console, installers | Released |
| 1.x | v1.1.0 | Production hardening: evaluations, MCP, guardrail providers, sign-in, secrets and vaults | Released |
| 2 | v3.0.0 | JavaScript handlers, local models, Redis and Kafka compatibility, external stores, hardware profiles, context memory, clusters | Released. Hardware benchmarks not yet run |
| 3 | v3.0.0 | Data-plane drivers, routing by latency and cost, vector tiering, confidential apps | **Preview:** tested on emulated hardware only. The DPU driver isn't built yet |

## What "tested" means here

- **Real:** it ran against the real thing, such as real models, real servers or real operating systems.
- **Fake:** it ran against a stand-in that speaks the same protocol, such as recorded API responses, an in-process Kafka, or a fake key broker. This checks our side of the protocol, but not the service's quirks.
- **Emulated:** the hardware was simulated, from a hardware profile (`AIAPP_HAL_PROFILE`) or an emulated attestation platform. This checks the logic and the fallbacks, but not real hardware.
- **Not yet:** built, but not run end to end.

Every push runs the full test suite with the race detector on Linux. Release tags also run it on macOS and Windows, plus the browser tests.

## Tested for real

| Area | How it was tested |
|---|---|
| All ten blueprints, from `aiapp new` to a correct answer | Real local models (Ollama `llama3.2:3b`, `nomic-embed-text`) on an 8-core desktop |
| Linux, macOS and Windows builds; Docker; Kubernetes (Helm) | CI, plus container and Helm restart tests that keep the data |
| Restarts, backup and restore, version rollback | End-to-end tests on a server running all ten apps |
| App isolation (memory, disk, files, budgets, request floods) | A misbehaving app next to a well-behaved one, on Linux |
| Python and JavaScript (Node.js) handlers | Conformance suite for both runtimes |
| Local models on CPU (llama.cpp) and context memory | Real models on CPU; time-to-first-token gains measured |
| Redis clients (RESP3) | `redis-cli`, redis-py and node-redis |
| External stores: Redis, PostgreSQL with pgvector | Real servers in containers |
| Secrets from HashiCorp Vault | Real Vault dev server |
| MCP server and client | A client built on the official MCP Go SDK, with real workers and a local model |
| Clusters: three nodes, replication, failover | Three containers on one machine; a node-loss test with about 2,600 writes, none lost |
| Web pages and components | Browser tests (Playwright) |

## Tested against fakes

These need accounts or paid services. We plan to check them against the real services before calling them verified.

| Area | Fake used |
|---|---|
| Hosted models: OpenAI, Azure OpenAI, Anthropic, Google Gemini, AWS Bedrock | Recorded protocol responses |
| Speech-to-text (OpenAI, Azure) for meeting notes | Recorded responses |
| Kafka and Azure Event Hubs | franz-go's in-process Kafka (a real broker can be used with `KAFKA_BROKERS`) |
| Azure AI Search store | A fake of its REST API |
| Azure Key Vault, Azure AI Content Safety, Entra ID sign-in | Fakes of their APIs |
| Connectors: S3, Azure Blob, SharePoint, OneDrive | Fakes. SQL Server is compiled but not run; private Git with tokens isn't tried |
| Commercial SIEMs and token-introspection providers | Generic protocol tests |
| Model routing to prefill/decode engines such as NVIDIA Dynamo | Fake OpenAI-compatible backends with set latencies |
| Key brokers for confidential apps | A fake broker that speaks the server's protocol |
| Azure deployment (azd) | Templates compile; not deployed |

## Tested on emulated hardware

| Feature | What's emulated | What real hardware would show |
|---|---|---|
| GPU allocation and vLLM supervision | GPUs in a hardware profile | Whether vLLM, GPU allocation and KV-cache offload (LMCache) work and how fast |
| Hardware detection: multi-socket NUMA, CXL memory, GPUs, Grace-class coherent memory | Built-in hardware profiles | Whether detection reads real machines correctly |
| Vector tiering onto CXL memory | `cxl-server` profile; the kernel's tiering setting | Real latency and capacity gains |
| Data-plane drivers and BlueField detection | `dpu-server` profile | Detection on a real card (the DPU driver itself isn't built, see below) |
| Confidential apps (AMD SEV-SNP, Intel TDX) | An emulated attestation platform with a public test key | Real attestation reports and real key brokers |

## Not built yet

- **BlueField DPU driver (M3.2):** encryption, checksums and TLS offloaded to the DPU. It needs a BlueField-2 or BlueField-3 card and NVIDIA's DOCA SDK to build and test. The server already detects the card, checks a driver's results against the CPU's, and falls back.
- **Hardware benchmarks (M2.9, M3.6):** published numbers on a standard VM, a GPU server, and next-generation hardware. The Phase 3 target is at least 30% lower time to first token on long-context chat and 30% less host CPU per request.
- **Blob store adapters** (S3, Azure Blob) for app files.

## What we need

| What | What it unlocks | Size of the ask |
|---|---|---|
| A cloud VM, 16 vCPU / 64 GB | Baseline benchmarks for the CPU-only setup | A few days |
| One or more NVIDIA GPUs (L4/L40S/H100 class) | vLLM, GPU allocation, KV-cache offload, prefill/decode routing, GPU benchmarks | Days to a few weeks |
| A confidential VM: AMD SEV-SNP or Intel TDX (for example Azure DCasv5/ECasv5 or a TDX VM) | Real attestation and key release for confidential apps | Days |
| A server with an NVIDIA BlueField-2/3 DPU, with DOCA | Building the DPU driver and measuring offload | Weeks |
| A server with CXL memory | Verifying CXL detection and vector tiering | Days |
| A multi-socket server, or a Grace Hopper / Grace Blackwell system | NUMA and coherent-memory placement | Days |
| An Azure subscription with credits | Event Hubs, AI Search, Key Vault, Entra, Content Safety, Blob, azd deployment | Ongoing, small |
| API credits for hosted models (OpenAI, Anthropic, Gemini, Bedrock, Azure OpenAI) | Live checks of every provider adapter | Small |

## How you can help

1. **Offer hardware access or cloud credits.** Open a [hardware offer](https://github.com/Sandaal/ai-app-server/issues/new?template=hardware-offer.yml). Say what you have and for how long. Remote access for a few days is often enough. Don't post credentials in the issue; we'll arrange access privately.
2. **Share your machine's profile.** If you run on any of the hardware above, install the server and run:

    ```bash
    aiapp hardware --json > my-hardware.json
    ```

    Attach the file to a hardware offer, or to an [issue](https://github.com/Sandaal/ai-app-server/issues). It shows whether detection reads your machine correctly. It contains your CPU, memory, disk, GPU and PCI device details, and no data. Read it before you post it.
3. **Try the server against a real service** you already use (Kafka, Event Hubs, S3, SharePoint, a SIEM, a hosted model) and report what works and what doesn't.
4. **Improve the example apps and SDKs** in [`apps/`](https://github.com/Sandaal/ai-app-server/tree/main/apps) and [`sdk/`](https://github.com/Sandaal/ai-app-server/tree/main/sdk) through pull requests.

Results from contributed hardware will be published on this page, with credit if you want it.
