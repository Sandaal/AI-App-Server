# Performance and sizing

These numbers come from the project's load test. A knowledge-chat app (retrieval plus a streamed answer) runs behind a **fake model**: 300 ms to the first token, then 60 tokens at 15 ms each, about 1.2 s per answer. The fake model is used so that the numbers show the server and not a provider. With a real model, add its latency, and expect its rate limits to cap throughput long before the server does.

## Measured
The tests ran in Docker containers on an 8-core desktop (Windows host, Linux containers), with CPU and memory capped as shown. A real VM of the same size will do at least as well.

| Setup | Documents (vectors) | Indexing | Memory after indexing | Concurrency | Requests/s | First token p50 / p95 | Whole answer p50 / p95 | Errors |
|---|---|---|---|---|---|---|---|---|
| 4 CPU, 8 GB, 4 workers | 2,000 (4,000) | 19 s | 293 MB | 1 | 0.9 | 310 / 314 ms | 1225 / 1230 ms | 0 |
| | | | | 8 | 6.4 | 322 / 331 ms | 1270 / 1299 ms | 0 |
| | | | | 32 | 25.8 | 317 / 420 ms | 1248 / 1414 ms | 0 |
| | | | | 64 | 49.0 | 401 / 509 ms | 1364 / 1598 ms | 0 |
| | | | | 128 | 74.7 | 673 / 1106 ms | 1757 / 2147 ms | 0 |
| 8 CPU, 12 GB, 8 workers | 20,000 (40,000) | 354 s | 1,529 MB | 64 | 47.0 | 388 / 609 ms | 1360 / 1631 ms | 0 |
| | | | | 128 | 73.0 | 700 / 1146 ms | 1783 / 2378 ms | 0 |
| | | | | 256 | 94.3 | 1388 / 2101 ms | 2839 / 3705 ms | 0 |

- **Overhead:** up to about 32 concurrent conversations, the server adds almost nothing to the model's own time (1.25 s versus 1.2 s). Beyond about 64 per app, first-token latency grows.
- **Errors:** none at any level.
- **Memory** is dominated by the documents (text, vectors, keyword index, graph) and by the workers, at about 60–80 MB each. Peak memory under load was 326 MB and 1,736 MB for the two runs.
- **Indexing** ran at about 100 documents/s for a small collection and about 56/s at 20,000 documents, as graph inserts cost more in a larger graph. Indexing runs in background jobs, so the app answers while it indexes.
- **Vector search:** on its own, at 20,000 vectors of 384 dimensions, it takes about 1.5 ms (float32) or 2.0 ms (int8), with recall@10 of 1.0.

**Where throughput stops.** Doubling the CPUs didn't raise throughput at 128 concurrent (74.7 vs 73.0 req/s). The limit for one app is its request pipeline (workers, retrieval and the model connection), not the core count. Because of that:
- For more throughput, run more apps on one server, give an app more workers, or run more servers.
- Most deployments will meet the model provider's rate limits first.

## Memory per item
| Item | Approximate memory |
|---|---|
| Server, idle | about 40 MB |
| Worker (Python process) | 60–80 MB idle; capped by `--worker-memory` (default 2 GB) |
| Vector, 768 dims, float32 | 3 KB |
| Vector, 768 dims, int8 (`--vector-quantization int8`) | 0.8 KB |
| Graph (HNSW, M=24), per vector | about 0.5 KB |
| Chunk text plus keyword index | about 2× the text size |

**Quantization:** `--vector-quantization int8` halved the heap of a 10,000 × 768 collection (43 → 22 MB), with scores within 0.002 and recall@10 of 0.96 against float search. It makes vector search about 30% slower. It is worth it from about a million vectors, or on memory-limited VMs.

## On the target VM (16 vCPU, 64 GB)
These figures are extrapolated from the measurements, not measured on such a VM.

- **Apps:** 20 apps with 2–4 workers each come to about 4–6 GB of workers.
- **Documents:** a few million chunks fit in memory:
  - float32: about 4 KB each with text, so 1 M chunks ≈ 4 GB, plus the graph
  - int8: about 1.5 KB each, so 1 M chunks ≈ 1.5 GB
- **Concurrency:** several hundred concurrent conversations across apps, bounded by model providers.
- **Disk:** plan for 3–5× the size of the source documents (encrypted KV, the vector snapshot and graph, versions, Python environments), plus the audit log, which grows with traffic. Keep `/data` on SSD block storage; network file shares must be NFS, never SMB.

## Tuning
- **`workers:`** in an app's manifest: raise it for apps with heavy Python handlers.
- **Quotas:** `aiapp quota set APP --concurrency N` protects other apps from a burst, and `--worker-memory` caps a heavy app.
- **`--vector-quantization int8`** for large collections.
- **More than one server:** separate servers isolate whole teams. A [cluster](cluster.md) adds availability and capacity: every node serves, and data is replicated across nodes.
