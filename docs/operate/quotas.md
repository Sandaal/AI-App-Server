# Quotas and limits

Quotas keep one app from hurting the others.

```bash
aiapp quota hr-bot                     # current limits and usage
aiapp quota set hr-bot --storage 2GB --vectors 500k --concurrency 50 --worker-memory 1GB --daily-usd 20
```

| Limit | What happens at the limit |
|---|---|
| `--storage` | writes fail with `QuotaExceeded`; reads still work |
| `--vectors` | adding more chunks fails (indexing reports it) |
| `--concurrency` | requests over the limit get `429 too_many_concurrent_requests` with `Retry-After: 1` |
| `--workers` | the most workers the app may ask for |
| `--worker-memory` | a worker using more is replaced (the app keeps serving) |
| `--daily-usd`, `--monthly-usd`, `--daily-tokens`, `--monthly-tokens` | model calls answer `budget_exceeded` until the period resets (UTC) |

**Per key:** add `--key KEY_ID` to give one API key its own budget on top of the app's, for example `aiapp quota set hr-bot --key k_123 --daily-usd 2`. `aiapp quota set --default …` sets the limits for apps without their own.

## Server-wide limits

| Setting | Default |
|---|---|
| `aiapp serve --worker-memory` | 2 GB per worker (Linux, macOS, Windows) |
| `aiapp serve --worker-max-file` | 1 GB per file a worker writes (Linux, macOS) |
| `rate_limit:` in an app | requests per minute per client |
| `job_concurrency:` in an app | background jobs running at once |

## Sizing

- One app served 75–95 streamed answers per second with no errors in measurements; the server adds almost nothing to the model's own time.
- Memory: about 2 GB for a few small apps. Large document sets: vectors switch to int8 by themselves when they outgrow a quarter of memory (see [Hardware](hardware.md)); `--vector-quantization int8` forces it.
- Workers: `workers:` in each app (default 2) sets how many Python processes serve it.
