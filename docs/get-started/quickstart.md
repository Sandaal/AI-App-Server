# Quickstart: chat with your documents in ten minutes

You will install the server, connect a model, and deploy a chat app that answers from your own files with citations.

## 1. Install

=== "Windows"

    In PowerShell:

    ```powershell
    irm https://github.com/Sandaal/aiapp-server/releases/latest/download/install.ps1 -OutFile install.ps1
    powershell -ExecutionPolicy Bypass -File install.ps1
    ```

    Open a **new** terminal afterwards, so `aiapp` is on your PATH.

=== "macOS / Linux"

    ```bash
    curl -fsSLO https://github.com/Sandaal/aiapp-server/releases/latest/download/install.sh
    sh install.sh
    ```

=== "Docker"

    ```bash
    docker run -d --name aiapp -p 8080:8080 -v aiapp-data:/data \
      -e OPENAI_API_KEY=sk-... ghcr.io/sandaal/aiapp-server:latest
    ```

    Then run the commands below inside the container: `docker exec -it aiapp sh`.

The installer tells you if Python is missing. The easiest fix is [uv](https://docs.astral.sh/uv/), which lets the server prepare Python by itself:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh                                   # macOS / Linux
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"   # Windows
```

## 2. Start the server

```bash
aiapp serve
```

Leave it running, and open a second terminal for the next steps. Check it with `aiapp health`.

## 3. Connect a model

=== "OpenAI"

    ```bash
    aiapp secret set OPENAI_API_KEY      # paste the key when asked
    ```

=== "Azure OpenAI"

    ```bash
    aiapp secret set AZURE_OPENAI_API_KEY
    aiapp secret set AZURE_OPENAI_ENDPOINT   # https://YOUR-RESOURCE.openai.azure.com
    ```

    Use `--provider azure-openai` in step 4, then set your deployment names in `ai-app.yaml`.

=== "Local and free (Ollama)"

    Install [Ollama](https://ollama.com), then:

    ```bash
    ollama pull llama3.2 && ollama pull nomic-embed-text
    ```

    Use `--provider ollama` in step 4. No key needed.

More providers (Anthropic, Gemini, Bedrock): see [Model providers](../install/models.md).

## 4. Create and deploy a chat app

```bash
aiapp new knowledge-chat hr-bot --provider openai
cd hr-bot
```

Put your documents (PDF, Word, PowerPoint, Excel, Markdown, HTML, email…) in the `policies/` folder. The template already has a sample there. Then:

```bash
aiapp source add ./policies/
aiapp deploy
```

## 5. Ask a question

Open **http://127.0.0.1:8080/apps/hr-bot/** in your browser for the built-in chat page, or call it:

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"message":"How many days of annual leave do employees get?"}' \
  http://127.0.0.1:8080/apps/hr-bot/chat
```

The answer streams back with citations such as `[1]`, pointing at the documents and pages it came from.

## What next

- **Change documents:** edit `policies/` and run `aiapp deploy` again. Only changed files are re-indexed.
- **See usage and cost:** `aiapp logs hr-bot`.
- **See one request step by step:** `aiapp trace` and `aiapp trace ID`.
- **Open the console:** `aiapp console`.
- **Try another blueprint:** [the ten blueprints](../build/blueprints.md).
- **Let others use it safely:** [Security checklist](../operate/security.md).
