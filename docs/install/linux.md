# Install on Linux

Works on x86_64 and arm64, on any distribution (glibc or musl).

## 1. Run the installer

```bash
curl -fsSLO https://github.com/Sandaal/aiapp-server/releases/latest/download/install.sh
sh install.sh
```

As root the binary goes to `/usr/local/bin`, otherwise to `~/.local/bin`. The script checks the download's checksum and checks for Python and uv. Install uv if it says so:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 2a. Run it by hand

```bash
aiapp serve        # data in ~/.aiapp, listening on 127.0.0.1:8080
```

## 2b. Run it as a service (systemd)

```bash
sudo sh install.sh --service
```

This:

1. creates a system user `aiapp`,
2. keeps data in `/var/lib/aiapp`,
3. deploys every app folder in `/etc/aiapp/apps/` at start,
4. reads provider keys from `/etc/aiapp/env` (`KEY=value` lines; the file is created readable by root only),
5. listens on `127.0.0.1:8080`.

Manage it with:

```bash
systemctl status aiapp
journalctl -u aiapp -f
sudo -u aiapp AIAPP_DATA_DIR=/var/lib/aiapp aiapp apps     # CLI commands against the service
```

**Add a key** to `/etc/aiapp/env`, for example `OPENAI_API_KEY=sk-...`, then `sudo systemctl restart aiapp`.

## Serve other machines

1. Read the [Security checklist](../operate/security.md).
2. Put a reverse proxy with HTTPS in front (recommended), or change `--addr` in `/etc/systemd/system/aiapp.service` to `0.0.0.0:8080` and run `sudo systemctl daemon-reload && sudo systemctl restart aiapp`.

Example nginx site (note `proxy_buffering off`, so chat answers stream):

```nginx
server {
  listen 443 ssl;
  server_name ai.example.com;
  ssl_certificate     /etc/ssl/certs/ai.example.com.pem;
  ssl_certificate_key /etc/ssl/private/ai.example.com.key;
  location / {
    proxy_pass http://127.0.0.1:8080;
    proxy_set_header Host $host;
    proxy_buffering off;
    proxy_read_timeout 300s;
    client_max_body_size 100m;
  }
}
```

Next: [connect a model](models.md).
