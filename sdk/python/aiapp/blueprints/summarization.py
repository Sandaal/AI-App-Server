"""Summarization: summaries of long documents, by map-reduce.

Routes
    POST /summarize   body = the document (PDF, DOCX, Markdown or text), name in
                      ``X-Filename``; or JSON ``{"text": "...", "style": ..., "max_words": ...}``.
                      Queues a durable job; ``?wait=SECONDS`` (max 60) waits for it.
                      ``style`` is ``paragraph`` (default), ``bullets`` or ``executive``;
                      ``?style=`` / ``?max_words=`` work for file uploads.
    GET  /result      ``?id=JOB_ID`` → ``{"state", "result"?, "error"?}``.

The job is a workflow. The document is split into chunks of about 12,000
characters at paragraph breaks; each chunk is summarized as a saved step
(several at once), then the chunk summaries are combined, in rounds if they
are still too long, into the final summary and its key points. A retried
or restarted job reuses the chunk summaries it already has.

``summary:`` in ai-app.yaml sets defaults (``style``, ``max_words``,
``language``); ``instructions.md`` in the app folder is added to every prompt.
Needs a ``chat`` model; documents up to 4 MB.
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid

from aiapp import ModelError, Request, Response, app
from aiapp.blueprints.document_extraction import document_text
from aiapp.system import ParseError

UPLOADS = "uploads"
UPLOAD_TTL = 7 * 24 * 3600
MAX_UPLOAD = 4 << 20
MAX_WAIT = 60
CHUNK = 12_000       # characters per map step
COMBINE = 16_000     # characters of summaries combined in one reduce step
PARALLEL = 4         # chunk summaries in flight at once
STYLES = {
    "paragraph": "Write flowing prose paragraphs.",
    "bullets": "Write the summary as concise bullet points.",
    "executive": "Write an executive summary: the conclusion first, then the facts that support it, then open questions.",
}

SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "key_points": {"type": "array", "items": {"type": "string"}, "description": "3 to 7 short key points"},
    },
    "required": ["summary", "key_points"],
}


def _json(obj, status=200) -> Response:
    return Response(json.dumps(obj), status=status, content_type="application/json")


def _config() -> dict:
    return app.manifest.get("summary") or {}


def _instructions() -> str:
    path = os.path.join(os.getcwd(), "instructions.md")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return "\n\n" + f.read()
    return ""


def chunks(text: str, size: int = CHUNK) -> list[str]:
    """Split at paragraph breaks into pieces of about size characters (a
    paragraph longer than size is split at sentence ends, then hard)."""
    paras = [p for p in text.split("\n\n") if p.strip()]
    out, cur = [], ""
    for p in paras:
        while len(p) > size:
            cut = p.rfind(". ", 0, size)
            cut = cut + 1 if cut > size // 2 else size
            pieces = [p[:cut], p[cut:].lstrip()]
            if cur:
                out.append(cur)
                cur = ""
            out.append(pieces[0])
            p = pieces[1]
        if cur and len(cur) + len(p) + 2 > size:
            out.append(cur)
            cur = p
        else:
            cur = f"{cur}\n\n{p}" if cur else p
    if cur:
        out.append(cur)
    return out


async def summarize(req: Request):
    filename = req.headers.get("x-filename", "")
    body, opts = req.body, {}
    if "json" in req.headers.get("content-type", ""):
        try:
            payload = req.json() or {}
        except json.JSONDecodeError:
            return _json({"error": "invalid JSON"}, 400)
        body = str(payload.get("text", "")).encode("utf-8")
        filename = filename or "document.txt"
        opts = {k: payload[k] for k in ("style", "max_words", "language") if k in payload}
    for k in ("style", "max_words", "language"):  # also accepted as query parameters (file uploads)
        if req.query.get(k) and k not in opts:
            opts[k] = int(req.query[k]) if k == "max_words" and req.query[k].isdigit() else req.query[k]
    if not body:
        return _json({"error": "send the document as the request body (name in X-Filename), or {\"text\": ...}"}, 400)
    if len(body) > MAX_UPLOAD:
        return _json({"error": f"documents up to {MAX_UPLOAD >> 20} MB"}, 413)
    if opts.get("style") and opts["style"] not in STYLES:
        return _json({"error": f"style must be one of {', '.join(STYLES)}"}, 400)
    upload = uuid.uuid4().hex
    await app.kv.put(upload, body, namespace=UPLOADS, ttl=UPLOAD_TTL)
    job = await app.jobs.enqueue("summarize", {"upload": upload, "filename": filename or "document.txt", "options": opts})

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


@app.workflow
async def run(wf, p):
    """The summarize job."""
    raw = await app.kv.get(p["upload"], namespace=UPLOADS)
    if raw is None:
        raise RuntimeError("the uploaded document has expired")
    try:
        text, pages = document_text(p["filename"], raw)
    except ParseError as e:
        return {"error": str(e)}
    if not text.strip():
        return {"error": "no text found (scanned PDFs need OCR, which is not supported yet)"}

    opts = {**_config(), **(p.get("options") or {})}
    style = STYLES.get(opts.get("style") or "paragraph", STYLES["paragraph"])
    max_words = int(opts.get("max_words") or 250)
    language = opts.get("language")
    lang = f" Write in {language}." if language else " Write in the document's language."
    extra = _instructions()

    parts = chunks(text)
    sem = asyncio.Semaphore(PARALLEL)

    async def summarize_part(i: int, part: str) -> str:
        async with sem:
            prompt = (f"This is part {i + 1} of {len(parts)} of a document. Summarize this part faithfully in at most "
                      f"{max(80, 3 * max_words // max(len(parts), 1))} words, keeping names, numbers, dates and "
                      f"decisions.{lang}{extra}")
            return await app.models.chat.complete(part, system=prompt, temperature=0)

    try:
        if len(parts) == 1:
            summaries = [parts[0]]  # short enough: summarize it directly
        else:
            summaries = await asyncio.gather(*[
                wf.step(f"map-{i}", summarize_part, i, part) for i, part in enumerate(parts)])
        # Reduce in rounds until the summaries fit in one prompt.
        level = 0
        while len("\n\n".join(summaries)) > COMBINE and len(summaries) > 1:
            groups = chunks("\n\n".join(summaries), COMBINE)
            level += 1
            summaries = await asyncio.gather(*[
                wf.step(f"reduce-{level}-{i}", app.models.chat.complete, g, temperature=0,
                        system=f"Combine these partial summaries of one document into one shorter summary, "
                               f"keeping the important facts.{lang}")
                for i, g in enumerate(groups)])
        async def combine() -> dict:  # wf.step's own `name` argument would clash with json(name=...)
            return await app.models.chat.json(
                "\n\n".join(summaries), schema=SUMMARY_SCHEMA, name="summary", temperature=0,
                system=(f"Summarize the document{' from these partial summaries' if len(parts) > 1 else ''}. "
                        f"{style} Use at most {max_words} words. Use only what the text says.{lang}{extra}"))

        final = await wf.step("final", combine)
    except ModelError as e:
        if e.code in ("invalid_output", "budget_exceeded"):
            return {"error": str(e)}
        raise  # provider trouble: let the job retry (finished chunks are kept)
    return {
        "filename": p["filename"],
        "pages": pages,
        "characters": len(text),
        "chunks": len(parts),
        "summary": final.get("summary", ""),
        "key_points": final.get("key_points", []),
    }
