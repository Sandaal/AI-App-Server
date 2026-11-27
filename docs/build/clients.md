# Call apps from your code

Every route is `POST http://SERVER:8080/apps/APP/ROUTE`. Send a key or token as `Authorization: Bearer …` when the app requires one.

## curl

```bash
curl -X POST -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"message":"How many days of leave do I get?"}' \
  https://ai.contoso.com/apps/hr-bot/chat
```

Streaming routes answer with **Server-Sent Events**: `data:` lines with text, possibly a `replace` event (a guardrail changed the answer), then an `end` event with JSON metadata such as `citations`. Other routes return JSON. Add `-H "X-Session-Id: conv-42"` to keep a conversation.

## JavaScript / TypeScript

```bash
npm install @sandaal/ai-app-server-client
```

```ts
import { AIAppClient, AIAppError } from "@sandaal/ai-app-server-client";

const client = new AIAppClient({ baseUrl: "https://ai.contoso.com", app: "hr-bot", token: getToken });

const answer = await client.chat("How many days of leave do I get?", {
  sessionId: "conv-42",
  onText: (text) => render(text),       // grows as the answer streams
});
answer.citations;                        // [{ n: 1, source: "leave-policy.pdf", page: "2" }]

await client.call("/classify", { text: "I was charged twice" });   // JSON routes
await client.upload("/extract", file, { query: { wait: 60 } });   // files
await client.approvals.pending();
await client.approvals.decide(id, true, "fine");

try { await client.chat(q); } catch (e) {
  if (e instanceof AIAppError) console.log(e.status, e.code, e.guardrail, e.retryAfter, e.invocationId);
}
```

Works in browsers and Node 18+, with no dependencies. `token` can be a string or an async function (MSAL, etc.); `apiKey` also works.

!!! note
    Until the npm package is published, load the same client in a page from your server: `import { AIAppClient } from "https://YOUR-SERVER/_sdk/aiapp.js"`.

## Python

Any HTTP library works:

```python
import httpx

r = httpx.post("https://ai.contoso.com/apps/hr-bot/classify",
               headers={"Authorization": f"Bearer {key}"}, json={"text": "I was charged twice"})
print(r.json())

with httpx.stream("POST", "https://ai.contoso.com/apps/hr-bot/chat",
                  headers={"Authorization": f"Bearer {key}"}, json={"message": "Hi"}) as s:
    for line in s.iter_lines():
        if line.startswith("data: "):
            print(line[6:], end="", flush=True)
```

## OpenAI SDKs and tools

Chat apps also answer as an OpenAI-compatible chat model at `/apps/APP/v1`:

```python
from openai import OpenAI
client = OpenAI(base_url="https://ai.contoso.com/apps/hr-bot/v1", api_key=key)
r = client.chat.completions.create(model="hr-bot", messages=[{"role": "user", "content": "How many days of leave?"}])
print(r.choices[0].message.content)
```

So tools that speak the OpenAI API (LangChain, chat UIs, spreadsheets add-ins) can use your app, with its documents, guardrails and quotas.

## Ids for support

Every response has an `X-Invocation-Id` header. `aiapp trace ID` shows that request step by step.
