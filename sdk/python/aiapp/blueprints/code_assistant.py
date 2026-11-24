"""Code assistant: answers questions about a codebase, citing files and lines.

Route ``/chat`` (streaming, the knowledge-chat protocol, so the chat page works).
Sources are code: a Git connector or a local folder. Every source of this
blueprint is indexed as code, in chunks that follow functions and types and
carry their line ranges, so citations read ``src/server.go:120-168``.
"""

from __future__ import annotations

from aiapp import ModelError, Request, Response, app, set_metadata
from aiapp.blueprints.knowledge_chat import parse

TOP_K = 8
HISTORY = 8
SYSTEM = """You are a senior engineer answering questions about a codebase, using only the numbered excerpts below.
- Cite every claim with the excerpt number, like [2], and name files and functions as they appear.
- When asked how to change something, point to the exact files and lines to edit and show short code.
- If the excerpts don't contain the answer, say what you'd need to look at instead. Don't guess.

Excerpts:
"""


def _context(hits) -> tuple[str, list[dict]]:
    parts, cites = [], []
    for i, h in enumerate(hits, start=1):
        src, lines = h.metadata.get("source", h.id), h.metadata.get("lines", "")
        label = f"{src}:{lines}" if lines else src
        parts.append(f"[{i}] {label}\n{h.text}")
        cites.append({"n": i, "source": label, "page": None, "score": round(h.similarity, 3)})
    return "\n\n".join(parts), cites


async def chat(req: Request):
    question, history = parse(req)
    if not question:
        return Response('{"error": "send {\\"message\\": \\"...\\"}"}', status=400, content_type="application/json")
    return answer(question, "" if history is not None else req.session_id, history)


async def answer(question: str, session: str, history):
    hits = [h for h in await app.vectors.search("sources", question, k=TOP_K, mode="hybrid")
            if h.similarity >= 0.15 or h.keyword >= 1.0]
    context, cites = _context(hits)
    set_metadata("citations", cites)
    if not hits:
        text = "I couldn't find code about that in the indexed repository."
        await app.memory.append(session, question, text)
        yield text
        return
    if history is None:
        history = await app.memory.history(session, last=HISTORY)
    reply = []
    try:
        async for token in app.models.chat.stream(question, system=SYSTEM + context, history=history, temperature=0.1):
            reply.append(token)
            yield token
    except ModelError as e:
        set_metadata("error", e.code)
        yield "\n\n[The model is unavailable right now. Please try again.]"
        return
    await app.memory.append(session, question, "".join(reply))
