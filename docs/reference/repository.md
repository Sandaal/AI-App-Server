# The public repository

**https://github.com/Sandaal/ai-app-server** has everything you need to install, build on and run AI App Server.

| Folder or page | What's there | Use it to… |
|---|---|---|
| [Releases](https://github.com/Sandaal/ai-app-server/releases) | the server for Windows, macOS and Linux, the installers, the VS Code extension, `SHA256SUMS`, release notes | [install](../install/index.md) or upgrade |
| [`apps/`](https://github.com/Sandaal/ai-app-server/tree/main/apps) | complete, tested apps for ten use cases | start a new app from the closest one ([guide](../build/examples.md)) |
| [`apps/examples/`](https://github.com/Sandaal/ai-app-server/tree/main/apps/examples) | one small app per extension point: routes, tools, workflows, guardrails, events, connectors, web pages, a customized blueprint | learn how to add a feature |
| [`sdk/python/`](https://github.com/Sandaal/ai-app-server/tree/main/sdk/python/aiapp) | the Python SDK your apps import (`from aiapp import app`) | read exactly what each call does |
| [`sdk/python/aiapp/blueprints/`](https://github.com/Sandaal/ai-app-server/tree/main/sdk/python/aiapp/blueprints) | how each of the ten blueprints works | [change a blueprint's code](../build/customize-blueprints.md) |
| [`sdk/js/`](https://github.com/Sandaal/ai-app-server/tree/main/sdk/js) | the JavaScript client, the web components and the built-in pages | [put AI on your pages](../build/web.md) or [call apps from code](../build/clients.md) |
| [`deploy/helm/`](https://github.com/Sandaal/ai-app-server/tree/main/deploy/helm/aiapp-server) | the Helm chart | [run on Kubernetes](../install/kubernetes.md) |
| [`deploy/azd/`](https://github.com/Sandaal/ai-app-server/tree/main/deploy/azd) | Azure Container Apps and AKS templates | [run on Azure](../install/azure.md) |
| [`deploy/systemd/`](https://github.com/Sandaal/ai-app-server/tree/main/deploy/systemd) | the Linux service unit | [run as a service](../install/linux.md) |
| [`schema/`](https://github.com/Sandaal/ai-app-server/tree/main/schema) | the `ai-app.yaml` JSON Schema | editor completion ([VS Code](../build/vscode.md)) |
| [`docs/`](https://github.com/Sandaal/ai-app-server/tree/main/docs) | the source of this documentation site | suggest a correction |
| [Issues](https://github.com/Sandaal/ai-app-server/issues) | questions and bug reports | get help ([troubleshooting](../operate/troubleshooting.md)) |
| [Security](https://github.com/Sandaal/ai-app-server/security) | private vulnerability reports | [report a vulnerability](../operate/security.md#reporting-a-vulnerability) |

The Docker image is `ghcr.io/sandaal/aiapp-server` ([Docker guide](../install/docker.md)).

```bash
git clone https://github.com/Sandaal/ai-app-server.git
```

Everything in the repository is under the [Apache License 2.0](https://github.com/Sandaal/ai-app-server/blob/main/LICENSE).
