"""Handlers the core calls to publish an app's tools over MCP
(``mcp_server:`` in ai-app.yaml). Not for app code."""

from __future__ import annotations

import json

from aiapp import Request, Response
from aiapp.blueprints.workflow_agent import local_tools


def _json(obj, status: int = 200) -> Response:
    return Response(json.dumps(obj, default=str), status=status, content_type="application/json")


async def list_tools(req: Request):
    """The @app.tool functions in tools.py: name, description, JSON schema."""
    return _json([{"name": t.name, "description": t.description, "parameters": t.parameters}
                  for t in local_tools().values()])


async def call_tool(req: Request):
    """Runs one tool with {"name", "arguments"}; errors come back as results."""
    body = req.json() or {}
    tool = local_tools().get(body.get("name", ""))
    if tool is None:
        return _json({"text": f"unknown tool {body.get('name')!r}", "is_error": True})
    try:
        value = await tool.call(body.get("arguments") or {})
    except Exception as e:  # the client sees the failure, like a model would
        return _json({"text": f"{type(e).__name__}: {e}", "is_error": True})
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    return _json({"text": text, "is_error": False})
