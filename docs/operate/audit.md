# Audit log and SIEM

The server keeps an encrypted audit log of what happens, without prompts or answers:

| Record type | Written when |
|---|---|
| `model_chat`, `model_embed`, … | a model is called: app, model, tokens, cost, duration, key |
| `guardrail` | a guardrail redacts or blocks (and why) |
| `tool_call`, `mcp_call` | a tool runs, or an MCP client calls the app |
| `console_login`, `console_action` | someone signs in to the hosted console, or acts in it |

## Read it

```bash
aiapp audit                                   # newest first
aiapp audit --app hr-bot --type model_ --since 24h
aiapp audit --subject oidc:1f2e... --json     # one person; JSON lines
aiapp logs hr-bot                             # just one app's model calls
```

The console's *Audit log* view shows it to `auditor` and `admin` roles.

## Send it to your SIEM

Create `audit-export.yaml` in the data folder (or pass `--audit-export FILE`; Helm: `auditExport:`), then restart:

```yaml
sinks:
  - { name: siem, type: syslog, address: "siem.internal:6514", network: tls }       # RFC 5424 (tcp, tls or udp)
  - { name: splunk, type: http, url: "https://splunk:8088/services/collector", format: splunk,
      headers: { Authorization: "Splunk ${vault:secret/siem#hec}" } }
  - { name: elastic, type: http, url: "https://logs.example.com/ingest" }             # JSON lines
  - { name: otel, type: otlp, endpoint: "http://otel-collector:4318" }               # OpenTelemetry logs
exclude: [key]          # fields never exported
redact_pii: true        # default
```

| Type | Works with |
|---|---|
| `syslog` | QRadar, ArcSight, rsyslog, Sentinel via the AMA syslog connector |
| `http`, `format: splunk` | Splunk HTTP Event Collector |
| `http` (JSON lines) | Elastic, Logstash, Fluent Bit, Vector, any webhook |
| `otlp` | OpenTelemetry Collector, Grafana Loki, Datadog, Azure Monitor |

- **Personal data** in exported records is redacted; the local log keeps the full record.
- **When a SIEM is down**, records are retried; if its queue fills up, the copy is dropped (never the local record) and counted.
- **Check delivery:** `aiapp audit export`, or the metric `aiapp_audit_export_records_total`.
