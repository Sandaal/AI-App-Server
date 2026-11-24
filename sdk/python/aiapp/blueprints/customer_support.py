"""Customer support: answers from the app's documents with citations, actions
through the app's tools, a person's approval before sensitive actions, and a
handoff to a person when the assistant can't help.

Route ``/chat`` (streaming, same protocol as knowledge-chat, so the chat page
works): ``{"message": "..."}`` with ``X-Session-Id`` to keep a conversation.
The end event carries ``citations``, and ``handoff: true`` once a person has
taken over.

Manifest::

    support:
      instructions: "You are the support assistant for Contoso..."
      approval_required: [refund_order]   # these wait for a person (aiapp approve / approvals page)
      approval_timeout: 24h
      handoff_topic: support.handoffs     # default; handoffs and later customer messages go here
      actions_topic: support.actions      # default; outcomes of approved actions go here

Tools are ``@app.tool`` functions in ``tools.py`` plus the app's MCP tools.
Two tools are always offered: ``handoff_to_human`` (the conversation goes to
the handoff topic; further messages are forwarded there instead of answered)
and the documents, which are searched before every answer.

An action that needs approval doesn't block the chat. It becomes a durable
``support_action`` job that waits for the decision, runs the tool if approved,
adds the outcome to the conversation and publishes it to the actions topic.
"""

from __future__ import annotations

import json
import re
import time

from aiapp import ModelError, Request, Response, app, set_metadata
from aiapp.blueprints.knowledge_chat import MIN_KEYWORD, MIN_SIMILARITY, context_block, parse
from aiapp.blueprints.workflow_agent import local_tools

HISTORY = 12
TOP_K = 4
HANDOFFS = "handoffs"
HANDOFF_TTL = 24 * 3600

DEFAULT_INSTRUCTIONS = (
    "You are a friendly, concise customer support assistant. Answer from the documentation passages when they "
    "cover the question, citing them like [1]. Use the tools to look things up or act. If you can't help, the "
    "customer asks for a person, or they are upset, call handoff_to_human."
)
RULES = (
    "Rules: never invent policies, prices or order details; say so when the documentation doesn't cover something. "
    "Only state that an action happened if a tool result says it did. When a tool says an action is waiting for "
    "approval, tell the customer it is pending and that they'll hear back."
)
HANDOFF_TOOL = {
    "name": "handoff_to_human",
    "description": "Hand the conversation to a person on the support team. Use when you can't help, the customer "
                   "asks for a person, or the matter is sensitive.",
    "parameters": {
        "type": "object",
        "properties": {
            "reason": {"type": "string", "description": "Why a person is needed"},
            "summary": {"type": "string", "description": "A short summary of the conversation so far for the person"},
        },
        "required": ["reason", "summary"],
    },
}
HANDED_OFF = "Thanks, I've passed this to our support team. A person will pick up from here."
STILL_HANDED_OFF = "I've passed your message on to the support team; a person will reply."


def _config() -> dict:
    return app.manifest.get("support") or {}


def _duration(text: str | None, default: float) -> float:
    m = re.fullmatch(r"(\d+(?:\.\d+)?)(s|m|h)", (text or "").strip())
    return float(m.group(1)) * {"s": 1, "m": 60, "h": 3600}[m.group(2)] if m else default


def _end_tokens(text: str):
    yield text


async def _tools(gated: set[str]) -> tuple[list[dict], dict]:
    local = local_tools()
    defs = [{"name": t.name, "description": t.description, "parameters": t.parameters} for t in local.values()]
    try:
        defs += [d for d in await app.mcp_tools() if d["name"] not in local]
    except Exception:
        pass
    for d in defs:
        if d["name"] in gated:
            d["description"] = (d["description"] + " (Needs a person's approval; the customer is told it is pending.)").strip()
    return defs + [HANDOFF_TOOL], local


async def _run_tool(local: dict, name: str, args: dict) -> str:
    try:
        if name in local:
            value = await local[name].call(args)
            return value if isinstance(value, str) else json.dumps(value, default=str)
        text, is_error = await app.call_mcp_tool(name, args)
        return ("Error: " if is_error else "") + text
    except Exception as e:  # the model sees the failure and can react
        return f"Error: {type(e).__name__}: {e}"


async def chat(req: Request):
    question, history = parse(req)
    if not question:
        return Response('{"error": "send {\\"message\\": \\"...\\"}"}', status=400, content_type="application/json")
    session = req.session_id
    return converse(question, session, history)


async def converse(question: str, session: str, client_history: list[dict] | None):
    cfg = _config()
    handoff_topic = cfg.get("handoff_topic") or "support.handoffs"

    # Already with a person: forward the message instead of answering.
    if session and await app.kv.get(session, namespace=HANDOFFS) is not None:
        await app.events.publish(handoff_topic, {"type": "message", "session": session, "message": question},
                                 key=session)
        await app.memory.append(session, question, STILL_HANDED_OFF)
        set_metadata("handoff", True)
        yield STILL_HANDED_OFF
        return

    hits = [h for h in await app.vectors.search("sources", question, k=TOP_K, mode="hybrid")
            if h.similarity >= MIN_SIMILARITY or h.keyword >= MIN_KEYWORD]
    context, citations = context_block(hits) if hits else ("", [])
    set_metadata("citations", citations)
    # The passages go first: small models otherwise lean on the tool rules and
    # say "I can't look that up" to questions the documentation answers.
    docs = ("Documentation passages. When they answer the customer's question, answer from them and cite them "
            "like [1]:\n" + context) if context else "No documentation matched this question."
    system = docs + "\n\n" + (cfg.get("instructions") or DEFAULT_INSTRUCTIONS).strip() + "\n\n" + RULES

    history = client_history if client_history is not None else await app.memory.history(session, last=HISTORY)
    gated = set(cfg.get("approval_required") or [])
    tools, local = await _tools(gated)
    convo = list(history) + [{"role": "user", "content": question}]
    answer = ""
    try:
        for _ in range(int(cfg.get("max_steps") or 5)):
            reply = await app.models.chat.turn(convo, tools=tools, system=system, temperature=0)
            if not reply["calls"]:
                answer = reply["text"]
                break
            convo.append({"role": "assistant", "content": reply["text"], "tool_calls": reply["calls"]})
            for call in reply["calls"]:
                name, args = call["name"], call["arguments"]
                if name == "handoff_to_human":
                    await _handoff(session, question, convo, args, handoff_topic)
                    await app.memory.append(session, question, HANDED_OFF)
                    set_metadata("handoff", True)
                    yield HANDED_OFF
                    return
                if name in gated:
                    job = await app.jobs.enqueue("support_action", {"session": session, "tool": name, "arguments": args,
                                                                    "question": question})
                    result = (f"Requested; waiting for a person's approval (request {job.id}). "
                              "Tell the customer it is pending and that they'll hear back.")
                else:
                    result = await _run_tool(local, name, args)
                convo.append({"role": "tool", "tool_call_id": call["id"], "content": result[:4000]})
        else:
            answer = "I'm sorry, I couldn't finish that. Let me pass you to a person."
            await _handoff(session, question, convo, {"reason": "the assistant ran out of steps", "summary": question},
                           handoff_topic)
            set_metadata("handoff", True)
    except ModelError as e:
        set_metadata("error", e.code)
        yield "\n\n[The assistant is unavailable right now. Please try again.]"
        return
    await app.memory.append(session, question, answer)
    for piece in _end_tokens(answer):
        yield piece


async def _handoff(session: str, question: str, convo: list[dict], args: dict, topic: str) -> None:
    transcript = [{"role": m["role"], "content": m.get("content", "")} for m in convo if m["role"] in ("user", "assistant")]
    record = {"type": "handoff", "session": session, "reason": args.get("reason", ""),
              "summary": args.get("summary", ""), "last_message": question, "transcript": transcript[-HISTORY:],
              "time": time.time()}
    await app.events.publish(topic, record, key=session or "anonymous")
    if session:
        await app.kv.put(session, json.dumps(record), namespace=HANDOFFS, ttl=HANDOFF_TTL)


@app.workflow
async def action(wf, p):
    """The support_action job: wait for a person, then run the tool (or not)."""
    cfg = _config()
    name, args, session = p["tool"], p["arguments"], p.get("session", "")
    decision = await wf.approval("approve", f"Allow support to run {name}?",
                                 {"tool": name, "arguments": args, "customer_message": p.get("question", "")},
                                 timeout=_duration(cfg.get("approval_timeout"), 24 * 3600))
    if decision.approved:
        local = local_tools()
        outcome = await wf.step("run", _run_tool, local, name, args)
        note = f"Update: your request was approved and done. {outcome}"
    else:
        outcome = None
        note = f"Update: your request ({name}) was not approved ({decision.state})." + (
            f" {decision.comment}" if decision.comment else "")
    await wf.step("tell", _tell, session, note, name, args, decision.state, outcome, cfg.get("actions_topic") or "support.actions")
    return {"tool": name, "state": decision.state, "by": decision.by, "comment": decision.comment, "outcome": outcome}


async def _tell(session, note, name, args, state, outcome, topic) -> bool:
    if session:
        await app.memory.append(session, "(status update)", note)
    await app.events.publish(topic, {"session": session, "tool": name, "arguments": args, "state": state,
                                     "outcome": outcome}, key=session or "anonymous")
    return True
