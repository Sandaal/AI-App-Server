# JavaScript handlers (Node.js)

Handlers can be written in JavaScript instead of Python. Set `runtime: node` in `ai-app.yaml`. Everything else works the same way, through the same server features:

- routes and roles,
- models and storage,
- jobs, workflows and events,
- guardrails, tracing and tests.

```bash
aiapp new node-app my-js-app --provider openai
cd my-js-app && aiapp deploy
```

```yaml
app: my-js-app
version: "1"
runtime: node
models:
  chat: { provider: openai, model: gpt-4o-mini }
routes:
  - { path: /hello, handler: "handlers:hello" }               # handlers.mjs, function hello
  - { path: /chat, handler: "handlers:chat", stream: true }
```

`handlers:hello` is the function `hello` exported from `handlers.mjs`. The server also looks for `handlers.js`, `handlers.cjs`, `handlers.ts` and `handlers.mts`, in that order.

!!! info "What the server needs"
    A `node` executable, version 20 or later. The Docker image includes Node 22. On other installs, put `node` on the `PATH`, or point `--node` (or `AIAPP_NODE`) at it. The SDK itself ships inside the server.

## The request and the answer

```js
import { app, Response, setMetadata } from "@aiapp-server/server";

export async function hello(req) {
  req.method;       // "POST"
  req.json();       // parsed JSON body (null if empty)
  req.text;         // body as text;  req.body is a Buffer
  req.query;        // { page: "2" } from ?page=2
  req.headers;      // lower-case names
  req.sessionId;    // from the X-Session-Id header
  req.invocationId; // the id shown in aiapp trace
  req.principal;    // .subject, .roles, .claims, .hasRole("approver"), .tenant

  return { greeting: "Hello" };                       // an object: JSON
  // return "text";                                   // text
  // return new Response({ id: 42 }, { status: 201, headers: { "X-Id": "42" } });
}

// An async generator streams (Server-Sent Events).
export async function* chat(req) {
  const question = req.json()?.message ?? "";
  const history = await app.memory.history(req.sessionId, 10);
  let answer = "";
  for await (const part of app.models.chat.stream(question, { history, system: "Be brief." })) {
    answer += part;
    yield part;
  }
  await app.memory.append(req.sessionId, question, answer);
  setMetadata("turns", history.length / 2 + 1); // added to the stream's final "end" event
}
```

If a handler throws, the caller gets a 500 with the invocation id. The error and its stack go to the server log and `aiapp trace`.

## Models

```js
const text = await app.models.chat.complete("Summarize: ...", { system: "Be brief.", temperature: 0.2 });

for await (const t of app.models.chat.stream("Explain ...", { history })) { /* ... */ }

const invoice = await app.models.chat.json(req.text, {
  schema: { type: "object", properties: { total: { type: "number" } }, required: ["total"] },
});

const [vector] = await app.models.embedding.embed(["some text"]);
```

Provider errors throw `ModelError`, which has `.code` (for example `budget_exceeded`) and `.retryable`.

## Tools and agents

```js
const stock = app.tool(
  { name: "stock", description: "Units in stock for a product.",
    parameters: { type: "object", properties: { product: { type: "string" } }, required: ["product"] } },
  async ({ product }) => ({ product, inStock: await lookUp(product) }),
);

export async function ask(req) {
  const result = await app.models.chat.run(req.json().question, { tools: [stock], maxSteps: 6 });
  return { answer: result.text, tools: result.steps.map((s) => s.tool) };
}
```

`run` calls the model, runs the tools it asks for and repeats until it answers. With `mcp: true`, it also uses the tools of the app's MCP servers.

## Storage

```js
await app.kv.put("greeting", "hi", { ttl: 3600 });
(await app.kv.get("greeting"))?.toString();          // a Buffer, or null
await app.kv.incr("visits");
await app.kv.cas("state", "draft", "published");     // true if it was "draft"
await app.kv.hset("user:1", { name: "Ada" });  await app.kv.hgetall("user:1");
await app.kv.rpush("queue", ["a", "b"]);       await app.kv.lrange("queue");
await app.kv.sadd("tags", ["x", "y"]);         await app.kv.smembers("tags");

await app.vectors.upsert("notes", [{ id: "1", text: "the kettle boils water", metadata: { room: "kitchen" } }]);
const hits = await app.vectors.search("notes", "how do I boil water?", { k: 4, mode: "hybrid" });
const docs = await app.vectors.search("sources", question, { k: 4 }); // the app's ingested documents

const rows = await app.sql.query("crm", "SELECT name FROM customers LIMIT 5");
```

## Jobs, workflows and events

```yaml
jobs:
  - { name: refund, handler: "handlers:refund", max_attempts: 3 }
topics:
  notes: { retention: 7d }
subscriptions:
  - { topic: notes, handler: "handlers:onNote" }
```

```js
import { app, workflow } from "@aiapp-server/server";

export async function start(req) {
  const job = await app.jobs.enqueue("refund", { orderId: req.json().orderId });
  return { job: job.id };
}

// A durable workflow: finished steps are saved, and approvals wait without holding a worker.
export const refund = workflow(async (wf, input) => {
  const order = await wf.step("lookup", () => lookUpOrder(input.orderId));
  if (order.total > 100) {
    const decision = await wf.approval("refund", `Refund ${order.total}?`, order);
    if (!decision.approved) return { refunded: false };
  }
  return { refunded: true, reference: await wf.step("pay", () => pay(order)) };
});

export async function onNote(req) {
  const note = req.json(); // the event's value; req.event has its topic, offset, key and headers
  await app.events.publish("audit", { seen: note.id });
}
```

## Guardrails written in JavaScript

```yaml
guardrails:
  - no-competitors: { handler: "guards:competitors", stage: both, message: "I can only talk about Contoso." }
```

```js
import { guardrails } from "@aiapp-server/server";

export async function competitors(req) {
  const check = guardrails.check(req);   // .stage, .route, .texts
  if (check.texts.some((t) => t.toLowerCase().includes("fabrikam"))) return guardrails.block("mentions a competitor");
  return guardrails.allow();             // or guardrails.redact(newTexts)
}
```

## Traces

```js
const ranked = await app.span("rerank", { candidates: hits.length }, async (span) => {
  span.set("kept", 4);
  return rerank(hits);
});
await fetch(url, { headers: app.traceHeaders() }); // the called service joins the trace
```

## npm packages

Add packages to `package.json`, then run `npm install`. It writes `package-lock.json`, which must be deployed with the app.

```bash
npm install zod
aiapp deploy
```

When you deploy, the server installs the packages with `npm ci --omit=dev --ignore-scripts`:

- **Install once:** packages are installed once per lockfile. Redeploys, and other apps with the same lockfile, reuse the install.
- **No install scripts:** packages that need a post-install build step won't work.
- **Behind a proxy:** set `npm_config_registry` for the server to use your registry mirror.

You don't need to install `@aiapp-server/server`; the server provides it.

## TypeScript

You can write handlers in TypeScript in two ways:

- **Compile them:** compile with `tsc` and deploy the `.js` files.
- **Run them directly:** `.ts` handlers run as they are where Node can strip types: Node 22.18 or later, or 23.6 or later.

For editor types, add `@aiapp-server/server` as a dev dependency when it is published on npm. Until then, copy the type definitions (`sdk/js/server/dist/*.d.ts`) from the [public repository](https://github.com/Sandaal/ai-app-server).

## Testing

Tests are Python for every app, whatever language its handlers are in. `aiapp test` drives the app over HTTP with scripted models; see [Test and evaluate](testing.md).

```python
from aiapp.testing import AppTest

class Routes(AppTest):
    def test_hello(self):
        self.assertEqual(self.client.post("/hello", {"name": "Ada"}).json(), {"greeting": "Hello, Ada!"})
```

The server's own conformance suite runs the same tests against an app written in both Python and JavaScript. So the two languages behave the same, feature by feature.
