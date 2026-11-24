# Secrets and vaults

## Secrets stored by the server

```bash
aiapp secret set OPENAI_API_KEY        # asks for the value; stored encrypted
aiapp secret list                      # names only
aiapp secret delete OPENAI_API_KEY
```

Apps use them by name: `api_key_env: OPENAI_API_KEY` on a model, or `${OPENAI_API_KEY}` in connector and MCP settings. Environment variables of the server work the same way.

## Azure Key Vault

```bash
export AZURE_KEY_VAULT_URL=https://contoso-ai.vault.azure.net
```

```yaml
models:
  chat: { provider: openai, model: gpt-4o-mini, api_key_env: "kv:openai-key" }     # a Key Vault secret
sources:
  - { name: docs, git: { url: "https://github.com/contoso/docs", token: "${kv:github-token}" } }
```

`kv:NAME/VERSION` pins a version. The server signs in with, in this order: AKS workload identity, a service principal (`AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`), or managed identity (App Service, Container Apps, VMs). Give that identity the *Key Vault Secrets User* role.

## HashiCorp Vault

```bash
export VAULT_ADDR=https://vault.internal:8200
export VAULT_TOKEN=...                     # or VAULT_ROLE_ID + VAULT_SECRET_ID (AppRole), or VAULT_K8S_ROLE (Kubernetes)
export VAULT_NAMESPACE=team-a              # Enterprise / HCP only
```

```yaml
models:
  chat: { provider: openai, model: gpt-4o-mini, api_key_env: "vault:secret/hr-bot#openai" }   # MOUNT/PATH#KEY
```

KV v2 and v1 engines both work.

## Rotation and outages

- Values are cached for `AIAPP_SECRET_TTL` (default `5m`).
- If the vault can't be reached, the last value keeps working.
- Apps read keys when they are deployed: after rotating a key, redeploy the app (or restart the server).

## Check a reference

```bash
aiapp secret test vault:secret/hr-bot#openai
# vault:secret/hr-bot#openai resolves from HashiCorp Vault (51 characters; the value is not shown)
```
