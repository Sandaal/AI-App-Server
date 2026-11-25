// Node.js worker runtime: serves the Worker gRPC service for one app. The core
// starts it as
//
//   node aiapp-runtime.mjs --listen ADDR --host ADDR --app NAME --worker-id ID
//
// in the app's directory, with the per-worker token in AIAPP_WORKER_TOKEN. It
// exits when its stdin closes, so workers never outlive the core.
//
// This file is also the SDK: apps import "@aiapp-server/server", which the
// runtime maps to this module, so handlers share its connection to the core.

import fs from "node:fs";
import path from "node:path";
import { pathToFileURL, fileURLToPath } from "node:url";
import * as grpc from "@grpc/grpc-js";
import { SpanBuffer } from "./app.js";
import { MAX_MESSAGE, TOKEN_HEADER, connect, current, proto, toStruct, type Invocation } from "./host.js";
import { Request, Response } from "./request.js";
import { Suspended } from "./workflow.js";

export * from "./index.js";
import * as sdk from "./index.js";
(globalThis as any)[Symbol.for("aiapp.server.sdk")] = sdk; // for require("@aiapp-server/server")

const SDK_VERSION = "1.1.0";

function log(level: string, msg: string): void {
  process.stderr.write(`${level} aiapp.runtime: ${msg}\n`);
}

// --- handlers ----------------------------------------------------------------

const EXTENSIONS = [".mjs", ".js", ".cjs", ".ts", ".mts"];
const handlerCache = new Map<string, Function>();

/** Imports "module:function" from the app directory (module may be a path: lib/handlers:hello). */
export async function resolveHandler(spec: string): Promise<Function> {
  const cached = handlerCache.get(spec);
  if (cached) return cached;
  const i = spec.lastIndexOf(":");
  const modName = i > 0 ? spec.slice(0, i) : "";
  const fnName = i > 0 ? spec.slice(i + 1) : "";
  if (!modName || !fnName) throw new Error(`handler ${JSON.stringify(spec)} must look like module:function`);
  const base = path.resolve(process.cwd(), modName.replace(/\./g, "/"));
  const file = [...EXTENSIONS.map((e) => base + e), path.join(base, "index.mjs"), path.join(base, "index.js")].find((f) => fs.existsSync(f));
  if (!file) throw new Error(`no ${modName}.mjs, .js or .ts in the app folder`);
  const mod = await import(pathToFileURL(file).href);
  const fn = mod[fnName] ?? mod.default?.[fnName];
  if (typeof fn !== "function") throw new Error(`handler ${JSON.stringify(spec)} is not a function exported by ${path.basename(file)}`);
  handlerCache.set(spec, fn);
  return fn;
}

/** Imports every handler the manifest names before registering, so a broken version never becomes ready. */
async function preloadHandlers(): Promise<void> {
  let m: any = {};
  try { m = JSON.parse(process.env.AIAPP_MANIFEST || "{}"); } catch { return; }
  const specs = new Set<string>();
  for (const r of m.routes ?? []) if (r.handler) specs.add(r.handler);
  for (const key of ["subscriptions", "cron", "guardrails", "jobs"]) for (const e of m[key] ?? []) if (e?.handler) specs.add(e.handler);
  for (const s of specs) {
    if (s.startsWith("aiapp.")) continue; // Python blueprint handlers; not for this runtime
    try { await resolveHandler(s); } catch (e) {
      throw new Error(`handler ${s} can't be loaded: ${(e as Error).name}: ${(e as Error).message}`);
    }
  }
}

/** Makes `import ... from "@aiapp-server/server"` in the app resolve to this module. */
function installSdkShim(): void {
  const dir = path.join(process.cwd(), "node_modules", "@aiapp-server", "server");
  const self = import.meta.url;
  const want = `export * from ${JSON.stringify(self)};\n`;
  const indexFile = path.join(dir, "index.mjs");
  try {
    if (fs.existsSync(indexFile) && fs.readFileSync(indexFile, "utf8") === want) return;
    if (fs.existsSync(path.join(dir, "package.json")) && !fs.existsSync(indexFile)) return; // a real installed copy: it shares state through globalThis
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(path.join(dir, "package.json"), JSON.stringify({
      name: "@aiapp-server/server", version: SDK_VERSION, type: "module",
      exports: { ".": { import: "./index.mjs", require: "./index.cjs" } },
    }));
    fs.writeFileSync(indexFile, want);
    fs.writeFileSync(path.join(dir, "index.cjs"), `module.exports = globalThis[Symbol.for("aiapp.server.sdk")];\n`);
  } catch (e) {
    log("WARNING", `could not link @aiapp-server/server into the app folder: ${(e as Error).message}`);
  }
}

// --- responses -----------------------------------------------------------------

function toBuffer(item: unknown): Buffer {
  if (Buffer.isBuffer(item)) return item;
  if (item instanceof Uint8Array) return Buffer.from(item);
  if (typeof item === "string") return Buffer.from(item, "utf8");
  if (item !== null && typeof item === "object") return Buffer.from(JSON.stringify(item), "utf8");
  return Buffer.from(String(item), "utf8");
}

function toResponse(result: unknown): Response {
  if (result instanceof Response) return result;
  if (result === null || result === undefined) return new Response("", { status: 204 });
  if (Buffer.isBuffer(result) || result instanceof Uint8Array) return new Response(result, { contentType: "application/octet-stream" });
  if (typeof result === "object") return new Response(result, { contentType: "application/json" });
  return new Response(String(result), { contentType: "text/plain; charset=utf-8" });
}

const start = (status: number, headers: Record<string, string>, streaming: boolean) => ({ start: { status, headers, streaming } });
const errorChunk = (code: string, message: string) => ({ error: { code, message } });

function isAsyncIterable(v: any): v is AsyncIterable<unknown> { return v && typeof v[Symbol.asyncIterator] === "function"; }
function isIterator(v: any): v is Iterable<unknown> {
  return v && typeof v[Symbol.iterator] === "function" && typeof v.next === "function" && typeof v !== "string";
}

function parseTraceparent(tp: string): [string, string] | undefined {
  const p = (tp || "").split("-");
  if (p.length < 4 || !/^[0-9a-f]{32}$/.test(p[1]) || !/^[0-9a-f]{16}$/.test(p[2])) return undefined;
  if (/^0+$/.test(p[1]) || /^0+$/.test(p[2])) return undefined;
  return [p[1], p[2]];
}

// --- the Worker service ------------------------------------------------------------

class WorkerService {
  inFlight = 0;
  draining = false;
  server?: grpc.Server;
  connected!: Promise<void>;
  setConnected!: () => void;

  constructor(private token: string) {
    this.connected = new Promise((r) => (this.setConnected = r));
  }

  private authorized(md: grpc.Metadata): boolean { return md.get(TOKEN_HEADER)[0] === this.token; }

  async Invoke(callObj: grpc.ServerWritableStream<any, any>): Promise<void> {
    if (!this.authorized(callObj.metadata)) {
      callObj.destroy({ code: grpc.status.UNAUTHENTICATED, details: "invalid worker token" } as any);
      return;
    }
    await Promise.race([this.connected, new Promise((r) => setTimeout(r, 10_000))]);
    const msg = callObj.request;
    this.inFlight++;
    const spans = new SpanBuffer(msg.invocation_id);
    const inv: Invocation = { id: msg.invocation_id, metadata: {}, trace: parseTraceparent(msg.traceparent), spans };
    const write = (chunk: object) => new Promise<void>((resolve) => { if (!callObj.write(chunk)) callObj.once("drain", resolve); else resolve(); });
    const end = () => write({ end: { metadata: toStruct(inv.metadata) } });
    try {
      await current.run(inv, async () => {
        let fn: Function;
        try { fn = await resolveHandler(msg.handler); } catch (e) {
          log("ERROR", `cannot load handler ${msg.handler}: ${(e as Error).message}`);
          await write(errorChunk("handler_not_found", `${(e as Error).name}: ${(e as Error).message}`));
          return;
        }
        try {
          let result = await fn(new Request(msg));
          if (isAsyncIterable(result) || isIterator(result)) {
            await write(start(200, {}, true));
            for await (const item of result as AsyncIterable<unknown>) await write({ data: toBuffer(item) });
            await end();
            return;
          }
          const resp = toResponse(result);
          const headers = { ...resp.headers };
          let contentType = resp.contentType;
          if (!contentType && resp.body !== null && typeof resp.body === "object" && !Buffer.isBuffer(resp.body)) contentType = "application/json";
          if (contentType) headers["content-type"] = contentType;
          await write(start(resp.status, headers, false));
          const body = toBuffer(resp.body ?? "");
          if (body.length) await write({ data: body });
          await end();
        } catch (e) {
          if (e instanceof Suspended) {
            log("INFO", `${(e as Error).message} (invocation ${msg.invocation_id})`);
            await write(errorChunk(Suspended.code, (e as Error).message));
            return;
          }
          log("ERROR", `handler ${msg.handler} failed (invocation ${msg.invocation_id}): ${(e as Error).stack ?? e}`);
          await write(errorChunk("handler_exception", `${(e as Error).name ?? "Error"}: ${(e as Error).message ?? e}`));
        }
      });
    } finally {
      this.inFlight--;
      spans.closed = true;
      if (spans.spans.length) void spans.flush(); // after the response: spans never delay it
      callObj.end();
    }
  }

  Health(callObj: grpc.ServerUnaryCall<any, any>, cb: grpc.sendUnaryData<any>): void {
    if (!this.authorized(callObj.metadata)) return cb({ code: grpc.status.UNAUTHENTICATED, details: "invalid worker token" } as any);
    cb(null, { ready: !this.draining, in_flight: this.inFlight });
  }

  Drain(callObj: grpc.ServerUnaryCall<any, any>, cb: grpc.sendUnaryData<any>): void {
    if (!this.authorized(callObj.metadata)) return cb({ code: grpc.status.UNAUTHENTICATED, details: "invalid worker token" } as any);
    this.draining = true;
    const grace = (callObj.request.grace_seconds || 10) * 1000;
    log("INFO", `draining (grace ${grace / 1000}s)`);
    cb(null, {});
    const srv = this.server!;
    const force = setTimeout(() => { srv.forceShutdown(); process.exit(0); }, grace);
    srv.tryShutdown(() => { clearTimeout(force); process.exit(0); });
  }
}

function parseArgs(argv: string[]): Record<string, string> {
  const out: Record<string, string> = {};
  for (let i = 0; i < argv.length; i++) if (argv[i].startsWith("--")) out[argv[i].slice(2)] = argv[++i] ?? "";
  for (const k of ["listen", "host", "app", "worker-id"]) if (!out[k]) throw new Error(`--${k} is required`);
  return out;
}

async function main(): Promise<void> {
  const args = parseArgs(process.argv.slice(2));
  const token = process.env.AIAPP_WORKER_TOKEN ?? "";
  if (!token) throw new Error("AIAPP_WORKER_TOKEN is not set (the core starts this runtime)");
  // The core holds our stdin open; EOF means it is gone.
  process.stdin.on("end", () => process.exit(0));
  process.stdin.on("close", () => process.exit(0));
  process.stdin.resume();

  installSdkShim();
  await preloadHandlers();

  const svc = new WorkerService(token);
  const server = new grpc.Server({ "grpc.max_receive_message_length": MAX_MESSAGE, "grpc.max_send_message_length": MAX_MESSAGE });
  svc.server = server;
  server.addService(proto.Worker.service, {
    Invoke: svc.Invoke.bind(svc), Health: svc.Health.bind(svc), Drain: svc.Drain.bind(svc),
  });
  await new Promise<void>((resolve, reject) =>
    server.bindAsync(args.listen, grpc.ServerCredentials.createInsecure(), (err) => (err ? reject(err) : resolve())));

  const hostStub = new proto.Host(args.host, grpc.credentials.createInsecure());
  const md = new grpc.Metadata();
  md.set(TOKEN_HEADER, token);
  const resp: any = await new Promise((resolve, reject) =>
    hostStub.Register({ app: args.app, worker_id: args["worker-id"], runtime: `node${process.versions.node.split(".")[0]}`, sdk_version: SDK_VERSION },
      md, { deadline: Date.now() + 10_000 }, (err: Error | null, r: unknown) => (err ? reject(err) : resolve(r))));
  hostStub.close();
  connect(args.host, resp.session_token);
  svc.setConnected();
  log("INFO", `worker ${args["worker-id"]} registered for app ${args.app} on ${args.listen}`);
}

const isMain = process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1]);
if (isMain) {
  main().catch((e) => {
    log("ERROR", (e as Error).stack ?? String(e));
    process.exit(1);
  });
}
