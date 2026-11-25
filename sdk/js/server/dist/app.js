// The app object handlers use: models, storage, search, jobs, events, tools,
// spans. It mirrors the Python SDK (aiapp.app), in JavaScript style.
import { randomBytes } from "node:crypto";
import { call, current, fromStruct, stream, toBytes, toStruct } from "./host.js";
import { Event } from "./request.js";
/** A provider call failed after the core's retries and fallback. */
export class ModelError extends Error {
    code;
    retryable;
    constructor(code, message, retryable = false) {
        super(message);
        this.name = "ModelError";
        this.code = code;
        this.retryable = retryable;
    }
}
function invocationId() { return current.getStore()?.id ?? ""; }
function imagePart(im) {
    let data, mime;
    if (Buffer.isBuffer(im) || im instanceof Uint8Array)
        data = Buffer.from(im);
    else {
        data = Buffer.from(im.data);
        mime = im.mimeType;
    }
    if (!mime) {
        if (data.subarray(0, 4).toString("hex") === "89504e47")
            mime = "image/png";
        else if (data.subarray(0, 3).toString("hex") === "ffd8ff")
            mime = "image/jpeg";
        else if (data.subarray(0, 4).toString() === "GIF8")
            mime = "image/gif";
        else if (data.subarray(0, 4).toString() === "RIFF" && data.subarray(8, 12).toString() === "WEBP")
            mime = "image/webp";
    }
    if (!mime || !["image/png", "image/jpeg", "image/gif", "image/webp"].includes(mime)) {
        throw new Error("images must be PNG, JPEG, GIF or WebP (pass { data, mimeType } if detection fails)");
    }
    return { mime_type: mime, data };
}
function buildMessages(user, o) {
    const out = [];
    if (o.system)
        out.push({ role: "system", content: o.system });
    for (const m of [...(o.history ?? []), ...(o.messages ?? [])]) {
        out.push({
            role: m.role, content: m.content ?? "", tool_call_id: m.tool_call_id ?? "",
            tool_calls: (m.tool_calls ?? []).map((t) => ({ id: t.id, name: t.name, arguments_json: JSON.stringify(t.arguments) })),
            images: (m.images ?? []).map(imagePart),
        });
    }
    if (user !== undefined || o.images?.length)
        out.push({ role: "user", content: user ?? "", images: (o.images ?? []).map(imagePart) });
    if (!out.length)
        throw new Error("give a user message, messages or history");
    return out;
}
function options(o, extra = {}) {
    const opts = { ...extra };
    if (o.temperature !== undefined)
        opts.temperature = o.temperature;
    if (o.maxTokens !== undefined)
        opts.max_tokens = o.maxTokens;
    return toStruct(opts);
}
/** Declares a tool: `app.tool({ name, description, parameters }, fn)`. */
export function tool(spec, fn) {
    return { name: spec.name, description: spec.description, parameters: spec.parameters ?? { type: "object", properties: {} }, fn };
}
/** A logical model from the manifest's `models:` section. */
export class Model {
    name;
    constructor(name) {
        this.name = name;
    }
    /** Yields the answer as it streams. */
    async *stream(user, o = {}) {
        const req = { invocation_id: invocationId(), model: this.name, messages: buildMessages(user, o), options: options(o) };
        for await (const chunk of stream("ChatStream", req)) {
            if (chunk.kind === "delta")
                yield chunk.delta;
            else if (chunk.kind === "error")
                throw new ModelError(chunk.error.code, chunk.error.message, chunk.error.retryable);
        }
    }
    /** Returns the whole answer as one string. */
    async complete(user, o = {}) {
        let text = "";
        for await (const t of this.stream(user, o))
            text += t;
        return text;
    }
    /** Asks for JSON matching schema (a JSON Schema object) and returns it parsed. */
    async json(user, o) {
        const req = {
            invocation_id: invocationId(), model: this.name, messages: buildMessages(user, o),
            options: options(o, { json_schema: o.schema, schema_name: o.name ?? "output" }),
        };
        let text = "";
        for await (const chunk of stream("ChatStream", req)) {
            if (chunk.kind === "delta")
                text += chunk.delta;
            else if (chunk.kind === "error")
                throw new ModelError(chunk.error.code, chunk.error.message, chunk.error.retryable);
        }
        return JSON.parse(text);
    }
    /** One model turn with tools offered: { text, calls }. */
    async turn(messages, o = {}) {
        const req = {
            invocation_id: invocationId(), model: this.name, messages: buildMessages(undefined, { system: o.system, history: messages }),
            options: options(o), tools: (o.tools ?? []).map((t) => ({ name: t.name, description: t.description ?? "", parameters_json: JSON.stringify(t.parameters ?? {}) })),
        };
        let text = "";
        const calls = [];
        for await (const chunk of stream("ChatStream", req)) {
            if (chunk.kind === "delta")
                text += chunk.delta;
            else if (chunk.kind === "tool_call")
                calls.push({ id: chunk.tool_call.id, name: chunk.tool_call.name, arguments: JSON.parse(chunk.tool_call.arguments_json || "{}") });
            else if (chunk.kind === "error")
                throw new ModelError(chunk.error.code, chunk.error.message, chunk.error.retryable);
        }
        return { text, calls };
    }
    /**
     * Lets the model use tools until it can answer. With mcp (default true),
     * the app's MCP servers' tools are offered too. A failing tool is reported
     * to the model as an error rather than thrown.
     */
    async run(user, o = {}) {
        const local = new Map((o.tools ?? []).map((t) => [t.name, t]));
        let offered = [...local.values()].map((t) => ({ name: t.name, description: t.description, parameters: t.parameters }));
        if (o.mcp ?? true) {
            const listed = await call("ToolList", {});
            offered = offered.concat((listed.tools ?? []).filter((t) => !local.has(t.name))
                .map((t) => ({ name: t.name, description: t.description, parameters: JSON.parse(t.parameters_json || "{}") })));
        }
        const convo = [...(o.history ?? [])];
        if (user !== undefined)
            convo.push({ role: "user", content: user });
        const steps = [];
        for (let i = 0; i < (o.maxSteps ?? 8); i++) {
            const reply = await this.turn(convo, { tools: offered, system: o.system, temperature: o.temperature });
            if (!reply.calls.length) {
                convo.push({ role: "assistant", content: reply.text });
                return { text: reply.text, steps, messages: convo };
            }
            convo.push({ role: "assistant", content: reply.text, tool_calls: reply.calls });
            for (const c of reply.calls) {
                const step = { tool: c.name, arguments: c.arguments, result: null, error: null };
                let result;
                try {
                    const t = local.get(c.name);
                    if (t) {
                        const v = await t.fn(c.arguments);
                        result = typeof v === "string" ? v : JSON.stringify(v);
                    }
                    else {
                        const r = await call("ToolCall", { invocation_id: invocationId(), name: c.name, arguments_json: JSON.stringify(c.arguments) });
                        result = r.content;
                        if (r.is_error)
                            step.error = result;
                    }
                }
                catch (e) {
                    result = `Error: ${e.name}: ${e.message}`;
                    step.error = result;
                }
                step.result = result.slice(0, 2000);
                steps.push(step);
                convo.push({ role: "tool", tool_call_id: c.id, content: result });
            }
        }
        throw new ModelError("max_steps", `no answer after ${o.maxSteps ?? 8} rounds of tool calls`, false);
    }
    /** Embeds texts with this (embedding) model. */
    async embed(inputs) {
        const r = await call("Embed", { invocation_id: invocationId(), model: this.name, inputs });
        return (r.vectors ?? []).map((v) => v.values);
    }
    /** Turns a recording into text with this (speech-to-text) model. */
    async transcribe(audio, o = {}) {
        const r = await call("Transcribe", { invocation_id: invocationId(), model: this.name, audio, filename: o.filename ?? "audio.mp3", language: o.language ?? "", prompt: o.prompt ?? "" });
        return { text: r.text, language: r.language, durationSeconds: r.duration_seconds };
    }
}
/** The app's private key-value store and data structures (values are Buffers; strings are UTF-8). */
export class KV {
    async get(key, o = {}) {
        const r = await call("KVGet", { namespace: o.namespace ?? "default", key });
        return r.found ? Buffer.from(r.value) : null;
    }
    /** Stores value; ttl (seconds) > 0 makes it expire. */
    async put(key, value, o = {}) {
        await call("KVPut", { namespace: o.namespace ?? "default", key, value: toBytes(value), ttl_seconds: String(o.ttl ?? 0) });
    }
    async delete(key, o = {}) {
        await call("KVDelete", { namespace: o.namespace ?? "default", key });
        await this.op("delete", key, o.namespace);
    }
    op(op, key, namespace = "default", fields = {}) {
        return call("KVOp", { namespace, key, op, ...fields });
    }
    /** Compare-and-set: write value only if the current value equals expected (null: only if absent). value null deletes. */
    async cas(key, expected, value, o = {}) {
        const f = { ttl_ms: String(Math.round((o.ttl ?? 0) * 1000)) };
        if (expected === null)
            f.expect_absent = true;
        else
            f.expected = toBytes(expected);
        if (value === null)
            f.delete_value = true;
        else
            f.value = toBytes(value);
        return (await this.op("cas", key, o.namespace, f)).ok;
    }
    async incr(key, by = 1, o = {}) {
        return Number((await this.op("incr", key, o.namespace, { delta: by })).n);
    }
    async expire(key, ttl, o = {}) {
        return (await this.op("expire", key, o.namespace, { ttl_ms: String(Math.round(ttl * 1000)) })).ok;
    }
    async hset(key, fields, o = {}) {
        const names = Object.keys(fields);
        return Number((await this.op("hset", key, o.namespace, { fields: names, values: names.map((n) => toBytes(fields[n])) })).n);
    }
    async hget(key, field, o = {}) {
        const r = await this.op("hget", key, o.namespace, { fields: [field] });
        return r.ok ? Buffer.from(r.value) : null;
    }
    async hgetall(key, o = {}) {
        const r = await this.op("hgetall", key, o.namespace);
        return Object.fromEntries(r.fields.map((f, i) => [f, Buffer.from(r.values[i])]));
    }
    async rpush(key, values, o = {}) {
        return Number((await this.op("rpush", key, o.namespace, { values: values.map(toBytes) })).n);
    }
    async lpush(key, values, o = {}) {
        return Number((await this.op("lpush", key, o.namespace, { values: values.map(toBytes) })).n);
    }
    async lrange(key, start = 0, stop = -1, o = {}) {
        return (await this.op("lrange", key, o.namespace, { start: String(start), stop: String(stop) })).values.map((v) => Buffer.from(v));
    }
    async sadd(key, members, o = {}) {
        return Number((await this.op("sadd", key, o.namespace, { fields: members })).n);
    }
    async smembers(key, o = {}) {
        return (await this.op("smembers", key, o.namespace)).fields;
    }
}
/** Conversation memory: the last messages of each session. */
export class Memory {
    kv;
    static namespace = "memory";
    static maxMessages = 40;
    static ttl = 30 * 24 * 3600;
    constructor(kv) {
        this.kv = kv;
    }
    async history(sessionId, last = 10) {
        if (!sessionId)
            return [];
        const raw = await this.kv.get(sessionId, { namespace: Memory.namespace });
        const msgs = raw ? JSON.parse(raw.toString("utf8")) : [];
        return last > 0 ? msgs.slice(-last) : msgs;
    }
    async append(sessionId, user, assistant) {
        if (!sessionId)
            return;
        let msgs = await this.history(sessionId, 0);
        msgs = msgs.concat([{ role: "user", content: user }, { role: "assistant", content: assistant }]).slice(-Memory.maxMessages);
        await this.kv.put(sessionId, JSON.stringify(msgs), { namespace: Memory.namespace, ttl: Memory.ttl });
    }
    async clear(sessionId) { await this.kv.delete(sessionId, { namespace: Memory.namespace }); }
}
/** The app's private vector collections; ingested documents are in "sources". */
export class Vectors {
    /** Best matches first. mode: "vector" (meaning), "keyword" (BM25) or "hybrid". */
    async search(collection, query, o = {}) {
        const req = { collection, k: o.k ?? 5, filter: toStruct(o.filter), mode: o.mode ?? "vector" };
        if (typeof query === "string")
            req.query_text = query;
        else
            req.query_vector = { values: query };
        const r = await call("VectorSearch", req);
        return (r.hits ?? []).map((h) => ({
            id: h.id, score: h.score, text: h.text, similarity: h.similarity, keyword: h.keyword,
            metadata: Object.fromEntries(Object.entries(fromStruct(h.metadata)).map(([k, v]) => [k, String(v)])),
        }));
    }
    /** records: { id, text, vector?, metadata? }. Missing vectors are embedded. */
    async upsert(collection, records) {
        const r = await call("VectorUpsert", {
            collection,
            records: records.map((x) => ({ id: x.id, text: x.text ?? "", metadata: toStruct(x.metadata), ...(x.vector ? { vector: { values: x.vector } } : {}) })),
        });
        return r.upserted;
    }
}
function job(info) {
    const result = info.result?.length ? JSON.parse(Buffer.from(info.result).toString("utf8")) : null;
    return { id: info.id, name: info.name, state: info.state, attempts: info.attempts, maxAttempts: info.max_attempts, lastError: info.last_error, result };
}
/** Durable background jobs declared under `jobs:`. */
export class Jobs {
    /** Queues a job. With key, an unfinished job with the same key is returned instead of a duplicate. */
    async enqueue(name, payload = null, o = {}) {
        return job(await call("JobEnqueue", { name, payload: Buffer.from(JSON.stringify(payload)), delay_ms: String(Math.round((o.delay ?? 0) * 1000)), key: o.key ?? "" }));
    }
    async get(id) { return job(await call("JobGet", { id })); }
}
function batch(topic, r) {
    const records = (r.records ?? []).map((x) => new Event(topic, Number(x.offset), x.key, new Date(Number(x.time_unix_ms)).toISOString(), x.headers ?? {}, Buffer.from(x.value ?? []), 1, Number(r.partition ?? 0)));
    return { records, nextOffset: Number(r.next_offset ?? 0), partition: Number(r.partition ?? 0), assigned: (r.assigned ?? []).map(Number) };
}
/** Event topics: publish, and read with consumer groups. */
export class Events {
    async publish(topic, value, o = {}) {
        const r = await call("EventPublish", { topic, records: [{ key: o.key ?? "", headers: o.headers ?? {}, value: toBytes(value) }] });
        return Number(r.first_offset);
    }
    async publishMany(topic, values, o = {}) {
        const r = await call("EventPublish", { topic, records: values.map((v) => ({ key: o.key ?? "", headers: o.headers ?? {}, value: toBytes(v) })) });
        return Number(r.first_offset);
    }
    /** Records after consumer's committed position; call ack(batch, consumer) once handled. */
    async fetch(topic, consumer, o = {}) {
        const r = await call("EventRead", { topic, consumer, member: o.member ?? "", limit: o.limit ?? 100, wait_ms: String(Math.round((o.wait ?? 0) * 1000)) });
        return batch(topic, r);
    }
    async ack(b, consumer) {
        if (!b.records.length)
            return;
        await call("EventCommit", { topic: b.records[0].topic, consumer, next_offset: String(b.nextOffset), partition: b.partition });
    }
}
/** Read-only SQL over the databases under `insights:`. */
export class SQL {
    async query(database, query) {
        const r = await call("SQLQuery", { database, query });
        return { columns: r.columns, rows: JSON.parse(r.rows_json || "[]"), truncated: r.truncated };
    }
}
// --- spans -----------------------------------------------------------------
/** Finished spans of one invocation, sent to the core in batches. */
export class SpanBuffer {
    invocation;
    spans = [];
    closed = false;
    constructor(invocation) {
        this.invocation = invocation;
    }
    add(rec) {
        this.spans.push(rec);
        if (this.closed || this.spans.length >= 100)
            void this.flush();
    }
    async flush() {
        const spans = this.spans;
        this.spans = [];
        if (!spans.length)
            return;
        try {
            await call("RecordSpans", { invocation_id: this.invocation, spans });
        }
        catch { /* tracing never fails a handler */ }
    }
}
function nowNs() { return BigInt(Date.now()) * 1000000n + process.hrtime.bigint() % 1000000n; }
/** A step in the request's trace; see app.span(). */
export class Span {
    name;
    attrs;
    error = "";
    traceId = "";
    spanId = "";
    parentId = "";
    start = 0n;
    constructor(name, attrs = {}) {
        this.name = name;
        this.attrs = { ...attrs };
    }
    set(key, value) { this.attrs[key] = value; return this; }
    fail(message) { this.error = message; return this; }
    get traceparent() { return this.spanId ? `00-${this.traceId}-${this.spanId}-01` : ""; }
    /** Runs fn inside the span: calls made in it (models, storage, tools) become its children. */
    async run(fn) {
        const parent = current.getStore();
        if (parent?.trace)
            [this.traceId, this.parentId] = parent.trace;
        else
            this.traceId = randomBytes(16).toString("hex");
        this.spanId = randomBytes(8).toString("hex");
        this.start = nowNs();
        const inner = { id: parent?.id ?? "", metadata: parent?.metadata ?? {}, trace: [this.traceId, this.spanId], spans: parent?.spans };
        try {
            return await current.run(inner, () => fn(this));
        }
        catch (e) {
            if (!this.error)
                this.error = `${e.name}: ${e.message}`;
            throw e;
        }
        finally {
            const rec = {
                trace_id: this.traceId, span_id: this.spanId, parent_span_id: this.parentId, name: this.name,
                start_unix_nano: this.start.toString(), end_unix_nano: nowNs().toString(),
                attributes: toStruct(Object.fromEntries(Object.entries(this.attrs).map(([k, v]) => [k, typeof v === "object" && v !== null ? JSON.stringify(v) : v]))),
                error: this.error,
            };
            const sink = parent?.spans ?? Object.assign(new SpanBuffer(parent?.id ?? ""), { closed: true });
            sink.add(rec);
        }
    }
}
// --- the app ---------------------------------------------------------------
export class App {
    models = new Proxy({}, {
        get: (cache, name) => {
            if (typeof name !== "string")
                return undefined;
            return (cache[name] ??= new Model(name));
        },
    });
    kv = new KV();
    memory = new Memory(this.kv);
    vectors = new Vectors();
    jobs = new Jobs();
    events = new Events();
    sql = new SQL();
    /** Declares a tool for app.models.X.run: `app.tool({ name, description, parameters }, fn)`. */
    tool = tool;
    /** Runs fn as a step of the request's trace: `await app.span("rerank", { k: 8 }, async (s) => ...)`. */
    span(name, attrs, fn) {
        return new Span(name, attrs).run(fn);
    }
    /** `{ traceparent }` for the current request or span, to send to services you call. */
    traceHeaders() {
        const t = current.getStore()?.trace;
        return t ? { traceparent: `00-${t[0]}-${t[1]}-01` } : {};
    }
    /** The app's parsed ai-app.yaml, as the core loaded it. */
    get manifest() { return JSON.parse(process.env.AIAPP_MANIFEST || "{}"); }
    /** The app's MCP tools: [{ name, description, parameters }]. */
    async mcpTools() {
        const r = await call("ToolList", {});
        return (r.tools ?? []).map((t) => ({ name: t.name, description: t.description, parameters: JSON.parse(t.parameters_json || "{}") }));
    }
    /** Runs one MCP tool through the core: [text, isError]. */
    async callMcpTool(name, args) {
        const r = await call("ToolCall", { invocation_id: invocationId(), name, arguments_json: JSON.stringify(args) });
        return [r.content, r.is_error];
    }
}
export const app = (globalThis[Symbol.for("aiapp.server.app")] ??= new App());
/** Adds JSON metadata to the current response's end event (e.g. citations). */
export function setMetadata(key, value) {
    const inv = current.getStore();
    if (!inv)
        throw new Error("setMetadata is only available inside a handler");
    inv.metadata[key] = value;
}
