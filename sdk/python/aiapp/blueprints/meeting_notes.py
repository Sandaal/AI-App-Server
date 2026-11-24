"""Meeting notes: from a recording or a transcript to a summary, decisions,
action items (with owners and due dates) and open questions.

Routes
    POST /notes    body = a recording (mp3, m4a, wav, webm, ogg, flac; up to 25 MB),
                   name in ``X-Filename``; or a transcript, as a text file (.txt, .vtt,
                   .srt) or JSON ``{"transcript": "...", "title": "..."}``.
                   Queues a durable job; ``?wait=SECONDS`` (max 60) waits for it.
    GET  /result   ``?id=JOB_ID`` → ``{"state", "result"?, "error"?}``.

The job is a workflow: the transcript (from the ``transcribe`` model) is a
saved step, so a retry never pays for transcription twice. Long transcripts
are read in parts whose notes are then merged.

``meeting_notes:`` in ai-app.yaml sets ``language`` (transcription hint and
output language) and ``vocabulary`` (names and terms to spell correctly).
Needs a ``chat`` model, and a ``transcribe`` model for recordings.
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid

from aiapp import ModelError, Request, Response, app
from aiapp.blueprints.summarization import chunks

UPLOADS = "uploads"
UPLOAD_TTL = 7 * 24 * 3600
PART = 3 << 20          # KV values are limited to 4 MB: recordings are stored in parts
MAX_AUDIO = 25 << 20
MAX_WAIT = 60
CHUNK = 40_000          # transcript characters read at once
TEXT_EXT = {"txt", "vtt", "srt", "md"}  # transcripts sent as files
AUDIO_EXT = {"mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm", "ogg", "oga", "flac"}

NOTES_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "A short title for the meeting"},
        "summary": {"type": "string", "description": "What the meeting was about and what came out of it, in a few sentences"},
        "attendees": {"type": "array", "items": {"type": "string"}, "description": "People who spoke or were named as present"},
        "decisions": {"type": "array", "items": {"type": "string"}},
        "action_items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "task": {"type": "string"},
                    "owner": {"type": "string", "description": "Who will do it, if said"},
                    "due": {"type": "string", "description": "When, as said in the meeting, if said"},
                },
                "required": ["task"],
            },
        },
        "open_questions": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["title", "summary", "decisions", "action_items"],
}


def _json(obj, status=200) -> Response:
    return Response(json.dumps(obj), status=status, content_type="application/json")


def _config() -> dict:
    return app.manifest.get("meeting_notes") or {}


def _instructions() -> str:
    path = os.path.join(os.getcwd(), "instructions.md")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return "\n\n" + f.read()
    return ""


async def notes(req: Request):
    filename = req.headers.get("x-filename", "")
    payload = {"filename": filename or "recording"}
    ctype = req.headers.get("content-type", "")
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    is_text = ctype.startswith("text/") or ext in TEXT_EXT
    if "json" in ctype or is_text or req.body.lstrip().startswith(b"{"):
        if is_text and "json" not in ctype:
            body = {"transcript": req.text}
        else:
            try:
                body = req.json() or {}
            except json.JSONDecodeError:
                return _json({"error": "invalid JSON"}, 400)
        transcript = str(body.get("transcript", "")).strip()
        if not transcript:
            return _json({"error": 'send a recording as the body (name in X-Filename), or {"transcript": "..."}'}, 400)
        upload = uuid.uuid4().hex
        await app.kv.put(upload, transcript, namespace=UPLOADS, ttl=UPLOAD_TTL)
        payload.update({"transcript_upload": upload, "title": body.get("title", "")})
    else:
        audio = req.body
        if not audio:
            return _json({"error": 'send a recording as the body (name in X-Filename), or {"transcript": "..."}'}, 400)
        if ext not in AUDIO_EXT:
            return _json({"error": "name the recording in X-Filename with its format, e.g. meeting.mp3 "
                                   "(mp3, m4a, wav, webm, ogg or flac)"}, 400)
        if len(audio) > MAX_AUDIO:
            return _json({"error": f"recordings up to {MAX_AUDIO >> 20} MB (split longer meetings)"}, 413)
        if "transcribe" not in (app.manifest.get("models") or {}):
            return _json({"error": "this app has no transcribe model; add one under models: or send a transcript"}, 400)
        upload = uuid.uuid4().hex
        parts = [audio[i:i + PART] for i in range(0, len(audio), PART)]
        for i, part in enumerate(parts):
            await app.kv.put(f"{upload}/{i}", part, namespace=UPLOADS, ttl=UPLOAD_TTL)
        payload.update({"audio_upload": upload, "parts": len(parts)})
    job = await app.jobs.enqueue("notes", payload)

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


async def _transcribe(p: dict) -> dict:
    audio = b""
    for i in range(p["parts"]):
        part = await app.kv.get(f"{p['audio_upload']}/{i}", namespace=UPLOADS)
        if part is None:
            raise RuntimeError("the uploaded recording has expired")
        audio += part
    cfg = _config()
    vocab = cfg.get("vocabulary") or []
    t = await app.models.transcribe.transcribe(audio, filename=p["filename"], language=cfg.get("language"),
                                               prompt=", ".join(vocab) if vocab else None)
    return {"text": t.text, "duration": t.duration_seconds, "language": t.language, "segments": len(t.segments)}


@app.workflow
async def run(wf, p):
    """The notes job."""
    try:
        if p.get("audio_upload"):
            tr = await wf.step("transcript", _transcribe, p)
        else:
            text = await app.kv.get(p["transcript_upload"], namespace=UPLOADS)
            if text is None:
                raise RuntimeError("the uploaded transcript has expired")
            tr = {"text": text.decode("utf-8"), "duration": 0, "language": "", "segments": 0}
        text = tr["text"].strip()
        if not text:
            return {"error": "the recording has no speech the model could transcribe"}

        lang = _config().get("language")
        lang_rule = f" Write in {lang}." if lang else " Write in the meeting's language."
        rules = (" Use only what was said; leave out owners and dates that weren't mentioned rather than guessing."
                 f"{lang_rule}{_instructions()}")
        title = p.get("title") or ""
        parts = chunks(text, CHUNK)

        async def notes_for(i: int, part: str) -> dict:
            where = f"part {i + 1} of {len(parts)} of " if len(parts) > 1 else ""
            return await app.models.chat.json(part, schema=NOTES_SCHEMA, name="meeting_notes", temperature=0,
                                              system=f"These are {where}a meeting transcript. Write meeting notes."
                                                     + rules)

        partial = await asyncio.gather(*[wf.step(f"notes-{i}", notes_for, i, part) for i, part in enumerate(parts)])
        if len(partial) == 1:
            final = partial[0]
        else:
            async def merge() -> dict:
                return await app.models.chat.json(
                    json.dumps(partial), schema=NOTES_SCHEMA, name="meeting_notes", temperature=0,
                    system="Merge these notes from consecutive parts of one meeting into one set of notes: one title "
                           "and summary, every decision and action item once." + rules)

            final = await wf.step("merge", merge)
    except ModelError as e:
        if e.code in ("invalid_output", "budget_exceeded") or (e.code == "transcription_error" and not e.retryable):
            return {"error": str(e)}
        raise  # provider trouble: let the job retry (finished steps are kept)
    if title:
        final["title"] = title
    return {
        "filename": p.get("filename"),
        "duration_seconds": tr.get("duration") or None,
        "language": tr.get("language") or None,
        "transcript": text,
        "parts": len(parts),
        **final,
    }
