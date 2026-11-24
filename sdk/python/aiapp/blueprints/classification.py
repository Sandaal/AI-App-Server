"""Classification: sort texts into the labels defined in ai-app.yaml.

Routes
    POST /classify   ``{"text": "..."}`` (or plain text) → ``{"label", "confidence",
                     "reason"}``, or ``{"labels": [...]}`` with ``multi_label``.
                     ``{"items": [{"id": ..., "text": ...}, ...]}`` classifies up
                     to 50 texts at once.

Manifest::

    classification:
      labels:
        - { name: billing,   description: "Invoices, refunds, payment problems" }
        - { name: technical, description: "Bugs, errors, how-to questions" }
        - { name: other }
      multi_label: false
      instructions: "Tickets come from a SaaS help desk."
      topic: tickets                  # optional: classify every record published here
      output_topic: tickets.classified  # optional: publish each result here

With ``topic``, the blueprint subscribes to it (in order, at least once). Every
result, from the route or the topic, goes to ``output_topic`` when set, with
the label in the ``label`` header so consumers can route on it. Needs a ``chat``
model. Labels come out of structured output constrained to the manifest's
names, so a reply is always one of them.
"""

from __future__ import annotations

import asyncio
import json

from aiapp import ModelError, Request, Response, app

MAX_ITEMS = 50
MAX_TEXT = 20_000


def _json(obj, status=200) -> Response:
    return Response(json.dumps(obj), status=status, content_type="application/json")


def _config() -> dict:
    return app.manifest.get("classification") or {}


def _schema(cfg: dict) -> dict:
    names = [lab["name"] for lab in cfg.get("labels", [])]
    label = {"type": "string", "enum": names}
    props = {
        "confidence": {"type": "number", "minimum": 0, "maximum": 1, "description": "How sure you are, 0 to 1"},
        "reason": {"type": "string", "description": "One short sentence"},
    }
    if cfg.get("multi_label"):
        props["labels"] = {"type": "array", "items": label, "uniqueItems": True}
        required = ["labels", "confidence", "reason"]
    else:
        props["label"] = label
        required = ["label", "confidence", "reason"]
    return {"type": "object", "properties": props, "required": required}


def _system(cfg: dict) -> str:
    lines = []
    for lab in cfg.get("labels", []):
        d = lab.get("description")
        lines.append(f"- {lab['name']}" + (f": {d}" if d else ""))
    how = ("Choose every label that applies (possibly none)." if cfg.get("multi_label")
           else "Choose the single label that fits best.")
    system = f"Classify the text into these labels.\n{chr(10).join(lines)}\n{how} Only use the labels listed."
    if cfg.get("instructions"):
        system += "\n\n" + str(cfg["instructions"])
    return system


async def classify_text(text: str) -> dict:
    cfg = _config()
    out = await app.models.chat.json(text[:MAX_TEXT], schema=_schema(cfg), name="classification",
                                     system=_system(cfg), temperature=0)
    if "confidence" in out:
        out["confidence"] = max(0.0, min(1.0, float(out["confidence"])))
    return out


async def _publish(result: dict, *, key: str = "", source: dict | None = None) -> None:
    topic = _config().get("output_topic")
    if not topic:
        return
    label = result.get("label") or ",".join(result.get("labels") or [])
    await app.events.publish(topic, {**result, **({"source": source} if source else {})}, key=key,
                             headers={"label": label})


async def classify(req: Request):
    try:
        body = req.json() if req.body.lstrip().startswith(b"{") else {"text": req.text}
    except json.JSONDecodeError:
        return _json({"error": "invalid JSON"}, 400)
    try:
        if "items" in body:
            items = body["items"]
            if not isinstance(items, list) or not 0 < len(items) <= MAX_ITEMS:
                return _json({"error": f"items must be a list of 1 to {MAX_ITEMS} texts"}, 400)
            sem = asyncio.Semaphore(5)

            async def one(i, item):
                async with sem:
                    text = item.get("text", "") if isinstance(item, dict) else str(item)
                    r = await classify_text(text)
                    item_id = item.get("id", i) if isinstance(item, dict) else i
                    await _publish(r, key=str(item_id))
                    return {"id": item_id, **r}

            return _json({"results": await asyncio.gather(*[one(i, it) for i, it in enumerate(items)])})
        text = str(body.get("text") or "").strip()
        if not text:
            return _json({"error": 'send {"text": "..."} or {"items": [...]}'}, 400)
        r = await classify_text(text)
        await _publish(r)
        return _json(r)
    except ModelError as e:
        status = 429 if e.code == "budget_exceeded" else 502
        return _json({"error": str(e), "code": e.code}, status)


async def on_event(req: Request):
    """Subscription handler for ``classification.topic``: classify the record
    (its value, or its ``text`` field if it is a JSON object)."""
    ev = req.event
    try:
        data = ev.json()
    except ValueError:
        data = None
    text = data.get("text", "") if isinstance(data, dict) else ev.text
    if not str(text).strip():
        return {"skipped": "empty"}
    r = await classify_text(str(text))  # a ModelError fails the delivery, which is retried
    await _publish(r, key=ev.key or str(ev.offset), source={"topic": ev.topic, "offset": ev.offset})
    return r
