# AI App Server

**Run AI applications from one small configuration file**: chat over your documents, document extraction, agents with tools, workflows with human approval, classification, meeting notes and more. No web framework, database or vector store to set up; everything is stored on the server's own disk, encrypted.

📖 **Documentation: https://sandaal.github.io/aiapp-server/**

⬇️ **Download: [latest release](https://github.com/Sandaal/aiapp-server/releases/latest)** (Windows, macOS, Linux, VS Code extension) · Docker: `ghcr.io/sandaal/aiapp-server`

## Install

**Windows** (PowerShell):

```powershell
irm https://github.com/Sandaal/aiapp-server/releases/latest/download/install.ps1 -OutFile install.ps1
powershell -ExecutionPolicy Bypass -File install.ps1
```

**macOS / Linux:**

```bash
curl -fsSLO https://github.com/Sandaal/aiapp-server/releases/latest/download/install.sh
sh install.sh
```

**Docker:**

```bash
docker run -d -p 8080:8080 -v aiapp-data:/data -e OPENAI_API_KEY=sk-... ghcr.io/sandaal/aiapp-server:latest
```

Kubernetes (Helm) and Azure (azd) templates are in [`deploy/`](deploy/).

## Your first app

```bash
aiapp serve                                    # in one terminal
aiapp secret set OPENAI_API_KEY                # in another
aiapp new knowledge-chat hr-bot --provider openai
cd hr-bot && aiapp source add ./policies/ && aiapp deploy
# open http://127.0.0.1:8080/apps/hr-bot/
```

Next: the [quickstart](https://sandaal.github.io/aiapp-server/get-started/quickstart/).

## This repository

This repository holds the releases, the documentation site (`docs/`), the deployment templates (`deploy/`) and the `ai-app.yaml` JSON Schema (`schema/`). Questions and bug reports are welcome as [issues](https://github.com/Sandaal/aiapp-server/issues); for security issues see [SECURITY.md](SECURITY.md).

Licensed under the [Apache License 2.0](LICENSE).
