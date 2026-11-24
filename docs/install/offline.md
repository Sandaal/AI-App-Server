# Offline (air-gapped) servers

The server itself needs no internet. Two things normally come from the internet: the program download and the Python packages for your apps.

## 1. Bring the program

On a connected machine, download the archive for the target platform and `SHA256SUMS` from [Download](../download.md). Copy both, then:

=== "Linux / macOS"

    ```bash
    sh install.sh --archive aiapp_1.1.0_linux_amd64.tar.gz
    ```

=== "Windows"

    ```powershell
    powershell -ExecutionPolicy Bypass -File install.ps1 -Archive .\aiapp_1.1.0_windows_amd64.zip
    ```

## 2. Bring the Python packages

On a connected machine with the same OS and CPU:

```bash
aiapp wheelhouse ./wheels ./hr-bot ./invoices     # the worker packages plus each app's requirements
```

Copy the `wheels` folder over and start the server with it:

```bash
aiapp serve --wheelhouse ./wheels        # or AIAPP_WHEELHOUSE=./wheels
```

The server then installs only from that folder.

## 3. Models

Use a model server inside your network: a local [Ollama](https://ollama.com), vLLM, or an Azure OpenAI private endpoint. Point apps at it with `provider: openai-compatible` and `endpoint:`, see [Model providers](models.md).
