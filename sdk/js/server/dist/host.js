// The connection to the core: the gRPC Host service (models, storage, jobs,
// events, tools...) and the per-invocation context (which request a call is
// for, and the active trace span).
import { AsyncLocalStorage } from "node:async_hooks";
import * as grpc from "@grpc/grpc-js";
import * as protoLoader from "@grpc/proto-loader";
import descriptor from "./proto.json" with { type: "json" };
export const TOKEN_HEADER = "x-aiapp-token";
export const INVOCATION_HEADER = "x-aiapp-invocation";
export const MAX_MESSAGE = 32 << 20;
const pkgDef = protoLoader.fromJSON(descriptor, {
    keepCase: true, longs: String, enums: String, defaults: true, oneofs: true,
});
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const proto = grpc.loadPackageDefinition(pkgDef).aiapp.v1;
// Process-wide, so a second copy of the SDK (an app that installed the package
// itself) shares the runtime's context and connection.
const G = globalThis;
export const current = (G[Symbol.for("aiapp.server.als")] ??= new AsyncLocalStorage());
/** Runs fn with ctx as the current invocation (spans nest by updating `trace`). */
export function withInvocation(ctx, fn) {
    return current.run(ctx, fn);
}
const CLIENT = Symbol.for("aiapp.server.client");
export function connect(target, token) {
    const stub = new proto.Host(target, grpc.credentials.createInsecure(), {
        "grpc.max_receive_message_length": MAX_MESSAGE, "grpc.max_send_message_length": MAX_MESSAGE,
    });
    G[CLIENT] = { stub, token };
}
export function hostClient() {
    const client = G[CLIENT];
    if (!client)
        throw new Error("not connected to the core; handlers run inside `aiapp serve`");
    return client;
}
/** gRPC metadata for a Host call: worker token, invocation, trace context. */
export function metadata() {
    const md = new grpc.Metadata();
    md.set(TOKEN_HEADER, hostClient().token);
    const inv = current.getStore();
    if (inv?.id)
        md.set(INVOCATION_HEADER, inv.id);
    if (inv?.trace)
        md.set("traceparent", `00-${inv.trace[0]}-${inv.trace[1]}-01`);
    return md;
}
/** Calls a unary Host method and returns its response (as a promise). */
export function call(method, request) {
    const c = hostClient();
    return new Promise((resolve, reject) => {
        c.stub[method](request, metadata(), (err, resp) => (err ? reject(mapError(err)) : resolve(resp)));
    });
}
/** Calls a server-streaming Host method and yields its messages. */
export async function* stream(method, request) {
    const s = hostClient().stub[method](request, metadata());
    try {
        for await (const msg of s)
            yield msg;
    }
    catch (err) {
        throw mapError(err);
    }
}
/** The storage quota is used up (storage or vectors); reads still work. */
export class QuotaExceeded extends Error {
    constructor(message) { super(message); this.name = "QuotaExceeded"; }
}
/** A core call failed (bad input, not found, unavailable...). */
export class HostError extends Error {
    code;
    constructor(code, message) { super(message); this.name = "HostError"; this.code = code; }
}
function mapError(err) {
    if (!err || typeof err.code !== "number")
        return err;
    const name = grpc.status[err.code] ?? String(err.code);
    if (err.code === grpc.status.RESOURCE_EXHAUSTED)
        return new QuotaExceeded(err.details || err.message);
    return new HostError(name, err.details || err.message);
}
// --- google.protobuf.Struct <-> plain JSON --------------------------------
// protobufjs's built-in google.protobuf.Value uses camelCase field names
// (keepCase applies only to our own messages).
export function toValue(v) {
    if (v === null || v === undefined)
        return { nullValue: "NULL_VALUE" };
    if (typeof v === "number")
        return { numberValue: v };
    if (typeof v === "boolean")
        return { boolValue: v };
    if (typeof v === "string")
        return { stringValue: v };
    if (Array.isArray(v))
        return { listValue: { values: v.map(toValue) } };
    if (typeof v === "object")
        return { structValue: toStruct(v) };
    return { stringValue: String(v) };
}
export function toStruct(obj) {
    const fields = {};
    for (const [k, v] of Object.entries(obj ?? {}))
        if (v !== undefined)
            fields[k] = toValue(v);
    return { fields };
}
export function fromValue(v) {
    if (!v)
        return null;
    // Decoded messages name the set field in `kind`; values built by toValue don't.
    const kind = v.kind ?? ["numberValue", "stringValue", "boolValue", "structValue", "listValue"].find((k) => v[k] !== undefined);
    switch (kind) {
        case "numberValue": return v.numberValue;
        case "stringValue": return v.stringValue;
        case "boolValue": return v.boolValue;
        case "structValue": return fromStruct(v.structValue);
        case "listValue": return (v.listValue?.values ?? []).map(fromValue);
        default: return null;
    }
}
export function fromStruct(s) {
    const out = {};
    for (const [k, v] of Object.entries(s?.fields ?? {}))
        out[k] = fromValue(v);
    return out;
}
export function toBytes(v) {
    if (Buffer.isBuffer(v))
        return v;
    if (v instanceof Uint8Array)
        return Buffer.from(v);
    if (typeof v === "string")
        return Buffer.from(v, "utf8");
    return Buffer.from(JSON.stringify(v), "utf8");
}
