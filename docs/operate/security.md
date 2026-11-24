# Security checklist

The server starts safe: it listens on `127.0.0.1` only, and the CLI works only on the server machine. Before others can reach it, go through this list.

## Before opening it to the network

- [ ] **Every app requires credentials:** [API keys](keys.md) or [sign-in](sign-in.md). Apps with neither are open to anyone who can reach them; the server warns about them at start.
- [ ] **HTTPS in front:** a reverse proxy (nginx, IIS, Caddy) or a Kubernetes ingress with TLS. Then listen on the network with `--addr 0.0.0.0:8080`, or keep `127.0.0.1` behind a local proxy.
- [ ] **The master key is backed up** separately from the data, and on Kubernetes kept in a Secret. See [Backups](backups.md).
- [ ] **The data folder is protected:** only the account running the server can read it. It holds the encrypted data, the master key and the admin socket that the CLI uses.
- [ ] **Provider keys are secrets,** not in app files: `aiapp secret set`, or a [vault](secrets.md).
- [ ] **Guardrails** fit each app: at least `pii-redaction` and `prompt-injection` for apps used by the public. See [Guardrails](../build/guardrails.md).
- [ ] **Quotas** on each app, so one can't use all the storage, memory or budget. See [Quotas](quotas.md).
- [ ] **CORS** lists only your own sites (`cors.origins`).
- [ ] **Audit export** to your SIEM, if you have one. See [Audit log](audit.md).

## What the server does for you

| Area | Protection |
|---|---|
| Data at rest | everything encrypted with keys derived from the master key: documents, vectors, memory, jobs, events, secrets, the audit log |
| Logs and traces | never contain prompts or answers; only names, ids, sizes and timings |
| Apps | each runs in its own Python processes with memory and file-size limits; apps can't read each other's data |
| Deploys | a new version must start and pass a health check before it serves; a broken version is refused |
| Admin | the CLI and the local console use a socket in the data folder, not the network; the hosted console can't reach keys, secrets, deploys or backups |
| Sign-in | tokens are verified (signature, issuer, audience, expiry); page sign-in uses PKCE and sealed cookies, with CSRF protection |
| Model calls | personal data can be redacted before it leaves (`pii-redaction`, `presidio`) |

## Reporting a vulnerability

Please report security issues privately through GitHub's *Report a vulnerability* on the [repository](https://github.com/Sandaal/ai-app-server/security), not in public issues.
