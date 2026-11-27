# @sandaal/client

The JS/TS client and web components for apps served by AI App Server.

- Works in browsers and in Node 18 or later.
- Has no runtime dependencies.
- The browser bundle is 16 KB minified.

## Web components (no build step)
Every server serves the bundle, so a page can load it from the server directly:

```html
<script type="module" src="https://ai.contoso.com/_sdk/aiapp.js"></script>

<aiapp-chat app="hr-bot" heading="HR assistant" placeholder="Ask about leave, benefits…"></aiapp-chat>
<aiapp-upload app="invoices" route="/extract" accept=".pdf,.png,.jpg" wait="60"></aiapp-upload>
<aiapp-approvals app="support" refresh="15"></aiapp-approvals>
```

| Element | What it does | Events |
|---|---|---|
| `<aiapp-chat>` | Streams answers, links `[n]` citations, lists sources, and keeps a conversation per tab (`memory="none"` turns that off). Attributes: `route`, `intro`, `heading`, `placeholder` | `aiapp-answer`, `aiapp-error`, `aiapp-auth-required` |
| `<aiapp-upload>` | Uploads a file by drag and drop or file picker, and shows the result | `aiapp-result`, `aiapp-error` |
| `<aiapp-approvals>` | Lists workflow steps waiting for a person, with approve and reject. Needs the `approver` role | `aiapp-decided` |

- **Server URL:** the elements call the server they were loaded from. Set `base-url` to point them elsewhere.
- **Theming:** CSS variables (`--aiapp-accent`, `--aiapp-bg`, `--aiapp-fg`, `--aiapp-muted`, `--aiapp-border`, `--aiapp-radius`, `--aiapp-font`, `--aiapp-height`) and `::part(...)`. The elements follow the system dark mode unless `theme="light"` is set.

### Pages on another origin
If the page isn't served by the server itself, allow the page's origin in `ai-app.yaml`:

```yaml
cors:
  origins: ["https://intranet.contoso.com"]
```

### Signing in
For sign-in, hand the element a token provider, such as MSAL for Entra ID:

```js
document.querySelector("aiapp-chat").tokenProvider = async () =>
  (await msal.acquireTokenSilent({ scopes: ["api://hr-bot/.default"] })).accessToken;
```

`api-key="…"` works too, but anyone can read a key in a page, so keep keys to internal tools.

## Client

```ts
import { AIAppClient, AIAppError } from "@sandaal/client";

const client = new AIAppClient({ baseUrl: "https://ai.contoso.com", app: "hr-bot", token: getToken });

const answer = await client.chat("How many days of leave do I get?", {
  sessionId: "conv-42",
  onText: (text) => render(text),        // grows as the answer streams
});
answer.citations;                          // [{n: 1, source: "leave-policy.pdf", page: "2"}]

for await (const ev of client.stream("/chat", { message: "Hi" })) { /* text | replace | end */ }

await client.call("/classify", { text: "I was charged twice" });   // {label: "billing", ...}
await client.upload("/extract", file, { query: { wait: 60 } });
await client.approvals.pending();
await client.approvals.decide(id, true, "fine");

try { await client.chat(q); } catch (e) {
  if (e instanceof AIAppError) e.status, e.code, e.guardrail, e.retryAfter, e.invocationId;
}
```

**Guardrail changes:** when a guardrail changes or withholds a streamed answer, the stream sends a `replace` event. `chat()` applies it for you.

**OpenAI SDKs:** `client.openAIBaseURL()` gives the base URL to use with an OpenAI SDK.

## Development

```
npm install
npm run build    # dist/ (ESM + .d.ts) and dist/aiapp.js (the bundle the server embeds)
npm test         # node:test; web components run in jsdom
```

Commit `dist/` after building: the server embeds `dist/aiapp.js`, and CI fails if the committed build doesn't match the source.
