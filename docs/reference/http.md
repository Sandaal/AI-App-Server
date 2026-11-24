# HTTP endpoints

| Endpoint | What |
|---|---|
| `GET /health` | `200` when the server is up |
| `GET /version` | the server version |
| `POST /apps/APP/ROUTE` | an app's routes (JSON, uploads, or Server-Sent Events for streaming routes) |
| `GET /apps/APP/` | the app's page (`ui:`), or its own files from `ui: ./ui` |
| `POST /apps/APP/v1/chat/completions` | chat apps as an OpenAI-compatible chat model |
| `POST /apps/APP/mcp` | the app as an MCP server (`mcp_server:`) |
| `/apps/APP/_approvals/` | approvals page and API (role `approver`) |
| `GET /apps/APP/_logs` | the app's model-call log (role `read-logs`) |
| `/apps/APP/_auth/login`, `callback`, `logout`, `me` | page sign-in (`auth.oidc.client_id`) |
| `GET /_sdk/aiapp.js` | the JS client and web components |
| `/_console/` | the hosted console (`console.yaml`) |

Metrics are on a separate address: `--metrics-addr` serves `GET /metrics`.

## Request headers

| Header | |
|---|---|
| `Authorization: Bearer …` | an API key or an access token (`X-API-Key` also works for keys) |
| `X-Session-Id` | keeps a conversation (memory) across requests |
| `traceparent` | continue your trace (W3C) |

## Response headers

| Header | |
|---|---|
| `X-Invocation-Id` | the request's id: `aiapp trace ID` |
| `Retry-After` | with `429`, seconds to wait |

## Streaming format

Streaming routes answer `text/event-stream`:

```
data: You get 25 days
data:  of leave [1].

event: end
data: {"citations":[{"n":1,"source":"leave-policy.pdf","page":"2"}]}
```

An `event: replace` means a guardrail changed the answer: replace what you showed with its data.

## Errors

JSON with `error` (a code) and usually `message`:

| Status | `error` | |
|---|---|---|
| 400 | guardrail name, `bad_request` | refused by a guardrail, or a bad request |
| 401 | `invalid_api_key`, `invalid_token` | missing or bad credentials |
| 403 | `forbidden`, `cross_site_request` | missing role; cookie request from another site |
| 404 | `route not found` | |
| 429 | `rate_limited`, `too_many_concurrent_requests` | slow down |
| 503 | `workers are not running`, … | the app is starting, or a dependency is down |
