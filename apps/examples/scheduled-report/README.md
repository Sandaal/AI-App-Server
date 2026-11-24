# Scheduled job and events

A nightly job (cron) writes a report with the model and publishes it as an event; a subscription reacts to it. Jobs retry, events are durable, failures go to a dead-letter topic you can replay.

| | |
|---|---|
| `ai-app.yaml` | the app |
| `handlers.py` | the job, the subscriber and two routes |
| `tests/` | tests: `aiapp test` |

## Run it

With a running server ([install](https://sandaal.github.io/aiapp-server/install/)) and a model key (`aiapp secret set OPENAI_API_KEY`):

```bash
cd scheduled-report
aiapp test      # runs with scripted models: no key or cost
aiapp deploy
```

Try it:

```bash
curl -X POST http://127.0.0.1:8080/apps/scheduled-report/run      # run the job now
curl -X POST http://127.0.0.1:8080/apps/scheduled-report/latest   # what the subscriber stored
aiapp cron scheduled-report && aiapp topics scheduled-report
```

## Extend it

- Change the schedule (`cron:`) and the data source (`todays_figures`).
- In `on_report`, post to Teams or Slack, send an email, or call your API.
- If the subscriber fails, `aiapp dead replay scheduled-report reports.dead` sends the reports again after your fix.

## Change it and redeploy

Copy the folder into your own repository, change it (`aiapp dev` redeploys on every save), run `aiapp test`, then `aiapp deploy` to your server. `aiapp rollback` goes back.

Guide: [Jobs Events](https://sandaal.github.io/aiapp-server/build/jobs-events/)
