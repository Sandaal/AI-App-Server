# Run on Azure

Two [Azure Developer CLI (azd)](https://learn.microsoft.com/azure/developer/azure-developer-cli/) templates are in the [public repository](https://github.com/Sandaal/aiapp-server/tree/main/deploy/azd), folder `deploy/azd/`:

| Template | What it creates |
|---|---|
| `container-apps` | Azure Container Apps, with data on an Azure Files **NFS** share |
| `aks` | AKS with the Helm chart, data on an Azure Disk |

## Steps

1. Push the server image to your registry (or use `ghcr.io/sandaal/aiapp-server:1.1`).
2. `git clone https://github.com/Sandaal/aiapp-server.git`, then put your app folders in the template's `apps/` folder (`deploy/azd/container-apps/apps/` or `deploy/azd/aks/apps/`).
3. Read the template's `azure.yaml`, then:

```bash
azd up
```

## Use Azure services from your apps

| Need | How |
|---|---|
| Azure OpenAI | `provider: azure-openai` in the app, with `AZURE_OPENAI_ENDPOINT` and a key or the server's managed identity, see [Model providers](models.md) |
| Keys in Key Vault | `api_key_env: "kv:openai-key"`, see [Secrets and vaults](../operate/secrets.md) |
| Sign-in with Entra ID | [Sign-in](../operate/sign-in.md) |
| Harmful content checks | the `azure-content-safety` [guardrail](../build/guardrails.md) |
| Monitoring | send OpenTelemetry to Azure Monitor, see [Monitoring](../operate/monitoring.md) |

!!! danger "Storage must be NFS or a disk"
    Don't put the data on SMB file shares (such as App Service storage mounts): the embedded database needs NFS or block storage.
