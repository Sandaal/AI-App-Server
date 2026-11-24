import random


async def tip(req):
    return {"tip": random.choice(["Ask about returns.", "Ask how refunds are paid."])}
