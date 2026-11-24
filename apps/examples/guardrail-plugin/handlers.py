from aiapp import app


async def ask(req):
    return await app.models.chat.complete((req.json() or {}).get("question", ""), system="You are Contoso's product assistant.")
