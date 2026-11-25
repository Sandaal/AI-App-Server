# External stores

By default an app's data lives in the server's own storage. An app can keep it in systems your organization already runs instead:

| Data | External store |
|---|---|
| Key-value data: `app.kv`, `app.memory` (chat history), workflow state | Redis |
| Vectors: `app.vectors` and the app's indexed documents | PostgreSQL with pgvector, or Azure AI Search |

```yaml
storage:
  kv: { redis: "${APP_REDIS}" }                 # redis://user:password@host:6379/0, or rediss:// for TLS
  vectors: { pgvector: "${APP_PG}" }            # postgres://user:password@host:5432/db?sslmode=require
```

```yaml
storage:
  vectors:
    azure_ai_search: { endpoint: "https://contoso-search.search.windows.net", api_key: "${SEARCH_ADMIN_KEY}" }
```

Store the URLs and keys with `aiapp secret set APP_REDIS` and so on, not in the file. `kv` and `vectors` are independent: set either or both.

## What changes, and what doesn't

- **The SDK:** handlers don't change. `app.kv`, `app.memory`, `app.vectors` and document search behave the same, and the Redis-protocol listener reaches the external data too.
- **Checked at deploy:** the server connects when the app is deployed. If it can't reach a store, the deploy fails with the reason, and the running version keeps serving.
- **What stays in the server:** jobs, topics, API keys, audit and traces.
- **Existing data isn't moved:** switching an existing app to external stores starts it with empty stores. Removing `storage:` brings back what the built-in stores held.
- **Quotas:** checks on writes still apply. Measure usage in the external system itself.

## Redis

- **Versions:** Redis 6.2 or later, Valkey, Azure Cache for Redis or Amazon ElastiCache.
- **Keys:** they look like `aiapp:{APP/NAMESPACE}:v:KEY` (values), `…:s:KEY` (hashes, lists, sets, sorted sets, counters) and `…:l:KEY` (leases). The braces keep an app's namespace in one Redis Cluster slot.
- **Atomic operations:** compare-and-set and leases are Lua scripts, so they stay atomic.
- **Expiry:** uses Redis's own.

## PostgreSQL with pgvector

- **Setup:** the `vector` extension must be installed, or creatable by the user. The server creates the table `aiapp_collections` and one table per collection (`aiapp_v_…`).
- **Indexes:** each collection table has an HNSW cosine index on the vectors, full-text search on the texts and a GIN index on the metadata.
- **Search modes:** `mode="vector"` uses the vector index, `"keyword"` uses Postgres full-text search, and `"hybrid"` fuses both rankings.
- **Managed services:** Azure Database for PostgreSQL, Amazon RDS and Supabase work where pgvector is enabled.

## Azure AI Search

- **Indexes:** one per collection, named `aiapp-…`, created on first use with an HNSW cosine vector field, the text (searchable) and the metadata (filterable).
- **Search modes:** `"keyword"` uses the service's BM25, and `"hybrid"` its built-in fusion.
- **Key:** use an admin key, which is needed to create indexes.

!!! warning "Azure AI Search: not yet tested against the service"
    The adapter is tested against a fake of the REST API (version 2024-07-01), not yet against an Azure AI Search service. Redis and pgvector are tested against real servers.
