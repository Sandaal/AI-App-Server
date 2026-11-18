# AI App Server

An application server for AI. Developers build AI apps in **Python** and **JavaScript/TypeScript**, deploy them like web apps, and the server provides every runtime service those apps need: model access, memory, cache, events, vectors, security, guardrails, observability and deployment, in one binary that runs on any hardware.

> Status: Phase 0 in progress. Milestone M0.1 (server skeleton) is in place.

## Initial goal
Deploy the top 10 AI use cases in minutes through built-in blueprints.

```bash
aiws new knowledge-chat my-hr-bot
aiws source add ./hr-policies/
aiws deploy
```

## Try the skeleton
Requires Go 1.24+ (Linux or macOS).

```bash
go build -o bin/aiws ./core/cmd/aiws
./bin/aiws serve --data-dir ./data      # public API on 127.0.0.1:8080
curl 127.0.0.1:8080/health
./bin/aiws apps --data-dir ./data       # CLI talks to the server over a local socket
```

## Repository layout
| Path | Contents |
|---|---|
| `core/` | Server core (Go): request pipeline, storage, data plane, HAL |
| `sdk/python/` | Python SDK and worker runtime for server-side apps |
| `sdk/js/` | JavaScript/TypeScript client SDK and UI components |
| `blueprints/` | Top-10 use-case app templates |
| `cli/` | `aiws` command-line tool |
| `docs/` | Strategy, architecture and decision records |

## Key decisions
- Server core in Go; apps in Python (v1) and JS/TS (front end; Node workers in v2)
- Built-in tiered storage and a Redis-like + Kafka-like data plane
- Runs fully on standard servers; uses next-generation AI hardware when present
- Independent: no dependency on any vendor agent framework; provider- and hardware-neutral

See [docs/strategy.md](docs/strategy.md) for the full product strategy, [docs/design/phase0.md](docs/design/phase0.md) for the Phase 0 design, and [docs/adr/](docs/adr/) for decision records.

## License
Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE). Contributions are welcome; see [CONTRIBUTING.md](CONTRIBUTING.md).
