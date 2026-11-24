"""Workflow agent: give it a task; it works through it with the app's tools,
pausing for a person before any tool listed under ``agent.approval_required``.

Routes
    POST /run   ``{"task": "...", "context": {...}?}`` → queues a durable run,
                202 ``{"job": id, "state": ...}``; ``?wait=SECONDS`` (≤ 60) waits.
    GET  /run   ``?id=JOB_ID`` → state, and once finished the answer and the
                full history of model turns, tool calls and approvals.

Tools are the ``@app.tool`` functions in ``tools.py`` in the app folder, plus
the app's MCP servers. The run is a workflow: every model turn and tool call
is a saved step, so a run that waits for an approval, or survives a restart,
continues where it stopped without repeating model calls or tool actions.

Manifest::

    agent:
      instructions: "You are the support agent for Contoso..."
      max_steps: 10
      approval_required: [refund_order, crm__delete_contact]
      approval_timeout: 24h
"""

from __future__ import annotations

import asyncio
import importlib
import json
import os
import re

from aiapp import ModelError, Request, Response, Tool, app

MAX_WAIT = 60
DEFAULT_INSTRUCTIONS = (
    "You are an agent that completes the user's task with the tools available. Think about which tool "
    "to use, call it, read the result, and continue until the task is done; then reply with a short summary "
    "of what you did and the outcome. If a tool needs approval and it is refused, say so and stop or choose "
    "another way. Never invent tool results."
)


# Added to every run's instructions, whatever the app configures: an agent
# must not report actions it did not take (small models in particular will
# otherwise promise a refund instead of calling the refund tool).
ALWAYS = (
    "Rules: to do something, call the tool that does it; never just say it will be done. Only state that "
    "an action happened if a tool result in this conversation confirms it. If you cannot do it, say so."
)


def _json(obj, status=200) -> Response:
    return Response(json.dumps(obj), status=status, content_type="application/json")


def _config() -> dict:
    return app.manifest.get("agent") or {}


def _duration(text: str | None, default: float) -> float:
    m = re.fullmatch(r"(\d+(?:\.\d+)?)(s|m|h)", (text or "").strip())
    if not m:
        return default
    return float(m.group(1)) * {"s": 1, "m": 60, "h": 3600}[m.group(2)]


def local_tools() -> dict[str, Tool]:
    """@app.tool functions in tools.py next to ai-app.yaml (optional)."""
    if not os.path.exists(os.path.join(os.getcwd(), "tools.py")):
        return {}
    module = importlib.import_module("tools")
    return {t.name: t for t in vars(module).values() if isinstance(t, Tool)}


USAGE = 'POST {"task": "..."} to start a run, or GET ?id=JOB_ID to read one'


async def run(req: Request):
    if req.method == "GET" or not req.body:
        job_id = req.query.get("id", "")
        if not job_id:
            return _json({"error": USAGE}, 400)
        try:
            job = await app.jobs.get(job_id)
        except Exception:
            return _json({"error": "run not found"}, 404)
        return _json(_view(job))
    try:
        body = req.json() or {}
    except json.JSONDecodeError:
        body = {"task": req.text}
    task = str(body.get("task") or "").strip() if isinstance(body, dict) else ""
    if not task:
        return _json({"error": USAGE}, 400)
    job = await app.jobs.enqueue("agent", {"task": task, "context": body.get("context")})
    wait = min(float(req.query.get("wait", "0") or 0), MAX_WAIT)
    deadline = asyncio.get_running_loop().time() + wait
    while wait > 0 and job.state in ("queued", "running") and asyncio.get_running_loop().time() < deadline:
        await asyncio.sleep(0.5)
        job = await app.jobs.get(job.id)
    return _json(_view(job), 200 if job.state in ("done", "dead") else 202)


def _view(job) -> dict:
    out = {"job": job.id, "state": job.state}
    if job.state == "waiting":
        out["note"] = "waiting for an approval: see /_approvals/ or aiapp approvals"
    if job.state == "done":
        out.update(job.result or {})
    if job.last_error:
        out["error"] = job.last_error
    return out


def _clip(text: str, n: int = 4000) -> str:
    return text if len(text) <= n else text[:n] + " …[truncated]"


@app.workflow
async def agent(wf, input):
    cfg = _config()
    max_steps = int(cfg.get("max_steps") or 10)
    gated = set(cfg.get("approval_required") or [])
    timeout = _duration(cfg.get("approval_timeout"), 24 * 3600)
    system = (cfg.get("instructions") or DEFAULT_INSTRUCTIONS).strip() + "\n\n" + ALWAYS
    if input.get("context"):
        system += "\n\nContext for this task:\n" + json.dumps(input["context"])

    local = local_tools()

    async def list_tools():
        defs = [{"name": t.name, "description": t.description, "parameters": t.parameters} for t in local.values()]
        try:
            defs += [d for d in await app.mcp_tools() if d["name"] not in local]
        except Exception:
            pass  # no MCP servers, or none reachable: Python tools only
        for d in defs:
            if d["name"] in gated:
                d["description"] = (d["description"] + " (Requires a person's approval before it runs.)").strip()
        return defs

    tools = await wf.step("tools", list_tools)  # saved, so a replay offers the same tools
    convo = [{"role": "user", "content": input["task"]}]
    history = []

    for turn in range(max_steps):
        try:
            reply = await wf.step(f"model-{turn}", app.models.chat.turn, convo, tools=tools, system=system)
        except ModelError as e:
            if not e.retryable:
                return {"answer": None, "error": f"model error: {e}", "history": history}
            raise  # let the job retry
        history.append({"type": "model", "turn": turn, "text": reply["text"],
                        "calls": [{"tool": c["name"], "arguments": c["arguments"]} for c in reply["calls"]]})
        if not reply["calls"]:
            return {"answer": reply["text"], "history": history, "turns": turn + 1}
        convo.append({"role": "assistant", "content": reply["text"], "tool_calls": reply["calls"]})

        for call in reply["calls"]:
            name, args = call["name"], call["arguments"]
            step = f"tool-{turn}-{call['id']}"
            if name in gated:
                decision = await wf.approval(step, f"Allow the agent to run {name}?",
                                             {"task": input["task"], "tool": name, "arguments": args}, timeout=timeout)
                history.append({"type": "approval", "tool": name, "state": decision.state, "by": decision.by,
                                "comment": decision.comment})
                if not decision.approved:
                    result = f"Not run: a person did not approve it ({decision.state}). {decision.comment}".strip()
                    convo.append({"role": "tool", "tool_call_id": call["id"], "content": result})
                    continue

            async def execute(name=name, args=args):
                try:
                    if name in local:
                        value = await local[name].call(args)
                        return {"text": value if isinstance(value, str) else json.dumps(value, default=str), "error": False}
                    text, is_error = await app.call_mcp_tool(name, args)
                    return {"text": text, "error": is_error}
                except Exception as e:  # the model sees the failure and can react
                    return {"text": f"Error: {type(e).__name__}: {e}", "error": True}

            out = await wf.step(step, execute)
            history.append({"type": "tool", "tool": name, "arguments": args, "result": _clip(out["text"], 2000),
                            "error": out["error"]})
            convo.append({"role": "tool", "tool_call_id": call["id"], "content": _clip(out["text"])})

    return {"answer": None, "error": f"stopped after {max_steps} model turns without finishing", "history": history}
