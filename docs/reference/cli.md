# Commands

`aiapp help` lists them all. Commands other than `serve` talk to the server on the same machine through `DATA_DIR/admin.sock`; pass `--data-dir` (or set `AIAPP_DATA_DIR`) when the server uses another data folder. In an app folder, the app name is optional.

## Server

```
aiapp serve [--addr 127.0.0.1:8080] [--data-dir ~/.aiapp] [--apps-dir DIR] [--env prod]
            [--public-url https://ai.example.com] [--metrics-addr 127.0.0.1:9464]
            [--worker-memory 2GB] [--worker-max-file 1GB] [--vector-quantization int8]
            [--python PATH] [--wheelhouse DIR] [--log-level info]
            [--gateway FILE] [--console-config FILE] [--audit-export FILE]
aiapp health                          check the server answers
aiapp version
```

## Apps

| Command | What it does |
|---|---|
| `aiapp new BLUEPRINT NAME [--provider P]` | create an app from a [blueprint](../build/blueprints.md); providers `openai`, `azure-openai`, `anthropic`, `gemini`, `bedrock`, `ollama` |
| `aiapp deploy [DIR] [--env prod]` | deploy a new version (zero downtime) |
| `aiapp dev [DIR]` | serve the folder and redeploy on every save |
| `aiapp apps [--json]` | list deployed apps |
| `aiapp remove APP` | remove an app |
| `aiapp versions [APP]` · `aiapp rollback [APP] [--to N\|VERSION]` | [versions](../operate/versions.md) |
| `aiapp schema` | JSON Schema for `ai-app.yaml` |

## Documents

| Command | |
|---|---|
| `aiapp source add PATH` | add a file or folder to the app and index it |
| `aiapp sources [APP]` | connector status |
| `aiapp source sync APP [NAME]` | sync connectors now |

## Test and inspect

| Command | |
|---|---|
| `aiapp test [DIR] [-k NAME] [--pytest] [-v]` | run `tests/` with scripted models |
| `aiapp eval [DIR] [--min-pass 0.9] [--no-regress] [--history]` | golden cases with real models |
| `aiapp logs [APP] [--limit 20]` | recent model calls: tokens, cost, latency |
| `aiapp trace [APP]` · `aiapp trace ID` | recent requests and jobs; one as a tree |
| `aiapp console` | the web console on this machine |
| `aiapp mcp [APP]` | what the app publishes to MCP clients, and client config |

## Jobs, events, approvals

| Command | |
|---|---|
| `aiapp jobs [APP] [--state dead]` · `aiapp jobs show\|retry\|cancel APP ID` | background jobs |
| `aiapp cron [APP]` · `aiapp cron run APP NAME` | schedules |
| `aiapp topics [APP] [TOPIC]` · `aiapp publish APP TOPIC JSON` | event topics and lag |
| `aiapp dead [APP]` · `aiapp dead show\|replay\|purge APP TOPIC.dead` | dead letters |
| `aiapp approvals [APP]` · `aiapp approve\|reject APP ID` | workflow approvals |

## Security and limits

| Command | |
|---|---|
| `aiapp secret set\|list\|delete NAME` · `aiapp secret test REF` | [secrets](../operate/secrets.md) |
| `aiapp key create APP [--name N] [--role R]...` · `list APP` · `revoke APP ID` | [API keys](../operate/keys.md) |
| `aiapp quota [APP]` · `aiapp quota set APP\|--default ...` | [quotas](../operate/quotas.md) |
| `aiapp audit [--app A] [--type T] [--subject S] [--since 24h] [--json]` · `aiapp audit export` | [audit log](../operate/audit.md) |
| `aiapp gateway [reload]` | model deployments, health, cache; re-read `gateway.yaml` |

## Backups and offline

| Command | |
|---|---|
| `aiapp backup DIR [--include-key]` | consistent copy of a running server |
| `aiapp restore BACKUP_DIR --data-dir DIR` | into an empty data folder, server stopped |
| `aiapp wheelhouse DIR [APP_DIR...]` | download Python packages for [offline servers](../install/offline.md) |
