import { test } from "node:test";
import assert from "node:assert/strict";
import { JSDOM } from "jsdom";
import { fakeServer, sse } from "./helpers.mjs";

const dom = new JSDOM("<!doctype html><body></body>", { url: "http://page.example/" });
for (const k of ["window", "document", "HTMLElement", "customElements", "CustomEvent", "sessionStorage", "Node", "DragEvent"]) {
  globalThis[k] = dom.window[k];
}
const { renderAnswer } = await import("../dist/elements.js");
const until = async (f, ms = 2000) => {
  const end = Date.now() + ms;
  while (!f()) { if (Date.now() > end) throw new Error("timed out"); await new Promise((r) => setTimeout(r, 10)); }
};

test("renderAnswer escapes HTML and links known citations only", () => {
  const html = renderAnswer('<img src=x onerror=alert(1)> **25 days** [1] [9]\nok', [{ n: 1, source: "a" }]);
  assert.ok(!html.includes("<img"));
  assert.ok(html.includes("<strong>25 days</strong>") && html.includes('data-n="1"') && html.includes("[9]") && html.includes("<br>"));
});

test("<aiapp-chat> streams an answer with sources and keeps a session", async () => {
  const s = await fakeServer({
    "POST /apps/hr/chat": (req, body, res) => sse(res, [["", "25 days [1]."], ["end", '{"citations":[{"n":1,"source":"leave.md","page":"2"}]}']], { split: true }),
  });
  const el = document.createElement("aiapp-chat");
  el.setAttribute("app", "hr");
  el.setAttribute("base-url", s.url);
  el.setAttribute("heading", "HR <b>bot</b>");
  el.fetchImpl = fetch;
  document.body.appendChild(el);
  let answer;
  el.addEventListener("aiapp-answer", (e) => (answer = e.detail));
  await el.ask("How many days?");
  await until(() => answer);
  const root = el.shadowRoot;
  assert.equal(root.querySelector("header").textContent, "HR <b>bot</b>"); // escaped
  assert.match(root.querySelector(".bot").textContent, /25 days \[1\]\./);
  assert.match(root.querySelector(".sources").textContent, /leave\.md, page 2/);
  const sid = s.seen[0].headers["x-session-id"];
  assert.ok(sid && sessionStorage.getItem("aiapp-session:hr") === sid);
  await el.ask("again");
  assert.equal(s.seen[1].headers["x-session-id"], sid);
  await s.close();
});

test("<aiapp-chat> shows refusals and signals sign-in", async () => {
  const s = await fakeServer({
    "POST /apps/hr/chat": (req, body, res) => { res.writeHead(401, { "Content-Type": "application/json" }); res.end('{"error":"invalid_api_key"}'); },
  });
  const el = document.createElement("aiapp-chat");
  el.setAttribute("app", "hr"); el.setAttribute("base-url", s.url); el.setAttribute("memory", "none");
  el.fetchImpl = fetch;
  document.body.appendChild(el);
  let auth = false;
  el.addEventListener("aiapp-auth-required", () => (auth = true));
  await el.ask("hi");
  assert.ok(auth);
  assert.match(el.shadowRoot.querySelector(".err").textContent, /API key or sign-in/);
  assert.equal(s.seen[0].headers["x-session-id"], undefined);
  await s.close();
});

test("<aiapp-upload> sends a file and shows the result", async () => {
  const s = await fakeServer({
    "POST /apps/inv/extract": (req, body, res) => { res.writeHead(200, { "Content-Type": "application/json" }); res.end(JSON.stringify({ state: "done", file: req.headers["x-filename"], wait: req.url })); },
  });
  const el = document.createElement("aiapp-upload");
  el.setAttribute("app", "inv"); el.setAttribute("base-url", s.url); el.setAttribute("route", "/extract"); el.setAttribute("wait", "60");
  el.fetchImpl = fetch;
  document.body.appendChild(el);
  const r = await el.send(new Blob(["total 10"], { type: "text/plain" }), "invoice.txt");
  assert.deepEqual(r, { state: "done", file: "invoice.txt", wait: "/apps/inv/extract?wait=60" });
  assert.match(el.shadowRoot.querySelector("pre").textContent, /"state": "done"/);
  await s.close();
});

test("<aiapp-approvals> lists and decides", async () => {
  let pending = [{ id: "apr_1", app: "sup", job: "j", key: "approve", title: "Refund $40?", details: { amount: 40 }, state: "pending",
    created_at: new Date().toISOString(), expires_at: new Date(Date.now() + 3600e3).toISOString() }];
  const s = await fakeServer({
    "GET /apps/sup/_approvals/pending": (req, body, res) => { res.writeHead(200, { "Content-Type": "application/json" }); res.end(JSON.stringify({ approvals: pending, you: "ann" })); },
    "POST /apps/sup/_approvals/decide": (req, body, res) => {
      pending = [];
      res.writeHead(200, { "Content-Type": "application/json" }); res.end(JSON.stringify({ ...JSON.parse(body), state: "approved" }));
    },
  });
  const el = document.createElement("aiapp-approvals");
  el.setAttribute("app", "sup"); el.setAttribute("base-url", s.url); el.setAttribute("api-key", "aiapp_x");
  el.fetchImpl = fetch;
  document.body.appendChild(el);
  await until(() => el.shadowRoot.querySelector(".title"));
  assert.equal(el.shadowRoot.querySelector(".title").textContent, "Refund $40?");
  let decided;
  el.addEventListener("aiapp-decided", (e) => (decided = e.detail.approval));
  el.shadowRoot.querySelector("input").value = "fine";
  el.shadowRoot.querySelector('button[data-approve="true"]').click();
  await until(() => decided);
  assert.deepEqual(decided, { id: "apr_1", approve: true, comment: "fine", state: "approved" });
  await until(() => /Nothing is waiting/.test(el.shadowRoot.textContent));
  assert.equal(s.seen[0].headers.authorization, "Bearer aiapp_x");
  el.remove();
  await s.close();
});
