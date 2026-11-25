# Install on macOS

Works on macOS 12 or later, Intel and Apple silicon.

## 1. Run the installer

```bash
curl -fsSLO https://github.com/Sandaal/ai-app-server/releases/latest/download/install.sh
sh install.sh
```

The script picks the right download, checks its checksum, installs `aiapp` to `~/.local/bin` (or `/usr/local/bin` when run with `sudo`), and checks for Python. Make sure `~/.local/bin` is on your PATH, then: `aiapp version`.

## 2. Python

If the installer says so, install uv:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 3. Start the server

```bash
aiapp serve
```

Data goes to `~/.aiapp`. Use a second terminal for other commands.

## Options

| Option | Command |
|---|---|
| A specific version | `sh install.sh --version v3.0.0` |
| Offline install | `sh install.sh --archive aiapp_3.0.0_darwin_arm64.tar.gz` with `SHA256SUMS` in the same folder |
| By hand | unpack the archive; if macOS blocks the unsigned binary, run `xattr -d com.apple.quarantine ./aiapp` |

!!! tip "Free local models on a Mac"
    Apple silicon runs small models well. Install [Ollama](https://ollama.com), run `ollama pull llama3.2 && ollama pull nomic-embed-text`, and create apps with `--provider ollama`.

Next: [connect a model](models.md).
