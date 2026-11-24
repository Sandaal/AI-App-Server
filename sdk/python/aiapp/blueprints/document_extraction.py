"""Document extraction: pull the fields in the app's ``schema.json`` out of
uploaded documents, with the page and a quote as evidence for each field.

Routes
    POST /extract   body = the document (PDF, DOCX, Markdown or text), name in
                    ``X-Filename``; or JSON ``{"text": "..."}``. Queues a durable
                    job and answers 202 with ``{"job": id, "state": ...}``.
                    ``?wait=SECONDS`` (max 60) waits for the result instead.
    GET  /result    ``?id=JOB_ID`` → ``{"state", "result"?, "error"?}``.

Job ``extract`` does the work, so uploads survive restarts and failed model
calls are retried. ``instructions.md`` in the app folder, if present, is added
to the prompt. Needs a ``chat`` model; documents up to 4 MB.
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid

from aiapp import ModelError, Request, Response, app
from aiapp.system import ParseError, parse_docx, parse_pdf

UPLOADS = "uploads"
UPLOAD_TTL = 7 * 24 * 3600
MAX_UPLOAD = 4 << 20
MAX_TEXT = 60_000  # characters sent to the model; longer documents are cut
MAX_WAIT = 60


def _json(obj, status=200) -> Response:
    return Response(json.dumps(obj), status=status, content_type="application/json")


def load_schema() -> dict:
    with open(os.path.join(os.getcwd(), "schema.json"), encoding="utf-8") as f:
        return json.load(f)


def evidence_schema(schema: dict) -> dict:
    """Wrap the app's schema: the fields, plus where each came from."""
    return {
        "type": "object",
        "properties": {
            "data": schema,
            "evidence": {
                "type": "object",
                "description": "For each top-level field of data that has a value: the page it is on and a short exact quote.",
                "additionalProperties": {
                    "type": "object",
                    "properties": {"page": {"type": "integer"}, "quote": {"type": "string"}},
                    "required": ["quote"],
                },
            },
        },
        "required": ["data"],
    }


def document_text(filename: str, data: bytes) -> tuple[str, int]:
    """Text with [page N] markers (when the format has pages), and the page count."""
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if ext == "pdf":
        pages = parse_pdf(data)
    elif ext == "docx":
        pages = parse_docx(data)
    else:
        pages = [{"page": 0, "text": data.decode("utf-8", errors="replace")}]
    parts = []
    for p in pages:
        if p["text"].strip():
            parts.append(f"[page {p['page']}]\n{p['text']}" if p["page"] else p["text"])
    return "\n\n".join(parts), len(pages)


async def extract(req: Request):
    filename = req.headers.get("x-filename", "")
    body = req.body
    if "json" in req.headers.get("content-type", ""):
        try:
            payload = req.json() or {}
        except json.JSONDecodeError:
            return _json({"error": "invalid JSON"}, 400)
        body = str(payload.get("text", "")).encode("utf-8")
        filename = filename or "document.txt"
    if not body:
        return _json({"error": "send the document as the request body (name in X-Filename), or {\"text\": ...}"}, 400)
    if len(body) > MAX_UPLOAD:
        return _json({"error": f"documents up to {MAX_UPLOAD >> 20} MB"}, 413)
    upload = uuid.uuid4().hex
    await app.kv.put(upload, body, namespace=UPLOADS, ttl=UPLOAD_TTL)
    job = await app.jobs.enqueue("extract", {"upload": upload, "filename": filename or "document.txt"})

    wait = min(float(req.query.get("wait", "0") or 0), MAX_WAIT)
    deadline = asyncio.get_running_loop().time() + wait
    while wait > 0 and job.state in ("queued", "running") and asyncio.get_running_loop().time() < deadline:
        await asyncio.sleep(0.5)
        job = await app.jobs.get(job.id)
    if job.state in ("done", "dead"):
        return _json(_view(job))
    return _json({"job": job.id, "state": job.state}, 202)


async def result(req: Request):
    job_id = req.query.get("id") or req.text.strip()
    if not job_id:
        return _json({"error": "pass ?id=JOB_ID"}, 400)
    try:
        job = await app.jobs.get(job_id)
    except Exception:
        return _json({"error": "job not found"}, 404)
    return _json(_view(job))


def _view(job) -> dict:
    out = {"job": job.id, "state": job.state, "attempts": job.attempts}
    if job.state == "done":
        out["result"] = job.result
    if job.last_error:
        out["error"] = job.last_error
    return out


async def run(req: Request):
    """The extract job: parse, extract with the model, return data + evidence."""
    p = req.json()
    raw = await app.kv.get(p["upload"], namespace=UPLOADS)
    if raw is None:
        raise RuntimeError("the uploaded document has expired")
    try:
        text, pages = document_text(p["filename"], raw)
    except ParseError as e:
        return {"error": str(e)}  # retrying won't help: finish with the reason
    if not text.strip():
        return {"error": "no text found (scanned PDFs need OCR, which is not supported yet)"}
    truncated = len(text) > MAX_TEXT
    text = text[:MAX_TEXT]

    system = (
        "Extract the requested fields from the document. Use only what the document says; "
        "omit fields it does not contain rather than guessing. For each field you fill in, give the "
        "page number from the [page N] markers (if any) and a short exact quote as evidence."
    )
    instructions = os.path.join(os.getcwd(), "instructions.md")
    if os.path.exists(instructions):
        with open(instructions, encoding="utf-8") as f:
            system += "\n\n" + f.read()
    try:
        out = await app.models.chat.json(text, schema=evidence_schema(load_schema()), name="extraction",
                                         system=system, temperature=0)
    except ModelError as e:
        if e.code == "invalid_output":
            return {"error": "the model could not produce data matching schema.json"}
        raise  # provider trouble: let the job retry
    return {
        "filename": p["filename"],
        "pages": pages,
        "truncated": truncated,
        "data": out.get("data", {}),
        "evidence": out.get("evidence", {}),
    }
