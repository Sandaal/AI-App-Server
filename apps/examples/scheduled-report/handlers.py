"""daily_report runs every morning (cron) or on POST /run; it summarises the
day's figures and publishes the report. on_report is called for each
published report: here it stores it, in your app it might post to Teams,
email someone, or update a dashboard."""

import json

from aiapp import app


def todays_figures() -> dict:
    return {"orders": 182, "revenue": 23940.5, "refunds": 3}      # replace with your database or API


async def daily_report(req):
    figures = todays_figures()
    summary = await app.models.chat.complete(
        json.dumps(figures), system="Write a two-sentence daily summary of these shop figures for the team.")
    await app.events.publish("reports", {"figures": figures, "summary": summary.strip()}, key="daily")
    return {"published": True}


async def on_report(req):
    report = req.json()
    await app.kv.put("latest-report", json.dumps(report))


async def run_now(req):
    job = await app.jobs.enqueue("daily-report")
    return {"job": job.id}


async def latest(req):
    raw = await app.kv.get("latest-report")
    return json.loads(raw) if raw else {}
