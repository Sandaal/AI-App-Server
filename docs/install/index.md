# Install and run

## Pick your platform

| Where | Guide | Good for |
|---|---|---|
| Windows 10/11, Windows Server 2019+ | [Windows](windows.md) | a laptop or a Windows server |
| macOS 12+ (Intel or Apple silicon) | [macOS](macos.md) | development |
| Linux x86_64 or arm64 | [Linux](linux.md) | servers, with a systemd service |
| Docker | [Docker](docker.md) | one container with a volume |
| Kubernetes | [Kubernetes (Helm)](kubernetes.md) | clusters, with ingress and metrics |
| Azure Container Apps or AKS | [Azure](azure.md) | Azure, with `azd up` |
| No internet access | [Offline servers](offline.md) | air-gapped networks |

## What every install needs

- **Python for app handlers.** Install [uv](https://docs.astral.sh/uv/) and the server prepares Python by itself on first start. Or use Python 3.10 or later with the worker packages: `pip install "grpcio>=1.85.3" "protobuf>=7.35.1" "pypdf>=5"`.
- **Resources.** About 200 MB of disk for the program and its Python environment, plus your data. At least 2 GB of RAM for a few small apps.
- **A model.** An API key from a provider, or a local [Ollama](https://ollama.com). See [Model providers](models.md).

## After installing

1. Start the server: `aiapp serve`. It listens on `127.0.0.1:8080`, so only this machine can reach it at first.
2. Check it: `aiapp health`, or open `http://127.0.0.1:8080/health`.
3. Connect a model: [Model providers](models.md).
4. Build your first app: [Quickstart](../get-started/quickstart.md).

!!! warning "Back up the master key"
    On first start the server creates `master.key` in its data folder (`~/.aiapp`, or `%USERPROFILE%\.aiapp` on Windows). It encrypts everything. **Keep a copy somewhere safe and separate from your backups**: without it, no backup can be read. See [Backups](../operate/backups.md).
