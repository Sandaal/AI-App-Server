import { test } from "node:test";
import assert from "node:assert/strict";
import { AIAppError, CONSOLE_ACTION_HEADER, ConsoleClient } from "../dist/index.js";
import { fakeServer } from "./helpers.mjs";

const json = (res, status, v) => { res.writeHead(status, { "Content-Type": "application/json" }); res.end(JSON.stringify(v)); };

test("console reads go to api/admin and actions carry the CSRF header", async () => {
  const s = await fakeServer({
    "GET /_console/me": (req, body, res) => json(res, 200, { subject: "oidc:u1", roles: ["operator"], local: false, can: { audit: false, act: true }, sign_out: true }),
    "GET /_console/api/admin/apps": (req, body, res) => json(res, 200, { apps: [{ manifest: { app: "hr" } }] }),
    "GET /_console/api/admin/audit": (req, body, res) => json(res, 200, { records: [] }),
    "GET /_console/api/admin/apps/hr%2Fx/logs": (req, body, res) => json(res, 200, { records: [{ type: "model_chat" }] }),
    "POST /_console/api/admin/apps/hr/dead/orders.dead/replay": (req, body, res) => json(res, 200, { replayed: 2 }),
    "GET /_console/api/admin/secrets": (req, body, res) => json(res, 404, { error: "not available in the console" }),
  });
  const c = new ConsoleClient({ baseUrl: s.url + "/_console/" });
  const me = await c.me();
  assert.equal(me.can.act, true);
  assert.equal((await c.apps()).apps[0].manifest.app, "hr");
  await c.audit({ app: "hr", type: "console_", since: "24h", limit: 50 });
  assert.equal(s.seen.at(-1).url, "/_console/api/admin/audit?app=hr&type=console_&since=24h&limit=50");
  assert.equal((await c.logs("hr/x")).records[0].type, "model_chat"); // app names are escaped
  assert.deepEqual(await c.replayDead("hr", "orders.dead"), { replayed: 2 });
  const post = s.seen.at(-1);
  assert.equal(post.method, "POST");
  assert.equal(post.headers[CONSOLE_ACTION_HEADER.toLowerCase()], "1");
  await assert.rejects(c.get("secrets"), (e) => e instanceof AIAppError && e.status === 404 && /not available/.test(e.message));
  await s.close();
});
