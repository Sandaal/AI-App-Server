# Install on Windows

Works on Windows 10 and 11 and Windows Server 2019 or later, on x64 and ARM.

## 1. Run the installer

Open **PowerShell** (no admin rights needed) and run:

```powershell
irm https://github.com/Sandaal/ai-app-server/releases/latest/download/install.ps1 -OutFile install.ps1
powershell -ExecutionPolicy Bypass -File install.ps1
```

The script:

1. picks the right download for your CPU,
2. checks it against `SHA256SUMS`,
3. installs `aiapp.exe` to `%LOCALAPPDATA%\Programs\aiapp` and adds it to your PATH,
4. tells you whether Python or uv is ready.

**Open a new terminal** afterwards so the PATH change takes effect, then check: `aiapp version`.

## 2. Python

If the installer says Python isn't ready, install uv (recommended):

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

!!! note "Use python.org or uv, not the Microsoft Store Python"
    The server limits each app's memory with a Windows *job object*. The Microsoft Store build of Python runs outside it, so memory limits can't be enforced; the server warns when it sees it.

## 3. Start the server

```powershell
aiapp serve
```

Your data goes to `%USERPROFILE%\.aiapp`. Leave the window open and use a second terminal for other commands.

## Options

| Option | Command |
|---|---|
| Start automatically when you sign in | `powershell -ExecutionPolicy Bypass -File install.ps1 -Service` |
| A specific version | `... install.ps1 -Version v1.1.0` |
| Offline install | download the zip and `SHA256SUMS` from [Download](../download.md), then `... install.ps1 -Archive .\aiapp_1.1.0_windows_amd64.zip` |
| By hand | unzip anywhere and add the folder with `aiapp.exe` to your PATH |

## Serve other machines

By default only this computer can reach the server. To serve your network:

1. Read the [Security checklist](../operate/security.md) and require keys or sign-in for each app.
2. Start with `aiapp serve --addr 0.0.0.0:8080`, and allow port 8080 in Windows Defender Firewall.
3. Put HTTPS in front (IIS with Application Request Routing, or a reverse proxy).

Next: [connect a model](models.md).
