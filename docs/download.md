# Download

**Latest release:** [github.com/Sandaal/ai-app-server/releases/latest](https://github.com/Sandaal/ai-app-server/releases/latest), with release notes.

The quickest way is the installer for your platform ([Windows](install/windows.md), [macOS](install/macos.md), [Linux](install/linux.md)), which picks the right file and checks it. To download by hand:

| Platform | File |
|---|---|
| Windows x64 | `aiapp_VERSION_windows_amd64.zip` |
| Windows ARM | `aiapp_VERSION_windows_arm64.zip` |
| macOS Apple silicon | `aiapp_VERSION_darwin_arm64.tar.gz` |
| macOS Intel | `aiapp_VERSION_darwin_amd64.tar.gz` |
| Linux x64 | `aiapp_VERSION_linux_amd64.tar.gz` |
| Linux arm64 | `aiapp_VERSION_linux_arm64.tar.gz` |
| VS Code extension | `aiapp-vscode-VERSION.vsix` |
| Installers | `install.ps1`, `install.sh` |
| Checksums | `SHA256SUMS` |

**Docker:** `docker pull ghcr.io/sandaal/aiapp-server:latest` (amd64 and arm64).

**Helm chart and Azure templates:** in the [repository](https://github.com/Sandaal/ai-app-server), under `deploy/`.

## Verify a download

=== "Linux / macOS"

    ```bash
    sha256sum --check --ignore-missing SHA256SUMS      # macOS: shasum -a 256 -c --ignore-missing SHA256SUMS
    ```

=== "Windows"

    ```powershell
    (Get-FileHash .\aiapp_1.1.0_windows_amd64.zip -Algorithm SHA256).Hash
    # compare with the line for that file in SHA256SUMS
    ```

## Release notes

Each release's notes are on its [release page](https://github.com/Sandaal/ai-app-server/releases); the full history is in [CHANGELOG.md](https://github.com/Sandaal/ai-app-server/blob/main/CHANGELOG.md).
