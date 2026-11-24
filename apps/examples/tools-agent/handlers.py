from aiapp import app
from tools import check_stock, delivery_days


async def ask(req):
    """POST /ask {"question": "..."}: the model uses the tools, then answers."""
    result = await app.models.chat.run(
        (req.json() or {}).get("question", ""),
        tools=[check_stock, delivery_days],
        system="You are a shop assistant. Check stock and delivery with the tools before answering.",
        max_steps=6,
    )
    return {"answer": result.text, "tools_used": [s["tool"] for s in result.steps]}
