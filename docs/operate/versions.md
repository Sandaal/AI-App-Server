# Versions and rollback

Every `aiapp deploy` creates a new, immutable version of the app.

- New workers must start and pass a health check **before** traffic switches to them.
- A broken version (code that doesn't load, a bad manifest) is refused, and the old version keeps serving.
- Requests in progress finish on the old workers.

```bash
aiapp versions hr-bot          # all versions, which one serves, when each last served
aiapp rollback hr-bot          # back to the previous version
aiapp rollback hr-bot --to 3   # to version number 3 (or a version label: --to 1.2.0)
```

Rollback is instant and has no downtime. Documents, memory and other data are not rolled back; only the app's code and settings.

## Environments

`aiapp deploy --env prod` merges `ai-app.prod.yaml` over `ai-app.yaml`. A server started with `--env prod` (or `AIAPP_ENV=prod`) uses that overlay for apps it deploys from `--apps-dir`.

## Deploy at server start

`aiapp serve --apps-dir /etc/aiapp/apps` (Docker: `/apps`) deploys every folder with an `ai-app.yaml` when the server starts, which suits images and Kubernetes.
