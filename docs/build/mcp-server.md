# Publish apps to AI agents (MCP)

Your app can be an **MCP server**, so Claude, GitHub Copilot, VS Code agents and other [MCP](https://modelcontextprotocol.io) clients can use its tools and routes.

```yaml
mcp_server:
  tools: [lookup_order, lookup_customer]       # @app.tool functions from tools.py, or ["*"]
  routes:                                      # routes offered as tools too
    - { route: /chat, name: ask_hr, description: "Ask the HR assistant about policies" }
  roles: [mcp]                                 # callers need this role
```

```bash
aiapp deploy
aiapp key create hr-bot --name claude --role mcp    # a key for the MCP client
aiapp mcp hr-bot                                    # the endpoint and ready-to-paste client config
```

The endpoint is `https://SERVER/apps/APP/mcp` (streamable HTTP).

## Connect a client

=== "VS Code (Copilot agent mode)"

    `.vscode/mcp.json`:

    ```json
    {
      "servers": {
        "hr-bot": {
          "type": "http",
          "url": "https://ai.contoso.com/apps/hr-bot/mcp",
          "headers": { "Authorization": "Bearer ${input:hrKey}" }
        }
      },
      "inputs": [{ "id": "hrKey", "type": "promptString", "description": "HR bot key", "password": true }]
    }
    ```

=== "Claude Desktop / other clients"

    Use the URL and an `Authorization: Bearer KEY` header. `aiapp mcp APP` prints the config for common clients.

## What protects these calls

- The app's keys or sign-in, and `roles`.
- Its quotas and guardrails, exactly like HTTP calls.
- Every call is audited (`aiapp audit --type mcp_call`), traced and counted.
- **Tools that need a person's approval are never published.**
