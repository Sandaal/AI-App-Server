# Storage, memory and search

Every app has private, encrypted storage on the server: no database to install. Other apps can't see it.

## Key-value store: `app.kv`

```python
await app.kv.put("greeting", "hello", ttl=3600)        # seconds; 0 = keep
value = await app.kv.get("greeting")                    # bytes, or None
await app.kv.delete("greeting")
ok = await app.kv.cas("counter", "1", "2")    # compare-and-set: write "2" only if the value is "1"
ok = await app.kv.cas("lock", None, "me")      # None: only if the key doesn't exist yet
```

Keys live in namespaces (`namespace="orders"`, default `"default"`).

**Data structures**, like Redis:

| Kind | Calls |
|---|---|
| Counters | `incr(key, by=1)` |
| Hashes | `hset(key, {...})`, `hget`, `hgetall`, `hdel` |
| Lists | `lpush`, `rpush`, `lpop`, `rpop`, `lrange` |
| Sets | `sadd`, `srem`, `sismember`, `smembers` |
| Sorted sets | `zadd(key, {"ann": 3})`, `zincrby`, `zscore`, `zrange`, `zrangebyscore` |
| Expiry | `expire(key, ttl)`, `ttl(key)`, `type(key)`, `len(key)` |

**Leases** (a lock with a timeout), for work that only one worker may do at a time:

```python
from aiapp import LeaseHeld

try:
    async with app.kv.lease("nightly-sync", ttl=60):
        await sync()            # runs only while holding the lease; released afterwards
except LeaseHeld:
    pass                        # another worker is doing it
```

`app.kv.acquire(key, ttl)` takes or renews a lease without a `with` block (it returns `None` when someone else holds it), and `app.kv.release(lease)` frees it.

## Conversation memory: `app.memory`

```python
history = await app.memory.history(req.session_id, last=10)   # [{"role", "content"}, ...]
answer = await app.models.chat.complete(question, history=history)
await app.memory.append(req.session_id, question, answer)
await app.memory.clear(req.session_id)
```

Callers keep a conversation by sending the same `X-Session-Id` header. The built-in chat pages do this for you. Idle conversations are forgotten after 30 days.

## Vector search: `app.vectors`

Documents from [sources](documents.md) are in the `sources` collection. You can make your own collections too:

```python
await app.vectors.upsert("products", [
    {"id": "p1", "text": "Espresso machine, 15 bar", "metadata": {"category": "coffee"}},
    {"id": "p2", "text": "Burr grinder",             "metadata": {"category": "coffee"}},
])   # vectors are made with the app's embedding model when you don't pass them

hits = await app.vectors.search("products", "something to grind beans", k=3,
                                filter={"category": "coffee"}, mode="hybrid")
for h in hits:
    print(h.id, h.score, h.text, h.metadata)
```

| `mode` | Finds by |
|---|---|
| `vector` (default) | meaning |
| `keyword` | shared words (BM25), no embedding call |
| `hybrid` | both; best for exact terms like product codes |

## SQL over your databases: `app.sql`

Databases listed under `insights.databases` (read-only logins) can be queried from handlers:

```python
result = await app.sql.query("sales", "SELECT region, SUM(total) AS total FROM orders GROUP BY region")
tables = await app.sql.tables("sales")
```

## Limits

Each app has storage and vector quotas; see [Quotas and limits](../operate/quotas.md). Over the limit, writes raise `QuotaExceeded`.
