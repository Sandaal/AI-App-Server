# Monitoring

## Health

```bash
aiapp health                               # for scripts and health checks
curl http://127.0.0.1:8080/health
```

## Prometheus metrics

```bash
aiapp serve --metrics-addr 127.0.0.1:9464     # or AIAPP_METRICS_ADDR; Helm: metrics.enabled
```

Metrics include requests and latency per app and route, model calls, tokens and cost, cache hits, guardrail decisions, tool calls, background jobs, workers (ready, restarts), evals pass rate, MCP calls and audit export. All are prefixed `aiapp_`.

## OpenTelemetry (traces, metrics, logs)

Point the server at an OpenTelemetry Collector or a backend that accepts OTLP over HTTP (Jaeger, Grafana Tempo/Loki/Mimir, Datadog, Honeycomb, Azure Monitor…):

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318
aiapp serve
```

| Variable | Effect |
|---|---|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | all three signals |
| `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` (and `_METRICS_`, `_LOGS_`) | one signal |
| `OTEL_TRACES_EXPORTER=none` (and `METRICS`, `LOGS`) | turn one off |
| `OTEL_EXPORTER_OTLP_HEADERS` | e.g. `api-key=…` for hosted backends |
| `OTEL_METRIC_EXPORT_INTERVAL` | milliseconds, default 60000 |

**What a trace shows:** the request, guardrails, your handler and your own [spans](../build/tracing.md), every model call (model, tokens, cost), storage and tool calls. Background jobs, ingestion (each file's parse, embed and store) and connector syncs are traced too. Callers' W3C `traceparent` headers are continued.

## Without any backend

`aiapp trace`, `aiapp logs` and the [console](console.md) show recent traces and model calls, kept in memory since the server started.

## Logs

The server writes JSON logs to stderr: the terminal, `journalctl -u aiapp`, `docker logs`, or `kubectl logs`. `--log-level debug|info|warn|error`. Logs never contain prompts or answers.
