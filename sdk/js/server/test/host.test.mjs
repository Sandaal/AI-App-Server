// Unit tests for the SDK's encoding helpers. The behaviour of the runtime
// against a real server is covered by scripts/e2e-conformance.sh.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import * as protoLoader from "@grpc/proto-loader";
import { toStruct, fromStruct, toBytes } from "../dist/host.js";
import { Request, Response } from "../dist/request.js";
import { guardrails } from "../dist/index.js";

const descriptor = JSON.parse(readFileSync(new URL("../src/proto.json", import.meta.url)));
const pkg = protoLoader.fromJSON(descriptor, { keepCase: true, longs: String, enums: String, defaults: true, oneofs: true });

test("Struct values survive the wire format", () => {
  const value = { s: "kitchen", n: 1.5, b: true, nil: null, list: [1, "two", { three: 3 }], nested: { deep: { x: "y" } } };
  const m = pkg["aiapp.v1.Host"].VectorSearch; // VectorSearchResponse { hits: [VectorHit { metadata: Struct }] }
  const wire = m.responseSerialize({ hits: [{ id: "1", metadata: toStruct(value) }] });
  assert.ok(wire.length > 40, "the metadata was encoded");
  assert.deepEqual(fromStruct(m.responseDeserialize(wire).hits[0].metadata), value);
});

test("toStruct drops undefined fields", () => {
  assert.deepEqual(fromStruct(toStruct({ a: 1, b: undefined })), { a: 1 });
});

test("toBytes", () => {
  assert.equal(toBytes("hé").toString(), "hé");
  assert.equal(toBytes({ a: 1 }).toString(), '{"a":1}');
  assert.equal(toBytes(new Uint8Array([104, 105])).toString(), "hi");
});

test("Request reads the invocation message", () => {
  const r = new Request({
    method: "POST", route: "/x", headers: { "x-session-id": "s1", "content-type": "application/json" },
    body: Buffer.from('{"a":1}'), session_id: "s1", invocation_id: "inv", query: { q: "1" },
    principal: { subject: "ada", roles: ["admin"], claims: { aiapp_tenant: "t1" } },
  });
  assert.deepEqual(r.json(), { a: 1 });
  assert.equal(r.sessionId, "s1");
  assert.ok(r.principal.hasRole("admin"));
  assert.equal(r.principal.tenant, "t1");
});

test("Response and guardrail decisions", () => {
  const resp = new Response({ ok: true }, { status: 201 });
  assert.equal(resp.status, 201);
  assert.deepEqual(guardrails.block("why", "msg"), { action: "block", reason: "why", message: "msg" });
  assert.deepEqual(guardrails.redact(["x"]), { action: "redact", texts: ["x"], reason: "" });
});
