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

const pkgDef = protoLoader.fromJSON(descriptor as object, {
  keepCase: true, longs: String, enums: String, defaults: true, oneofs: true,
});
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const proto: any = (grpc.loadPackageDefinition(pkgDef) as any).aiapp.v1;

/** Per-invocation context, carried across awaits. */
export interface Invocation {
  id: string;
  metadata: Record<string, unknown>;      // sent with the response's end event
  trace?: [traceId: string, spanId: string]; // the active span
  spans?: SpanSink;                        // finished app.span() spans
}

export interface SpanSink { add(rec: unknown): void }

// Process-wide, so a second copy of the SDK (an app that installed the package
// itself) shares the runtime's context and connection.
const G = globalThis as any;
export const current: AsyncLocalStorage<Invocation> = (G[Symbol.for("aiapp.server.als")] ??= new AsyncLocalStorage<Invocation>());

/** Runs fn with ctx as the current invocation (spans nest by updating `trace`). */
export function withInvocation<T>(ctx: Invocation, fn: () => T): T {
  return current.run(ctx, fn);
}

const CLIENT = Symbol.for("aiapp.server.client");

export function connect(target: string, token: string): void {
  const stub = new proto.Host(target, grpc.credentials.createInsecure(), {
    "grpc.max_receive_message_length": MAX_MESSAGE, "grpc.max_send_message_length": MAX_MESSAGE,
  });
  G[CLIENT] = { stub, token };
}

export function hostClient(): { stub: any; token: string } {
  const client = G[CLIENT];
  if (!client) throw new Error("not connected to the core; handlers run inside `aiapp serve`");
  return client;
}

/** gRPC metadata for a Host call: worker token, invocation, trace context. */
export function metadata(): grpc.Metadata {
  const md = new grpc.Metadata();
  md.set(TOKEN_HEADER, hostClient().token);
  const inv = current.getStore();
  if (inv?.id) md.set(INVOCATION_HEADER, inv.id);
  if (inv?.trace) md.set("traceparent", `00-${inv.trace[0]}-${inv.trace[1]}-01`);
  return md;
}

/** Calls a unary Host method and returns its response (as a promise). */
export function call<T = any>(method: string, request: object): Promise<T> {
  const c = hostClient();
  return new Promise((resolve, reject) => {
    c.stub[method](request, metadata(), (err: grpc.ServiceError | null, resp: T) => (err ? reject(mapError(err)) : resolve(resp)));
  });
}

/** Calls a server-streaming Host method and yields its messages. */
export async function* stream<T = any>(method: string, request: object): AsyncGenerator<T> {
  const s = hostClient().stub[method](request, metadata());
  try {
    for await (const msg of s) yield msg as T;
  } catch (err) {
    throw mapError(err as grpc.ServiceError);
  }
}

/** The storage quota is used up (storage or vectors); reads still work. */
export class QuotaExceeded extends Error {
  constructor(message: string) { super(message); this.name = "QuotaExceeded"; }
}

/** A core call failed (bad input, not found, unavailable...). */
export class HostError extends Error {
  code: string;
  constructor(code: string, message: string) { super(message); this.name = "HostError"; this.code = code; }
}

function mapError(err: grpc.ServiceError): Error {
  if (!err || typeof err.code !== "number") return err as Error;
  const name = grpc.status[err.code] ?? String(err.code);
  if (err.code === grpc.status.RESOURCE_EXHAUSTED) return new QuotaExceeded(err.details || err.message);
  return new HostError(name, err.details || err.message);
}

// --- google.protobuf.Struct <-> plain JSON --------------------------------
// protobufjs's built-in google.protobuf.Value uses camelCase field names
// (keepCase applies only to our own messages).

export function toValue(v: unknown): object {
  if (v === null || v === undefined) return { nullValue: "NULL_VALUE" };
  if (typeof v === "number") return { numberValue: v };
  if (typeof v === "boolean") return { boolValue: v };
  if (typeof v === "string") return { stringValue: v };
  if (Array.isArray(v)) return { listValue: { values: v.map(toValue) } };
  if (typeof v === "object") return { structValue: toStruct(v as Record<string, unknown>) };
  return { stringValue: String(v) };
}

export function toStruct(obj: Record<string, unknown> | undefined | null): object {
  const fields: Record<string, object> = {};
  for (const [k, v] of Object.entries(obj ?? {})) if (v !== undefined) fields[k] = toValue(v);
  return { fields };
}

export function fromValue(v: any): unknown {
  if (!v) return null;
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

export function fromStruct(s: any): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(s?.fields ?? {})) out[k] = fromValue(v);
  return out;
}

export function toBytes(v: unknown): Buffer {
  if (Buffer.isBuffer(v)) return v;
  if (v instanceof Uint8Array) return Buffer.from(v);
  if (typeof v === "string") return Buffer.from(v, "utf8");
  return Buffer.from(JSON.stringify(v), "utf8");
}
