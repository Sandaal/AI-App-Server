# Kafka and Event Hubs

An app can exchange events with an existing Kafka cluster or Azure Event Hubs namespace through bridges:

- **Source bridges** bring a Kafka topic's records into one of the app's [topics](jobs-events.md), where subscriptions handle them.
- **Sink bridges** send one of the app's topics out to Kafka.

```yaml
topics:
  orders:  { retention: 7d }
  replies: { retention: 7d }
subscriptions:
  - { topic: orders, handler: "handlers:on_order" }
kafka:
  - name: orders-in                     # Kafka -> app
    brokers: ["${KAFKA_BROKERS}"]
    tls: true
    sasl: { mechanism: SCRAM-SHA-512, username: aiapp, password: "${KAFKA_PASSWORD}" }
    source: { topic: shop.orders, into: orders, start: earliest }
  - name: replies-out                   # app -> Kafka
    brokers: ["${KAFKA_BROKERS}"]
    tls: true
    sasl: { mechanism: SCRAM-SHA-512, username: aiapp, password: "${KAFKA_PASSWORD}" }
    sink: { from: replies, topic: shop.replies }
```

Keep credentials out of the file: `aiapp secret set KAFKA_PASSWORD`, and refer to it as `${KAFKA_PASSWORD}`. Key Vault and Vault references (`${kv:…}`, `${vault:…}`) work too.

## Azure Event Hubs

Event Hubs speaks the Kafka protocol. Give the namespace's connection string, and the server sets the broker (port 9093), TLS and sign-in itself:

```yaml
kafka:
  - name: telemetry-in
    event_hubs: "${EVENTHUBS_CONNECTION_STRING}"
    source: { topic: telemetry, into: telemetry }     # topic: the event hub's name
```

The Kafka endpoint needs the Standard tier or higher.

## Settings

| Setting | Meaning |
|---|---|
| `name` | the bridge's name (also used for its consumer position) |
| `brokers` | `host:port` seed brokers; a secret may hold a comma-separated list |
| `event_hubs` | an Event Hubs connection string, instead of `brokers` |
| `tls`, `ca_file` | connect with TLS; trust this CA (PEM file) instead of the system's |
| `sasl` | `mechanism` `PLAIN` (needs `tls`), `SCRAM-SHA-256` or `SCRAM-SHA-512`, with `username` and `password` |
| `source.topic`, `source.into` | the Kafka topic, and the app topic it is copied into (declared under `topics:`) |
| `source.group` | the Kafka consumer group (default `aiapp.APP.NAME`) |
| `source.start` | where a new group starts: `latest` (default) or `earliest` |
| `sink.from`, `sink.topic` | the app topic, and the Kafka topic it is copied to |
| `sink.start` | where the first run starts: `earliest` (default) or `latest` |

## What arrives, and how reliably

- **Source records:** they keep their key, value and headers. They also get the headers `kafka-topic`, `kafka-partition` and `kafka-offset`, which handlers read as `req.event.headers`.
- **Sink records:** they go out with the app record's key, value, headers and time. They are produced with `acks=all`.
- **At least once:** a bridge commits its position (Kafka offsets for a source, the app topic's position for a sink) only after the records are stored on the other side. After a crash a batch may arrive twice, never zero times, so make handlers safe to repeat.
- **Order:** a source keeps the order within each Kafka partition.
- **Limits:** the app's storage quota and any event guardrails (`events: [topic]`) apply to records a source brings in, as for `app.events.publish`.
- **Failures:** a bridge that loses its brokers, or is refused, retries with backoff (up to a minute) and never skips records.
- **Topics that don't exist:** a sink creates the Kafka topic where the brokers allow automatic creation. Otherwise, create it first.

## Watch them

```bash
aiapp kafka my-app
```

```text
BRIDGE       DIRECTION  KAFKA TOPIC   APP TOPIC   STATE     MOVED  LAST RECORD  LAST ERROR
orders-in    source     shop.orders   -> orders   running   1204   14:02:11     -
replies-out  sink       shop.replies  <- replies  retrying  97     13:58:40     produce to shop.replies: …
```

The server log has the same errors, with the app and bridge names. Bridges start when the app is deployed and stop when it is removed. A redeploy restarts them where they left off.
