"""Three routes showing the handler basics. Start here and change them."""

from aiapp import Response, app


async def hello(req):
    """POST /hello {"name": "Ada"} -> {"greeting": "Hello, Ada!"}"""
    body = req.json() or {}
    name = str(body.get("name", "")).strip()
    if not name:
        return Response({"error": "send a name"}, status=400)
    return {"greeting": f"Hello, {name}!"}


async def translate(req):
    """POST /translate {"text": "...", "to": "French"} -> {"translation": "..."}"""
    body = req.json() or {}
    text = await app.models.chat.complete(
        body.get("text", ""),
        system=f"Translate the user's text into {body.get('to', 'French')}. Reply with the translation only.",
        temperature=0,
    )
    return {"translation": text.strip()}


async def chat(req):
    """POST /chat {"message": "..."} with header X-Session-Id to keep the conversation."""
    question = (req.json() or {}).get("message", "")
    history = await app.memory.history(req.session_id, last=10)
    answer = ""
    async for part in app.models.chat.stream(question, history=history, system="You are a friendly assistant."):
        answer += part
        yield part                                    # sent to the caller as it arrives
    await app.memory.append(req.session_id, question, answer)
