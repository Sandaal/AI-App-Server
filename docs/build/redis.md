# Redis clients

The server can speak the Redis protocol. Existing code and tools that use Redis can then work with an app's data without changes:

- caches, rate limiters and session stores;
- `redis-cli`, redis-py, node-redis, go-redis and other clients.

Redis clients and the app's handlers share the data: what a client writes, `app.kv` reads, and the reverse.

## Turn it on

```bash
aiapp serve --resp-addr 127.0.0.1:6379
aiapp key create my-app --name cache --role kv      # prints the key
```

A client signs in with the app's name as the username and the key as the password. The key needs the `kv` role (or `admin`).

```bash
redis-cli -p 6379 --user my-app --pass aiapp_… PING
```

```python
import redis
r = redis.Redis(host="127.0.0.1", port=6379, username="my-app", password="aiapp_…")
```

```js
import { createClient } from "redis";
const c = createClient({ url: "redis://127.0.0.1:6379", username: "my-app", password: "aiapp_…" });
```

For clients that only send a password (a URL like `redis://:PASSWORD@host`), use `my-app:aiapp_…` as the password.

!!! warning "Use TLS beyond this machine"
    Keys are sent when a client signs in. On any address other than localhost, add `--resp-tls-cert` and `--resp-tls-key`, and connect with `rediss://`. Without them, the server warns at start.

## What you get

- **Protocols:** RESP2 and RESP3 (`HELLO 3`), and pipelining.
- **Namespace:** each app sees only its own keys, in the namespace `app.kv` uses by default.
- **Limits:** the app's [storage quota](../operate/quotas.md) and value limits apply, as for `app.kv`. A full quota answers `OOM`.
- **Durability:** every write is on disk before the reply, unlike Redis's default. On one test machine, with redis-benchmark over 16-command pipelines, writes ran at about 15,000/s and reads at about 400,000/s.

## Supported commands

| Kind | Commands |
|---|---|
| Connection | `AUTH`, `HELLO`, `PING`, `ECHO`, `QUIT`, `RESET`, `SELECT 0`, `CLIENT SETNAME/GETNAME/ID/SETINFO/INFO`, `COMMAND`, `INFO`, `TIME` |
| Strings | `GET`, `SET` (with `EX`, `PX`, `EXAT`, `PXAT`, `NX`, `XX` and `GET`), `SETNX`, `SETEX`, `PSETEX`, `MGET`, `MSET`, `GETDEL`, `STRLEN`, `INCR`, `INCRBY`, `DECR`, `DECRBY` |
| Keys | `DEL`, `UNLINK`, `EXISTS`, `EXPIRE`, `PEXPIRE`, `TTL`, `PTTL`, `TYPE` |
| Hashes | `HSET`, `HMSET`, `HGET`, `HMGET`, `HGETALL`, `HKEYS`, `HVALS`, `HDEL`, `HLEN`, `HEXISTS` |
| Lists | `LPUSH`, `RPUSH`, `LPOP`, `RPOP` (with a count), `LRANGE`, `LINDEX`, `LLEN` |
| Sets | `SADD`, `SREM`, `SMEMBERS`, `SISMEMBER`, `SCARD` |
| Sorted sets | `ZADD`, `ZINCRBY`, `ZSCORE`, `ZREM`, `ZCARD`, `ZRANGE` (with `BYSCORE`, `REV`, `LIMIT` and `WITHSCORES`), `ZREVRANGE`, `ZRANGEBYSCORE`, `ZREVRANGEBYSCORE` (with exclusive `(` bounds) |

Any other command answers with an error that says why:

| Not supported | Why, and what to use |
|---|---|
| `KEYS`, `SCAN`, `DBSIZE` | Key names are stored hashed, so they can't be listed. Keep the names you need in a set. |
| `MULTI`/`EXEC`, `WATCH`, `EVAL`, functions | Each command is atomic on its key. Use `SET … NX` (or an `app.kv` lease) to coordinate. |
| Pub/sub | Use the app's [topics](jobs-events.md), or [Kafka bridges](kafka.md). |
| Blocking commands (`BLPOP`…), streams, `ZADD` flags, bitmaps, HyperLogLog, geo | Not available. |
| `FLUSHDB`, `CONFIG`, `SHUTDOWN`… | Run the server with the `aiapp` CLI. |

## Differences from Redis

- **String expiry:** `TTL` and `PTTL` report `-1` for strings even when they will expire, because their expiry can't be read back. Expiry itself works, with one-second resolution (`PX` rounds up). Counters, hashes, lists and sets report their TTL exactly.
- **Strings and structures:** they are stored apart, but behave as Redis's do:
    - a structure command on a string answers `WRONGTYPE`;
    - `SET` replaces a structure;
    - `INCR` works on a number stored with `SET`, and on `app.kv.incr` counters.
- **Leases:** keys made by `app.kv` leases show as type `none`.
- **One database:** database 0 is the app's default namespace. Other `app.kv` namespaces aren't reachable over this protocol.
