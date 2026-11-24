# A copy of the knowledge-chat blueprint (sdk/python/aiapp/blueprints/knowledge_chat.py),
# changed for this app: answers are short and signed (see SYSTEM_PROMPT). Edit anything here.

"""Knowledge chat: answer questions from the app's ingested documents, with citations.

Route ``/chat`` (streaming). Request body: ``{"message": "..."}`` or plain text.
Send ``X-Session-Id`` to keep a conversation. The answer streams as SSE data
events; the end event carries ``{"citations": [{"n", "source", "page", "score"}]}``.

Needs two models in ai-app.yaml: ``chat`` and ``embedding``.
"""

from __future__ import annotations

import json

from aiapp import ModelError, Request, Response, app, set_metadata

TOP_K = 5
# A hit counts as relevant if it is similar in meaning or shares a fairly rare
# word with the question (BM25 >= MIN_KEYWORD), e.g. a policy or product code
# that embeddings blur. Hybrid search ranks by both.
MIN_SIMILARITY = 0.2
MIN_KEYWORD = 2.0
HISTORY_MESSAGES = 10

SYSTEM_PROMPT = """Answer in at most three sentences, then sign as "Contoso Help".
You answer questions using only the numbered context passages below.
- Answer in one to three plain sentences that state the facts, and put the passage number in square brackets after each claim, like "Staff get 20 days of leave [1]." Never reply with only citations.
- If the passages don't contain the answer, say you couldn't find it in the documents. Don't guess.

Context:
"""

NO_SOURCES = "I couldn't find anything about that in the indexed documents."


def parse(req: Request) -> tuple[str, list[dict] | None]:
    """The question, and the client's own history when it sends one (the
    OpenAI-compatible endpoint passes {"message", "messages"})."""
    ctype = req.headers.get("content-type", "")
    if "json" in ctype or req.text.lstrip().startswith("{"):
        try:
            body = req.json()
        except json.JSONDecodeError:
            body = None
        if isinstance(body, dict):
            question = str(body.get("message") or body.get("question") or "").strip()
            history = None
            if isinstance(body.get("messages"), list):
                # Everything before the final user message, minus client system prompts:
                # the blueprint's own instructions and context always apply.
                history = [
                    {"role": m["role"], "content": str(m.get("content", ""))}
                    for m in body["messages"][:-1]
                    if isinstance(m, dict) and m.get("role") in ("user", "assistant")
                ][-HISTORY_MESSAGES:]
            return question, history
    return req.text.strip(), None


def context_block(hits) -> tuple[str, list[dict]]:
    parts, citations = [], []
    for i, h in enumerate(hits, start=1):
        source = h.metadata.get("source", h.id)
        page = h.metadata.get("page")
        label = f"{source}, page {page}" if page else source
        parts.append(f"[{i}] ({label})\n{h.text}")
        citations.append({"n": i, "source": source, "page": page, "score": round(h.similarity, 3)})
    return "\n\n".join(parts), citations


async def chat(req: Request):
    question, history = parse(req)
    if not question:
        return Response('{"error": "send {\\"message\\": \\"...\\"}"}', status=400, content_type="application/json")
    # With client-supplied history the client owns the conversation; otherwise
    # the server keeps it per X-Session-Id.
    session_id = "" if history is not None else req.session_id
    return answer(question, session_id, history)


async def answer(question: str, session_id: str, history: list[dict] | None = None):
    hits = [
        h
        for h in await app.vectors.search("sources", question, k=TOP_K, mode="hybrid")
        if h.similarity >= MIN_SIMILARITY or h.keyword >= MIN_KEYWORD
    ]
    if not hits:
        set_metadata("citations", [])
        yield NO_SOURCES
        await app.memory.append(session_id, question, NO_SOURCES)
        return

    context, citations = context_block(hits)
    set_metadata("citations", citations)
    if history is None:
        history = await app.memory.history(session_id, last=HISTORY_MESSAGES)
    reply = []
    try:
        async for token in app.models.chat.stream(
            question, system=SYSTEM_PROMPT + context, history=history, temperature=0.2
        ):
            reply.append(token)
            yield token
    except ModelError as e:
        set_metadata("error", e.code)
        yield "\n\n[The model is unavailable right now. Please try again.]"
        return
    await app.memory.append(session_id, question, "".join(reply))
