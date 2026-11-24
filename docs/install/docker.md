# Run with Docker

The image is `ghcr.io/sandaal/aiapp-server` for amd64 and arm64. Tags: `latest`, a minor line such as `1.1`, or an exact version such as `1.1.0`.

## Start a server

```bash
docker run -d --name aiapp -p 8080:8080 \
  -v aiapp-data:/data \
  -v "$PWD/my-apps:/apps:ro" \
  -e OPENAI_API_KEY=sk-... \
  ghcr.io/sandaal/aiapp-server:1.1
```

| Path | What it is |
|---|---|
| `/data` | Everything the server stores, including the master key. Use a volume and back it up. |
| `/apps` | Every folder in it with an `ai-app.yaml` is deployed at startup. |

The container runs as a non-root user (uid 10001) and listens on all interfaces inside the container; publish the port only where it should be reachable.

## Run commands

```bash
docker exec aiapp aiapp apps
docker exec aiapp aiapp logs hr-bot
docker exec -it aiapp aiapp secret set ANTHROPIC_API_KEY
```

## Docker Compose

```yaml
services:
  aiapp:
    image: ghcr.io/sandaal/aiapp-server:1.1
    ports: ["8080:8080"]
    volumes:
      - aiapp-data:/data
      - ./apps:/apps:ro
    env_file: .env            # OPENAI_API_KEY=... etc.
    restart: unless-stopped
volumes:
  aiapp-data:
```

## Ship your apps in your own image

```dockerfile
FROM ghcr.io/sandaal/aiapp-server:1.1
COPY my-apps/ /apps/
```

## Local models with Ollama on the host

Point the app's models at `http://host.docker.internal:11434` and start the container with `--add-host=host.docker.internal:host-gateway` on Linux.
