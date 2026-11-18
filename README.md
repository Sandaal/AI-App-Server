# AI App Server

An application server for AI. Developers build AI apps in **Python** and **JavaScript/TypeScript**, deploy them like web apps, and the server provides every runtime service those apps need: model access, memory, cache, events, vectors, security, guardrails, observability and deployment, in one binary that runs on any hardware.

> Status: Phase 0 in progress. Built: server skeleton (M0.1), model gateway (M0.3), blob store, vector index and log store (part of M0.4). Next: YAML manifests, worker protocol (M0.2), Pebble KV.

## Initial goal
Deploy the top 10 AI use cases in minutes through built-in blueprints.

```bash
aiapp new knowledge-chat my-hr-bot
aiapp source add ./hr-policies/
aiapp deploy
```

## Try the skeleton
Requires Go 1.24+ (Linux or macOS).

```bash
go build -o bin/aiapp ./core/cmd/aiapp
./bin/aiapp serve --data-dir ./data      # public API on 127.0.0.1:8080
curl 127.0.0.1:8080/health
./bin/aiapp apps --data-dir ./data       # CLI talks to the server over a local socket
```

## Repository layout
| Path | Contents |
|---|---|
| `core/` | Server core (Go): request pipeline, storage, data plane, HAL |
| `sdk/python/` | Python SDK and worker runtime for server-side apps |
| `sdk/js/` | JavaScript/TypeScript client SDK and UI components |
| `blueprints/` | Top-10 use-case app templates |
| `cli/` | `aiapp` command-line tool |
| `docs/` | Strategy, architecture and decision records |

## Key decisions
- Server core in Go; apps in Python (v1) and JS/TS (front end; Node workers in v2)
- Built-in tiered storage and a Redis-like + Kafka-like data plane
- Runs fully on standard servers; uses next-generation AI hardware when present
- Independent: no dependency on any vendor agent framework; provider- and hardware-neutral

See [docs/roadmap.md](docs/roadmap.md) for the delivery plan, [docs/strategy.md](docs/strategy.md) for the full product strategy, [docs/design/](docs/design/) for the phase designs (0–3), and [docs/adr/](docs/adr/) for decision records.

## License
Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE). Contributions are welcome; see [CONTRIBUTING.md](CONTRIBUTING.md).
