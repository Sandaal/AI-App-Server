"""Content studio: from a brief to reviewed, approved content.

Routes
    POST /drafts   ``{"brief": "...", "kind": "blog|email|social|product|other", "audience": ..., "tone": ...,
                   "words": 400}`` → queues a draft job, ``{"job": id, "state": ...}``.
    GET  /drafts   ``?id=JOB_ID`` → state, the current draft and the review history.

The job is a workflow: an outline, a first draft, then review rounds. Each
round waits for a person's approval (the app's approvals page or ``aiapp
approve``), with the draft in the approval's details. Approve, and the draft
is published to the ``content.approved`` topic and is the job's result.
Reject with a comment, and the model revises the draft from the comment and
asks again, up to ``max_rounds``. Every step is saved, so a restart never
writes a draft twice.

``content:`` in ai-app.yaml sets ``instructions`` (brand voice and rules),
``max_rounds`` (default 3), ``publish_topic`` and ``review_timeout``.
``instructions.md`` in the app folder is added too. Needs a ``chat`` model.
"""

from __future__ import annotations

import json
import os
import re

from aiapp import ModelError, Request, Response, app

KINDS = {
    "blog": "a blog post with a title, short intro, sections with headings, and a conclusion",
    "email": "a marketing or customer email with a subject line and a clear call to action",
    "social": "a set of three short social media posts, each under 280 characters",
    "product": "a product description: one headline, a short paragraph and 3-5 benefit bullets",
    "other": "the piece described in the brief",
}
DRAFTS = "drafts"  # the live view of each job: current draft and reviews


def _json(obj, status=200) -> Response:
    return Response(json.dumps(obj), status=status, content_type="application/json")


def _config() -> dict:
    return app.manifest.get("content") or {}


def _voice() -> str:
    voice = str(_config().get("instructions") or "")
    path = os.path.join(os.getcwd(), "instructions.md")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            voice += "\n\n" + f.read()
    return voice.strip()


def _duration(text: str | None, default: float) -> float:
    m = re.fullmatch(r"(\d+(?:\.\d+)?)(s|m|h|d)", (text or "").strip())
    return float(m.group(1)) * {"s": 1, "m": 60, "h": 3600, "d": 86400}[m.group(2)] if m else default


async def drafts(req: Request):
    if req.method == "GET" or not req.body:
        job_id = req.query.get("id", "")
        if not job_id:
            return _json({"error": 'POST {"brief": "..."} to start a draft, or GET ?id=JOB_ID to read one'}, 400)
        try:
            job = await app.jobs.get(job_id)
        except Exception:
            return _json({"error": "draft not found"}, 404)
        view = json.loads(await app.kv.get(job_id, namespace=DRAFTS) or b"{}")
        out = {"job": job.id, "state": job.state, **view}
        if job.state == "waiting":
            out["note"] = "waiting for a reviewer: approve or reject it on the approvals page (/_approvals/)"
        if job.state == "done":
            out.update(job.result or {})
        if job.last_error:
            out["error"] = job.last_error
        return _json(out)
    try:
        body = req.json() or {}
    except json.JSONDecodeError:
        return _json({"error": "invalid JSON"}, 400)
    brief = str(body.get("brief") or "").strip()
    if not brief:
        return _json({"error": 'send {"brief": "...", "kind": "blog"}'}, 400)
    kind = body.get("kind") or "blog"
    if kind not in KINDS:
        return _json({"error": f"kind must be one of {', '.join(KINDS)}"}, 400)
    spec = {"brief": brief[:4000], "kind": kind, "audience": str(body.get("audience") or "")[:300],
            "tone": str(body.get("tone") or "")[:100], "words": int(body.get("words") or 400)}
    job = await app.jobs.enqueue("draft", spec)
    return _json({"job": job.id, "state": job.state}, 202)


async def _save_view(job_id: str, view: dict) -> bool:
    await app.kv.put(job_id, json.dumps(view), namespace=DRAFTS, ttl=90 * 86400)
    return True


def _brief_text(p: dict) -> str:
    lines = [f"Brief: {p['brief']}", f"Format: {KINDS[p['kind']]}", f"Length: about {p['words']} words"]
    if p.get("audience"):
        lines.append(f"Audience: {p['audience']}")
    if p.get("tone"):
        lines.append(f"Tone: {p['tone']}")
    return "\n".join(lines)


@app.workflow
async def run(wf, p):
    """The draft job."""
    cfg = _config()
    voice = _voice()
    system = "You are a skilled content writer. Write in clear, natural language. Don't invent facts, figures or quotes."
    if voice:
        system += "\n\nBrand voice and rules:\n" + voice
    brief = _brief_text(p)
    max_rounds = max(1, int(cfg.get("max_rounds") or 3))
    timeout = _duration(cfg.get("review_timeout"), 3 * 86400)
    view = {"kind": p["kind"], "brief": p["brief"], "reviews": []}
    try:
        outline = await wf.step("outline", app.models.chat.complete,
                                f"{brief}\n\nWrite a short outline (bullet points) for this piece.", system=system,
                                temperature=0.4)
        draft = await wf.step("draft-1", app.models.chat.complete,
                              f"{brief}\n\nOutline:\n{outline}\n\nWrite the piece. Reply with the piece only.",
                              system=system, temperature=0.7)
        for rnd in range(1, max_rounds + 1):
            view.update({"round": rnd, "draft": draft, "outline": outline})
            await wf.step(f"view-{rnd}", _save_view, wf.job_id, view)
            d = await wf.approval(f"review-{rnd}", f"Review {p['kind']} draft: {p['brief'][:60]}",
                                  {"brief": p["brief"], "kind": p["kind"], "round": rnd, "draft": draft},
                                  timeout=timeout)
            view["reviews"].append({"round": rnd, "state": d.state, "by": d.by, "comment": d.comment})
            if d.approved:
                topic = cfg.get("publish_topic") or "content.approved"
                await wf.step("publish", app.events.publish, topic,
                              {"kind": p["kind"], "brief": p["brief"], "content": draft, "approved_by": d.by,
                               "rounds": rnd}, key=wf.job_id)
                view["approved"] = True
                await wf.step("view-final", _save_view, wf.job_id, view)
                return {"approved": True, "content": draft, "rounds": rnd, "approved_by": d.by,
                        "reviews": view["reviews"], "published_to": topic}
            if d.state == "expired" or not d.comment or rnd == max_rounds:
                break
            draft = await wf.step(f"draft-{rnd + 1}", app.models.chat.complete,
                                  f"{brief}\n\nCurrent draft:\n{draft}\n\nReviewer's comments:\n{d.comment}\n\n"
                                  "Revise the draft to address every comment. Reply with the revised piece only.",
                                  system=system, temperature=0.5)
    except ModelError as e:
        if e.code == "budget_exceeded":
            return {"approved": False, "error": str(e), "reviews": view["reviews"]}
        raise
    view["approved"] = False
    await wf.step("view-final", _save_view, wf.job_id, view)
    return {"approved": False, "content": draft, "rounds": len(view["reviews"]), "reviews": view["reviews"]}
