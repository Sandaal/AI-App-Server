# Changelog

## Unreleased

- **Docs site home page** rebuilt as a landing page: the problem it solves, a comparison with the usual stack, three steps to a live app, the ten blueprints, production features, measured numbers and who it's for. There is a new Performance and sizing page, and the FAQ is up to date (JavaScript handlers, clusters). The public README follows the same story.

## v3.0.0 (2026-11-25)

Phase 2 (ADRs 0040–0049) and the first Phase 3 milestones (ADRs 0050–0053), in the v2.0 plan and the v3.0 plan.

**What is verified and what isn't.** Phase 2 is tested on real systems: local models on CPU, Redis clients, pgvector, three-node clusters and the Node.js runtime. GPU, vLLM, Event Hubs and Azure AI Search have run only against emulated GPUs or fakes. The Phase 3 features are a **preview**: data-plane drivers, CXL tiering and confidential apps have run only on emulated hardware, and the BlueField DPU driver isn't built yet. The hardware benchmarks (M2.9, M3.6) are still to do. The [Project status](https://sandaal.github.io/ai-app-server/status/) page lists every area and how it was tested.

- **Project status page** on the docs site: what is tested on real systems, what on emulated hardware or fakes, and the hardware the project needs. The public repository has a hardware-offer issue form.

- **Confidential apps.**
  - **Placement:** `confidential: {}` in the manifest runs an app only on servers that attest with AMD SEV-SNP or Intel TDX, through Linux's configfs-tsm. `measurements: [...]` limits it to approved VM images. In a cluster such apps are placed only on attested nodes.
  - **Key release:** with `--key-broker URL`, the app's data key is wrapped by a key a broker releases only against a fresh attestation report. A server without it can't read the app's data, even with the master key.
  - **Audit:** the node's evidence is in the audit log, and every record carries a reference to it.
  - **Tested:** with an emulated platform and a fake broker.

  (ADR 0053)
- **Vector collections move between memory and disk by use.**
  - **Budget:** collections may take half of the memory, plus half of any CXL memory the kernel tiers to.
  - **Over budget:** the collections used longest ago go to their own encrypted file. They load back on their next search or write with the same results, and stay on disk across restarts.
  - **Idle collections:** `--vector-cold-after` also moves collections unused for a while.
  - **Backups and cluster snapshots** carry every collection in full, and quotas count every tier.
  - **Visibility:** `aiapp hardware` shows the split and the plan's warm tier (CXL or DRAM).

  (ADR 0052)
- **Model routing by request, latency and cost.**
  - **Conditions:** a deployment can take only some requests: `min_prompt_tokens`, `max_prompt_tokens` and `max_output_tokens`. Long prompts go to long-context engines and short classifications to small CPU models.
  - **`routing: latency`:** picks the deployment predicted to answer first, from its measured time to first token and the calls it is serving.
  - **`routing: cost`:** picks the cheapest deployment predicted to answer within `latency_target_ms`. So a free local model takes the traffic until requests queue on it, and then they spill to a hosted model.
  - **Budgets:** apps past 80% of a model budget get the cheapest target.
  - **Visibility:** `aiapp gateway` shows each deployment's time to first token and the calls in progress.

  (ADR 0051)
- **Data-plane drivers (Phase 3 begins).**
  - **What:** encryption of stored data, checksums, TLS, the inference KV-cache tier and cluster replication traffic now go through one driver interface.
  - **Drivers:** the host driver (the CPUs) is the default. A DPU driver can take over when the hardware has a data processor.
  - **Choosing:** `--data-plane auto|host|dpu`. A driver is used only after it proves it gives the host driver's exact ciphertext and digests; otherwise the server falls back to the host and says why.
  - **Detection:** BlueField, BlueField-2 and BlueField-3 cards (PCI scan), plus an emulated `dpu-server` profile.
  - **Visibility:** `aiapp hardware` shows where each function runs and how much work it has done.

  (ADR 0050)
- **Clusters, part 3: every node serves.**
  - **Serving:** every node runs the apps' workers and serves requests itself. The leader also runs jobs, subscriptions, schedules, Kafka bridges and connector syncs, and a node that becomes leader starts them in place.
  - **Consistency:** writes that read and then change data (counters, sets, lists, locks, topic offsets, approvals, model spend) run on the leader, so concurrent requests on different nodes never lose an update. A node reads its own writes.
  - **Placement:** `cluster: { nodes: N }` in the manifest runs an app on N nodes (the leader and N−1 others); by default it runs on every node.
  - **Routing:** requests with `X-Session-Id` always go to the same node, which keeps that conversation's context cache warm. Responses say which node served them in `X-AIApp-Node`.
  - **Faster failover:** elections in data clusters take under a second.
  - **Fix:** a restarted node could report itself caught up while thousands of entries were still queued for its stores.
  - **Tested:** in the node-loss test about 2,600 writes went through a follower while the leader was killed, and none was lost. 150 concurrent increments through three nodes add up to exactly 150.

  (ADR 0049)
- **Clusters, part 2: replicated data and failover.**
  - **What is replicated:** every write a cluster acknowledges is on a majority of nodes before the reply. That covers app data, memory, jobs, events, vectors, files, deployed versions, keys and secrets.
  - **Serving:** the leader runs the apps and the other nodes forward requests to it. If the leader fails, another node takes over the apps with all the data.
  - **Joining:** new nodes receive a full copy and join as non-voters until they have caught up.
  - **Tested:** in the node-loss test the leader was killed during 2,824 acknowledged writes, and none was lost.

  (ADR 0048)
- **Clusters, part 1: the control plane.**
  - **Forming one:** start servers with `--cluster-addr` and form a cluster with `aiapp cluster init`, `aiapp cluster join ADDR --token …`, `leave`, `remove` and `status`.
  - **How it works:** a Raft group (hashicorp/raft, with its log on Pebble) agrees on membership, leadership, node health and cluster settings. It survives losing a minority of nodes, and restarted nodes rejoin by themselves.
  - **Security:** all node-to-node traffic is TLS 1.3, pinned to the cluster's own certificate, and joining needs a token.
  - **Not yet:** replicated app data and routing come next.

  (ADR 0047)
- **Context memory (faster first tokens for long contexts):**
  - **Prefix-aware routing:** requests that share a prompt prefix (a conversation, or a long system prompt) go to the engine replica that already holds it in its KV cache. It applies to local models with `replicas: N`, and to logical models with `routing: prefix` over your own inference servers. New conversations are balanced over replicas, and the load is bounded.
  - **KV-cache tiering:** llama.cpp's RAM tier (`cache_ram`) keeps evicted prompt caches.
  - **Measured on CPU:** warm time to first token went from 1.21 s to 0.08 s with prefix routing (round-robin for comparison), and from 3.53 s to 0.12 s with the RAM tier.

  (ADR 0046)
- **Hardware profile and placement (HAL v1):**
  - **What it reads:** at startup, the server reads the CPU (cores, AVX-512, AMX, SVE…), memory, NUMA nodes, CXL memory, disks, GPUs and coherent CPU-GPU memory.
  - **What it sizes from them:**
    - the key-value cache: a sixteenth of memory, where it was 8 MB;
    - vector precision: a new `--vector-quantization auto` default, which uses int8 only when vectors outgrow a quarter of memory;
    - llama.cpp threads and NUMA spreading.
  - **Warnings:** about slow disks.
  - **Seeing it:** `aiapp hardware` shows the profile and where each kind of data goes. `--profile gpu-server` (and other emulated machines) previews hardware you don't have, and `AIAPP_HAL_PROFILE` makes a server use one.

  (ADR 0045)
- **External stores:**
  - **Choosing them:** set `storage:` in `ai-app.yaml`. Key-value data (`app.kv`, chat memory and workflow state) can live in Redis, and vectors (`app.vectors` and indexed documents) in PostgreSQL/pgvector or Azure AI Search.
  - **What doesn't change:** handlers. Stores are checked when the app is deployed, and an unreachable one fails the deploy.
  - **Tested:** against real Redis 7.4 and PostgreSQL 17 with pgvector. Azure AI Search is tested against a fake of its API.

  (ADR 0044)
- **Kafka and Azure Event Hubs bridges:**
  - **Declaring them:** under `kafka:` in `ai-app.yaml`. A source brings a Kafka topic's records into an app topic, where subscriptions handle them. A sink sends an app topic out.
  - **Signing in:** TLS, SASL PLAIN or SCRAM, or an Event Hubs connection string. Credentials come from `${SECRET}` references.
  - **Delivery:** at least once, in order per partition, resuming after restarts. Quotas and event guardrails apply.
  - **Status:** `aiapp kafka APP` shows each bridge's state, records moved and errors.
  - **Tested:** against franz-go's fake cluster in CI and against a real Apache Kafka 3.9.0. Event Hubs itself is not yet tested.

  (ADR 0043)
- **Redis protocol:**
  - **Turning it on:** `aiapp serve --resp-addr 127.0.0.1:6379`. RESP2 and RESP3 and pipelining are supported, with optional TLS.
  - **What clients see:** Redis clients (`redis-cli`, redis-py, node-redis, go-redis…) sign in with `AUTH <app> <api-key>` and work with that app's data, the same data `app.kv` sees. The key needs the new `kv` role.
  - **Commands:** strings, counters, expiry, hashes, lists, sets and sorted sets. Unsupported commands say why.
  - **Limits:** quotas and value limits apply.

  (ADR 0042)
- **Local models (llama.cpp and vLLM):**
  - **What it does:** the server runs inference engines itself and supervises them. They start with the server, restart when they crash, wait while loading and stop with the server.
  - **Declaring them:** under `local:` in `gateway.yaml`.
  - **Using them:** apps call them with `provider: local`, or through logical models. Switching an app between hosted and local is then a `gateway.yaml` change only.
  - **Model store:** `aiapp model pull` downloads from a small catalog of Apache-2.0 models, or any GGUF with `--url` and `--sha256`, and checks the SHA-256. `aiapp model import` adds a model on an offline server, `aiapp model list` shows models and their states, and `aiapp model rm` deletes one.
  - **GPUs:** each model gets its own GPU set (`gpus`, `gpu_ids`, `gpu_memory`), found with `nvidia-smi` or listed with `AIAPP_GPUS`. vLLM gets tensor parallelism over them.
  - **Docker image:** includes llama.cpp (`b12193`, checksum-verified).
  - **Tested:** on CPU with real models: chat, streaming, structured output, tool calling, embeddings and search, the hosted-to-local switch, and crash restarts.
  - **Not yet tested:** the GPU and vLLM paths have not run on GPU hardware.

  (ADR 0041)
- **JavaScript handlers (Node.js runtime):**
  - **Turning it on:** `runtime: node` runs an app's handlers in Node.js, through the same worker protocol as Python.
  - **The SDK:** `@aiapp-server/server` has the Python SDK's features: models and agents with tools, KV, memory, vectors, SQL, jobs, durable workflows with approvals, events, plugin guardrails and spans. It ships inside the server.
  - **npm dependencies:** they come from the app's `package-lock.json` (`npm ci`) and are cached by lockfile.
  - **Starter:** `aiapp new node-app NAME`.
  - **Images:** the Docker images include Node 22; elsewhere, use `--node` or `AIAPP_NODE`.
  - **Conformance:** a suite runs the same tests against one app written in both languages.

  (ADR 0040)
- **npm package name:** the JS SDK is published as `@aiapp-server/client`; the `@aiapp` scope on npm belongs to someone else.

## v1.1.0 (2026-11-23)

Phase 1.x, the production hardening of v1.0. All nine milestones in the plan, ADRs 0031–0039.

### Platform
- **Evaluations:**
  - **Cases:** golden cases go in `evals/*.yaml`, with checks for contains and not-contains, regex, JSON fields, citations, latency, and a model judge.
  - **Running them:** `aiapp eval` runs them against the deployed app with its real models and stores each run. `--min-pass` and `--no-regress` turn it into a CI gate. `aiapp eval --history` lists past runs.
  - **Where results show:** the console's Evals tab and the `aiapp_eval_pass_rate` metric.
  - **Templates:** new knowledge-chat, document-extraction and classification apps include starter cases.

  (ADR 0031)
- **MCP gateway:**
  - **What it does:** apps publish their `tools.py` tools and routes (such as their chat) to MCP clients at `/apps/APP/mcp`, with `mcp_server:` in `ai-app.yaml`. Clients include Claude, Copilot and IDE agents.
  - **Protections:** each call goes through the app's keys or sign-in, roles, quotas and guardrails, and is audited, traced and counted. Tools that need a person's approval are never published.
  - **Commands:** `aiapp mcp APP` shows the endpoint, the tools and ready-to-paste client config.

  (ADR 0032)
- **Partitions and consumer groups:**
  - **Partitions:** `topics: { orders: { partitions: 4 } }` splits a topic by key. Each key keeps its order, and subscriptions handle partitions in parallel.
  - **Consumer groups:** `app.events.fetch(topic, group, member=…)` shares a topic's partitions among live members, and `app.events.ack(batch, group)` commits.
- **Dead letters:** `aiapp dead` lists, shows, replays (after a fix) and purges the records subscriptions gave up on. The console has a tab for them too.

  (ADR 0033)
- **External secrets:**
  - **References:** `${kv:NAME}` reads from Azure Key Vault and `${vault:MOUNT/PATH#KEY}` from HashiCorp Vault. They work wherever a secret name does, including `api_key_env: "vault:secret/hr#openai"`.
  - **Sign-in:** managed or workload identity, or a service principal, for Key Vault; a token, AppRole or Kubernetes auth for Vault.
  - **Caching:** values are cached for `AIAPP_SECRET_TTL` (5 minutes by default), and the last value keeps working if the vault goes down.
  - **Checking:** `aiapp secret test REF` checks a reference without showing its value.

  (ADR 0034)
- **Console sign-in:**
  - **Hosting:** the server can host the console at `/_console/`. Sign-in uses Entra ID or any OIDC provider, through the code flow with PKCE and a sealed session cookie.
  - **Roles:** viewer, auditor (adds the audit log), operator (adds replaying or purging dead letters, retrying or cancelling jobs, running cron and syncing sources) and admin. They are mapped from app roles or groups.
  - **Setup:** configure it in `console.yaml`, `--console-config` or Helm `console:`.
  - **Audit:** sign-ins and actions are recorded in the audit log.
  - **Local console:** `aiapp console` gets the same actions.
- **Audit export:**
  - **Destinations:** `audit-export.yaml` (or Helm `auditExport:`) sends the audit log to a SIEM over syslog (RFC 5424 over TCP, TLS or UDP), HTTP (JSON lines or Splunk HEC) and OTLP logs.
  - **Delivery:** records are sent in batches, retried, and counted.
  - **Privacy:** PII is redacted, and listed fields are dropped.
  - **Commands:** `aiapp audit` reads the log with filters, and `aiapp audit export` shows each sink's status.

  (ADR 0035)
- **Observability:**
  - **Spans from handlers:** `app.span("name", key=value)` adds a step to the request's trace. Spans nest, and model, storage and tool calls inside a span appear as its children.
  - **Trace context:** handlers get the request's trace context (`req.traceparent`), and `app.trace_headers()` passes it to services the handler calls.
  - **Jobs are traced:** ingestion jobs (per file: parse, embed, store) and connector syncs are traced.
  - **OTLP export:** with `OTEL_EXPORTER_OTLP_ENDPOINT` set, metrics and logs are exported over OTLP as well as traces.

  (ADR 0036)
- **Guardrail providers:**
  - **`presidio`:** redacts names, places and other entities with Microsoft Presidio (spaCy NER), running in the system worker.
  - **`azure-content-safety`:** checks text by harm category and severity, against custom blocklists, and with Prompt Shields. It signs in with a key or Entra ID.
  - **Job results and published records:** output guardrails can now check these too, with `jobs:` and `events:`. A blocked job fails without retries.

  (ADR 0037)
- **Auth and pages:**
  - **Page sign-in:** built-in pages sign people in with the OIDC code flow and PKCE when `auth.oidc.client_id` is set, with a sealed, app-scoped cookie session. Cross-site calls made with the cookie are refused.
  - **Token introspection:** opaque access tokens are validated through RFC 7662 introspection.
  - **Multi-tenant Entra apps:** a `{tenantid}` issuer and a `tenants:` allow-list are supported, and `tenant_isolation` keeps each tenant's KV, memory and vectors apart, jobs included.
  - **New flag:** `--public-url`.

  (ADR 0038)
- **Platform:**
  - **Windows memory limits:** a job object per worker (started suspended so the interpreter is inside it) caps its commit, and the memory watcher replaces workers over the limit, counting the whole job. Closing the job ends the worker.
  - **pytest fixtures:** `aiapp test --pytest` gets `aiapp_client`, `aiapp_models`, `aiapp_key` and `aiapp`.
  - **Console on the JS SDK:** the console is built on the new `ConsoleClient` in `@aiapp-server/client`.
  - **Browser tests:** Playwright tests cover the built-in pages, `<aiapp-chat>` and the console (`scripts/e2e-browser.sh`; in CI on tags and manual runs).

  (ADR 0039)
- **Docker image:** published to `ghcr.io/sandaal/aiapp-server` (amd64 and arm64) by the new publish workflow, which can also publish npm and VS Code once their tokens are set.

## v1.0.0 (2026-11-23)

The first production release (Phase 1).
- **Blueprints:** all ten.
- **Model gateway v2:** routing, budgets and a cache, with OpenAI, Azure OpenAI, Anthropic, Gemini, Bedrock and Ollama.
- **Connectors.**
- **Guardrails.**
- **Sign-in and roles.**
- **Versions with rollback,** and hot reload.
- **Tracing and metrics.**
- **SDKs:** a JS/TS SDK and web components, plus `aiapp test`.
- **Packaging:** Docker, Helm, azd and VS Code.
- **Isolation between apps.**
- **Builds** for Windows, macOS and Linux.

Install with the release's `install.sh` / `install.ps1`; see the [user guide](docs/user-guide.md). What was verified, and what wasn't: [exit criteria](docs/exit-criteria.md).

### Blueprints
- **Insights** (`aiapp new insights NAME`): ask questions about data in PostgreSQL, SQL Server or CSV files. The model writes the SQL, and the core runs it read-only, with one `SELECT`, row and time limits, and an optional table allow-list. The answer shows the queries and rows. (ADR 0023)
- **Code assistant** (`aiapp new code-assistant NAME`): questions about a codebase from a Git repository or a local folder. Code is indexed per function and type, and citations give file and lines (`pricing.py:11-16`). Any source can opt in with `code: true`.
- **Customer support** (`aiapp new customer-support NAME`): answers from your documents with citations, uses your tools, and lets sensitive actions (refunds) wait for a person's approval without blocking the chat. It can hand the conversation to a person through the `support.handoffs` topic. Uses the chat page. (ADR 0021)
- **Content** (`aiapp new content NAME`): a brief becomes an outline and a draft, which goes to human review on the approvals page. A rejection with comments produces a revised draft, and approved pieces are published to `content.approved`. Built-in page.
- **Meeting notes** (`aiapp new meeting-notes NAME`): upload a recording (up to 25 MB) or a transcript and get a summary, decisions, action items with owners and due dates, and open questions. Recordings are transcribed through the gateway. Built-in page. (ADR 0020)
- **Summarization** (`aiapp new summarization NAME`): summaries and key points of long documents. Documents are read in parts and the partial summaries are combined. A retried job keeps the parts it already finished. Styles: paragraph, bullets or executive. Built-in upload page. (ADR 0019)
- **Classification** (`aiapp new classification NAME`): sorts texts into labels defined in `ai-app.yaml`, and the reply is always one of them. Supports single and batch requests, optionally classifies every record on a topic, and can publish the results to another topic. Built-in page.

### Platform
- **Isolation between apps:**
  - **Memory:** workers over their memory limit are replaced (`aiapp quota set APP --worker-memory 1GB`, server default `--worker-memory 2GB`).
  - **Disk:** a single file can't grow past `--worker-max-file`, and each app's temporary files go to its own folder.
  - **Verified:** a noisy-neighbour test shows the other apps unaffected. See [exit criteria](docs/exit-criteria.md).
- **int8 vector quantization:** `aiapp serve --vector-quantization int8` stores vectors in a quarter of the memory, with scores within 0.002 of float.
- **Load tests and sizing:** `scripts/loadtest` and `scripts/e2e-load.sh` produce the measurements in the [sizing guide](docs/sizing.md). (ADR 0030)
- **Packaging:**
  - **Docker image:** a `Dockerfile` builds the server and the Python worker runtime in one image. It runs as a non-root user, keeps data and versions in `/data`, deploys apps under `/apps` at startup (`aiapp serve --apps-dir`), and checks itself with `aiapp health`.
  - **Helm chart:** `deploy/helm/aiapp-server` runs a single-replica StatefulSet with a PVC and a hardened pod, with options for ingress, metrics and a ServiceMonitor, secrets, the master key from a Secret, `gateway.yaml`, apps from ConfigMaps, and `helm test`.
  - **azd templates:** for Azure Container Apps (data on Azure Files NFS) and AKS (the Helm chart on Azure Disk), in `deploy/azd/`.

  (ADR 0029)
- **Editor support:**
  - **VS Code extension** (`editors/vscode`): new app from a blueprint, hot reload, tests, deploy with an environment picker, an apps and versions view with rollback, logs, traces and the console, plus completion and checks for `ai-app.yaml`.
  - **`aiapp schema`:** prints a JSON Schema for `ai-app.yaml`. `aiapp apps --json` and `aiapp versions --json` are new too.
  - **Copilot instructions:** new apps include `.github/copilot-instructions.md`.
- **Fix:** app files that are symlinks (Kubernetes ConfigMaps) are now included in versions.
- **Demo:** `scripts/poc.sh` is a 5-minute tour of the main features on local models.
- **JS/TS SDK and web components:**
  - **Client:** `@aiapp-server/client` (in `sdk/js/client`) handles streaming chat with citations, calls, uploads, approvals, typed errors and sign-in tokens.
  - **Web components:** every server serves `/_sdk/aiapp.js`, so one `<script>` tag gives a page `<aiapp-chat>`, `<aiapp-upload>` and `<aiapp-approvals>`.
  - **CORS:** a new `cors: { origins: [...] }` manifest setting lets pages on other origins use them.
- **`aiapp test`:**
  - **What it does:** it runs an app's `tests/` against a throwaway server, with every model answering from the test's script (`aiapp.testing`). Retrieval, guardrails, jobs and workflows all run for real.
  - **Templates:** new knowledge-chat, document-extraction and classification apps come with tests.

  (ADR 0028)
- **Observability:**
  - **Traces:** OpenTelemetry traces cover request, guardrail, handler, model, tool and storage spans, and include background jobs. They're exported over OTLP when `OTEL_EXPORTER_OTLP_ENDPOINT` is set, and recent ones are always kept in memory.
  - **`aiapp trace`:** `aiapp trace [APP]` lists recent requests, and `aiapp trace ID` shows one as a span tree with models and tokens.
  - **Metrics:** Prometheus `/metrics` with `aiapp serve --metrics-addr` covers requests, model calls, tokens, cost, cache hits, guardrail decisions, background runs and workers.
  - **Console:** `aiapp console` opens a read-only local console with apps, versions, request waterfalls, model usage, jobs, approvals, sources and quotas.

  (ADR 0027)
- **App lifecycle:**
  - **Immutable versions:** every deploy is a stored copy of the app folder, and folder edits don't reach the running app.
  - **History and rollback:** `aiapp versions` lists them, and `aiapp rollback [--to N|VERSION]` serves an earlier one with zero downtime.
  - **Environments:** `ai-app.prod.yaml` overlays with `aiapp deploy --env prod`, or a server default with `aiapp serve --env`.
  - **Hot reload:** `aiapp dev` redeploys on every save.
  - **Offline installs:** `aiapp wheelhouse DIR` and `aiapp serve --wheelhouse DIR` install requirements without internet access.
  - **Broken versions are rejected:** a new version whose handlers don't import is refused within seconds, and the old one keeps serving.
  - **Backups** include the version history.

  (ADR 0026)
- **Guardrails v2:**
  - **Built in:** `prompt-injection`, `blocked-topics`, `max-input`, `output-pii` (also on streamed answers) and `citations-required` (answers must cite a passage).
  - **Plugins:** guardrails can be written in Python (`handler: guards:check`, with `aiapp.guardrails`) or in Go (`guard.Register`).
  - **Dry run:** `guardrail_mode: dry-run`, or `dry_run: true` per entry, logs decisions without applying them.
  - **Audit:** every decision is audited without its text, and is readable through `/_logs`.
  - **Templates:** the knowledge-chat and customer-support templates now turn on `prompt-injection`.

  (ADR 0025)
- **Sign-in tokens and roles:** apps can accept OIDC access tokens (Microsoft Entra ID first) with `auth.oidc` in `ai-app.yaml`, alongside API keys. Routes can require roles (`roles: [refunds]`), provider groups map to app roles with `role_map`, and keys take any role (`aiapp key create APP --role read-logs`). `GET /apps/APP/_logs` serves model-call logs to `read-logs` callers. Handlers get `req.principal.has_role(...)`. (ADR 0024)
- **Connectors:** `sources:` can now sync from Git repositories, web pages and sitemaps, S3 (and S3-compatible) buckets, Azure Blob containers, PostgreSQL and SQL Server queries, and SharePoint or OneDrive libraries. They sync on a schedule, fetch only changed documents, and remove what was deleted upstream. See `aiapp sources` and `aiapp source sync`. (ADR 0022)
- **More document types:** PowerPoint (`.pptx`, per slide with notes), Excel (`.xlsx`, per sheet), HTML, CSV and email (`.eml`).
- **Speech-to-text:** `await app.models.transcribe.transcribe(audio, language="en", prompt="names")` with OpenAI, Azure OpenAI or OpenAI-compatible transcription models. Supports per-minute prices and budgets. Requests to apps can now be up to 26 MB.
- **Google Gemini and AWS Bedrock** providers (`provider: gemini` / `provider: bedrock`) support chat, streaming, tool calling, JSON-schema output and embeddings. `aiapp new --provider gemini|bedrock` scaffolds apps for them. They're tested against recorded protocol responses, not yet the live services. (ADR 0018)
- **Vision input:** `app.models.chat.complete("...", images=[png_bytes])`, and `images=` on `json()` for extracting data from photos and scans. Works with OpenAI, Azure, Anthropic, Gemini, Bedrock and OpenAI-compatible vision models.
- **Semantic cache** (opt-in per model): `semantic_cache: { embedding: embedding, threshold: 0.95 }` answers paraphrased questions from earlier answers within the same conversation context.
- **Model gateway v2:**
  - **Server model configuration:** operators describe deployments and logical models in `gateway.yaml`, and apps refer to them with `models: { chat: { use: chat } }`.
  - **Routing:** calls are spread across deployments by weight, with fallback tiers. A circuit breaker per deployment skips one that keeps failing.
  - **Cache:** exact repeats of `temperature: 0` calls are answered from memory, with no tokens billed.
  - **Budgets:** daily and monthly token and cost budgets per app and per API key, set with `aiapp quota set APP --daily-usd 5`. They're checked before each model call, and a refused call raises `ModelError("budget_exceeded")`.
  - **Commands:** `aiapp gateway` shows deployment health and cache stats, and `aiapp gateway reload` re-reads `gateway.yaml`.

  (ADR 0017)
- OpenAI-compatible models (Ollama, vLLM) are now reported as `openai-compatible/MODEL` in logs and prices instead of `openai/MODEL`.
- **Event topics:** `app.events.publish("orders", {...})` appends to an ordered, replayable topic, stored encrypted. Consume it in two ways:
  - **Subscriptions** in `ai-app.yaml` deliver each record to a handler in order, at least once. Failures are retried, and records that keep failing go to `TOPIC.dead`.
  - **Pull** with `app.events.fetch` and `commit`. Replay from an offset or a time with `app.events.read`.

  Retention is by age (default 7 days) and size. See `aiapp topics` and `aiapp publish`. (ADR 0016)
- **Cron:** `cron:` entries in the manifest run a job or a handler on a schedule. Each run is a durable job. Entries can have a timezone and a missed-run policy (`skip` or `run_once`). See `aiapp cron` and `aiapp cron run APP NAME`.
- **Data structures in `app.kv`:** hashes, lists, sets, sorted sets, counters, compare-and-set (`cas`) and leases with fencing tokens. Each structure can have a TTL, and every operation is atomic. They're encrypted like other app data, and member names are hashed inside storage keys. (ADR 0015)
- **Per-app quotas:** `aiapp quota set APP --storage 1GB --vectors 100k --workers 4 --concurrency 20` (or `--default` for all apps). Writes over the storage or vector quota fail with `QuotaExceeded`, and reads keep working. Deploys over the worker quota are refused. Requests over the concurrency limit get HTTP 429.
- **Windows is tested in CI.** The full test suite, including the race detector and real Python workers, runs on Windows, macOS and Linux for release tags and manual runs. (ADR 0014)
- Release binaries are built and attached to the GitHub release when a `v*` tag is pushed.

### Fixes
- **Vector search on clustered data:** some index builds missed whole groups of documents (recall@10 as low as 0.94). Neighbors are now chosen with the HNSW paper's heuristic, giving recall@10 of 1.000 at 100k vectors. The trade-off: building the index is about 2x slower, and search takes 2.5 ms instead of 1.9 ms. (ADR 0005)
- A request that reached a worker just as it started could fail with "not connected to the core". Workers now wait until they have registered with the core.

## v0.5.0 (2026-11-22)

v0.5 adds two blueprints beside knowledge chat, durable storage and jobs, tool use and human approvals. It's meant for design partners trying it on real problems.

### Blueprints
- **Document extraction** (`aiapp new document-extraction NAME`): upload PDF, Word or text documents through the API or the built-in upload page, and get the fields defined in `schema.json` back, each with the page and quote it came from. Each upload runs as a durable job. (ADR 0010)
- **Workflow agent** (`aiapp new workflow-agent NAME`): give it a task and it works through it with your Python tools (`tools.py`) and MCP servers. Tools listed under `agent.approval_required` wait for a person: `aiapp approve` on the command line, or `/apps/NAME/_approvals/` in a browser with an approver key. Every model turn, tool call and approval is saved and returned with the result. (ADR 0013)
- **Knowledge chat** now uses hybrid search (meaning plus keywords) by default, so exact terms such as product or policy codes are found.

### Platform
- **Vector index:** HNSW for large collections (about 2 ms per query and recall@10 of 0.98 at 100k vectors) and in-index BM25 keyword search, merged by reciprocal rank fusion. Search mode is `vector`, `keyword` or `hybrid`. (ADR 0005, 0006)
- **Encryption at rest:** each app's KV values, files and vector data are encrypted with that app's own key (AES-256-GCM), and those keys are protected by the server's master key. (ADR 0007)
- **Backup and restore:** `aiapp backup DIR` makes a consistent copy of a running server, with checksums; `aiapp restore` verifies it and rebuilds the server into a new data directory. The master key is left out unless you pass `--include-key`.
- **Deployments survive restarts.** Apps that were deployed come back when the server starts.
- **Durable jobs:** declare jobs under `jobs:` and queue them with `app.jobs.enqueue`. Failed jobs are retried with backoff, jobs that keep failing are moved to a dead-letter state, and duplicates are prevented with idempotency keys. Jobs survive a crash or restart. `aiapp jobs` shows them, and you can retry or cancel them from there. Document ingestion runs as jobs too. (ADR 0008)
- **Structured output:** `app.models.x.json(prompt, schema=...)` returns JSON that matches the schema. The core checks it and asks the model again once if it doesn't. (ADR 0009)
- **Tools and MCP:** write tools as `@app.tool` Python functions, or connect MCP servers (stdio or streamable HTTP) under `mcp:` with per-app allow-lists. Tool calls work the same way with OpenAI, Azure OpenAI, Anthropic and OpenAI-compatible models. (ADR 0011)
- **Workflows and approvals:** `@app.workflow` with `wf.step` (each result is saved, so finished steps are not repeated after a restart or retry) and `wf.approval` (the job pauses until someone decides, or the approval times out). API keys can have an `approver` role. (ADR 0012)

### Upgrade notes
- Ingested files inside an app folder are now identified by their path relative to that folder. Before, a restored or moved app was indexed a second time. On the first deploy after upgrading, each source file is embedded once more and its old chunks are removed.
- Data written by v0.1 is not encrypted. Start v0.5 with a fresh data directory and redeploy your apps.

### Known limitations
- Small local models (tested with `llama3.2:3b`) sometimes skip tools. In one run, the agent told the customer a refund had been made without calling the refund tool. An approval only covers tools the model actually calls, so use a capable tool-calling model for agents, and check the run history.
- Real-model checks for this release used local Ollama models. The Anthropic and OpenAI providers are covered by protocol tests, but they were not run against the live APIs this cycle.
- Scanned PDFs need OCR, which is not supported yet. The HNSW index has no background compaction yet. An agent runs the tool calls from one model turn one at a time.
- Backups go to local folders only. There are no scheduled or object-storage backups yet, and no master-key rotation.

### Verified
`scripts/e2e-blueprints.sh` builds the server on a fresh data directory and checks all three blueprints with local models. It then backs up the server, restores it into a new data directory, restarts it and checks the restored chat, extraction result and agent run: 11 of 11 checks passed.

## v0.1 (Phase 0)
The knowledge-chat blueprint: `aiapp new`, `aiapp deploy`, ingestion of Markdown, text, PDF and Word files, streaming chat with citations, the PII-redaction guardrail, API keys, rate limits, audit logs and the chat widget.
