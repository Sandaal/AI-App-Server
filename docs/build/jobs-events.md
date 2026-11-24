# Jobs, schedules and events

## Background jobs

For work that takes long, must not be lost, or should retry. Jobs survive restarts.

```yaml
jobs:
  - { name: report, handler: "handlers:report", max_attempts: 3, timeout: 10m }
job_concurrency: 2        # jobs of this app that run at once (optional)
```

```python
async def report(req):                 # the payload is the request body
    period = req.json()["period"]
    ...
    return {"rows": 120}                # stored as the job's result

async def start(req):                  # a route that starts it
    job = await app.jobs.enqueue("report", {"period": "2026-Q3"}, delay=0, key="report-2026-Q3")
    return {"job": job.id}             # key: the same key while running = the same job
```

```python
job = await app.jobs.get(job_id)       # job.state: queued, running, waiting, done, dead, canceled
```

A job that fails is retried with backoff; after `max_attempts` it is **dead**. From the CLI: `aiapp jobs APP`, `aiapp jobs show|retry|cancel APP ID`; or the [console](../operate/console.md).

## Schedules (cron)

```yaml
cron:
  - name: nightly-report
    schedule: "0 2 * * *"         # 5-field cron, or @hourly, @daily, @every 15m
    job: report
    payload: { period: yesterday }
    timezone: Europe/Paris        # default UTC
```

`aiapp cron APP` shows next runs; `aiapp cron run APP NAME` runs one now.

## Events (topics)

Topics are durable event streams inside the app, like a small Kafka.

```yaml
topics:
  orders: { partitions: 4, retention: 7d }    # optional settings; topics are created on first publish
subscriptions:
  - { topic: orders, handler: "handlers:on_order", max_attempts: 5 }
```

```python
await app.events.publish("orders", {"id": 42, "total": 99.0}, key="customer-7")

async def on_order(req):
    ev = req.event                  # ev.topic, ev.offset, ev.key, ev.partition, ev.delivery
    order = req.json()              # the record's value
    ...
```

- **Order:** records with the same `key` go to the same partition and are delivered in order; different partitions are handled in parallel.
- **Delivery:** at least once; `ev.delivery` counts attempts, so make handlers safe to repeat.
- **Failures:** after `max_attempts` a record moves to `TOPIC.dead` (a dead-letter topic).

### Dead letters

```bash
aiapp dead APP                              # dead-letter topics and how many are waiting
aiapp dead show APP orders.dead             # look at them
aiapp dead replay APP orders.dead           # after fixing the handler, send them again
aiapp dead purge APP orders.dead --yes      # or delete them
```

The [console](../operate/console.md) can replay and purge too.

### Read topics yourself

```python
batch = await app.events.fetch("orders", "billing", member="worker-1", limit=100, wait=5)  # a consumer group
for ev in batch.records:
    ...
await app.events.ack(batch, "billing")
```

Members of a consumer group share the topic's partitions automatically. `aiapp topics APP` shows topics and each consumer's lag; `aiapp publish APP TOPIC JSON` publishes by hand.
