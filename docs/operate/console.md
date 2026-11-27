# The console

A web view of the server: apps, versions, recent requests (with step-by-step traces), model calls and cost, jobs, topics, dead letters, cron, sources, evals, quotas, the model gateway and the audit log.

## On the server machine

```bash
aiapp console
```

It opens a browser at a private local address (`http://127.0.0.1:PORT/RANDOM-TOKEN/`). Only this machine can open it. From it you can also **replay or purge dead letters, retry or cancel jobs, run cron entries and sync sources**.

## Hosted console with sign-in

For your team, the server can host the console at `https://YOUR-HOST/_console/` with sign-in through Entra ID or any OIDC provider.

1. **Register an app** in Entra ID with the **Web** redirect URI `https://YOUR-HOST/_console/callback`, and create app roles `AIApp.Viewers`, `AIApp.Auditors`, `AIApp.Operators`, `AIApp.Admins`. Assign people or groups.
2. **Create `console.yaml`** in the data folder (or pass `--console-config FILE`; on Kubernetes set `console:` in the Helm values):

    ```yaml
    public_url: https://ai.example.com
    oidc:
      issuer: https://login.microsoftonline.com/TENANT_ID/v2.0
      client_id: APP_REGISTRATION_CLIENT_ID
      client_secret_env: CONSOLE_CLIENT_SECRET    # aiapp secret set CONSOLE_CLIENT_SECRET
    roles:                                        # app roles (or groups with roles_claim: groups)
      AIApp.Viewers: viewer
      AIApp.Auditors: auditor
      AIApp.Operators: operator
      AIApp.Admins: admin
    session: 8h
    ```

3. **Restart the server** and open `https://ai.example.com/_console/`.

| Role | Can |
|---|---|
| `viewer` | see everything the local console shows |
| `auditor` | viewer, plus the server-wide audit log and export status |
| `operator` | viewer, plus replay/purge dead letters, retry/cancel jobs, run cron, sync sources |
| `admin` | all of the above |

**Never reachable from the console**, whatever the role: keys, secrets, deploys, backups and quota changes. They stay on the CLI. Every sign-in and action is recorded in the [audit log](audit.md).

## Script the console API

The console's API is also available to scripts through `ConsoleClient` in the JS SDK (`@sandaal/ai-app-server-client`).
