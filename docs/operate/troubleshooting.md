# Troubleshooting

| Symptom | What to check |
|---|---|
| `server not running: cannot reach …/admin.sock` | Start `aiapp serve`, or point the CLI at its data folder with `--data-dir` or `AIAPP_DATA_DIR`. For the Linux service: `sudo -u aiapp AIAPP_DATA_DIR=/var/lib/aiapp aiapp …`. |
| `uv not found; workers use python3 from PATH`, apps don't start | Install [uv](https://docs.astral.sh/uv/), or Python 3.10+ with `grpcio`, `protobuf` and `pypdf`. |
| Deploy says `new version … did not become ready` | The app's Python fails to load. The message and the server log show the error; the previous version keeps serving. Try `aiapp dev` to see errors as you save. |
| `401 invalid_api_key` | The app has keys or sign-in: send `Authorization: Bearer KEY`. |
| `403 forbidden` | The key or user lacks a role the route needs (`roles:`). |
| `403 cross_site_request` | A page signed in with a cookie called the app from another site. Call from the app's own pages, or use a token. |
| `429 rate_limited` | Raise `rate_limit:` in the manifest or the concurrency quota. |
| `budget_exceeded` in answers | `aiapp quota APP` shows budgets; raise them with `aiapp quota set`. |
| The answer says the documents don't cover it | `aiapp sources` and `aiapp jobs` show indexing; check the files were added (`aiapp source add`) and deployed. Scanned PDFs need OCR. |
| A guardrail refuses normal messages | Set `guardrail_mode: dry-run`, look at `aiapp audit --type guardrail`, tune it. |
| Chat answers arrive all at once | A proxy buffers: nginx `proxy_buffering off`; ingress-nginx annotation `proxy-buffering: "off"`. |
| A model provider fails | `aiapp gateway` shows each deployment's health; `aiapp logs APP` shows errors. Add a `fallback:`. |
| `presidio is not installed` | `pip install presidio-analyzer presidio-anonymizer && python -m spacy download en_core_web_sm` in the server's Python. |
| A secret reference doesn't work | `aiapp secret test kv:NAME` (or `vault:…`) shows where it resolves from. |
| Windows: memory limits not enforced | The server warns about Microsoft Store Python: install Python from python.org or uv. |
| Where are the logs? | The server's JSON logs go to stderr (terminal, `journalctl -u aiapp`, `docker logs`). Model calls: `aiapp logs`. Requests: `aiapp trace`. |

## Get help

1. Find the request's id in the `X-Invocation-Id` response header, and run `aiapp trace ID`.
2. Collect `aiapp version`, the error message and the server log lines around it.
3. Open an issue on [GitHub](https://github.com/Sandaal/aiapp-server/issues), without keys, prompts or personal data.
