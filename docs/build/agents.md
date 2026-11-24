# Agents, tools and MCP

A **tool** is a Python function the model may call. An **agent** is a model that calls tools until it can answer.

## Tools

Write them in `tools.py` with `@app.tool`. The description comes from the docstring and the parameters from the type hints:

```python
from aiapp import app

@app.tool
def lookup_order(order_id: str) -> dict:
    """Look up an order by id (e.g. A-1001): item, total, customer and shipping status."""
    return ORDERS.get(order_id, {"error": "no such order"})

@app.tool
async def refund_order(order_id: str, reason: str) -> str:
    """Refund an order in full."""
    ...
```

Good docstrings matter: they are what the model reads to decide when to use a tool.

## Run an agent from a handler

```python
from tools import lookup_order, refund_order

async def run(req):
    result = await app.models.chat.run(
        req.json()["task"],
        tools=[lookup_order, refund_order],
        system="You are the shop's support agent. Check the facts with tools first.",
        max_steps=8,
    )
    return {"answer": result.text, "steps": len(result.steps)}
```

With `mcp=True` (the default), the tools of the app's MCP servers are offered too. A failing tool is reported to the model as an error instead of crashing the handler.

The **workflow-agent** blueprint does this for you, with a task page, durable runs and approvals:

```yaml
agent:
  instructions: "You are the support agent for an online shop."
  max_steps: 10
  approval_required: [refund_order]    # these tools wait for a person
  approval_timeout: 24h
```

## Use tools from MCP servers

Any [Model Context Protocol](https://modelcontextprotocol.io) server can give your app tools:

```yaml
mcp:
  - name: files                         # a local server, started by the app
    command: [npx, -y, "@modelcontextprotocol/server-filesystem", ./data]
  - name: crm                           # a remote server
    url: "https://crm.example.com/mcp"
    headers: { Authorization: "Bearer ${CRM_TOKEN}" }
    allow: [find_customer, list_orders] # only these tools (default: all)
```

From code:

```python
tools = await app.mcp_tools()                                  # [{"name", "description", "parameters"}]
text, is_error = await app.call_mcp_tool("find_customer", {"email": "ada@example.com"})
```

## Human approval

Sensitive tools (refunds, emails, changes) can wait for a person. See [Workflows and approvals](workflows.md).

## The other direction

To let outside agents (Claude, Copilot, IDEs) use **your** app's tools, see [Publish apps to AI agents](mcp-server.md).
