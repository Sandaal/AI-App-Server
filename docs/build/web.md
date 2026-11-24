# Pages and web components

## Built-in pages

Set `ui:` and the app gets a page at `http://SERVER:8080/apps/APP/`:

| `ui:` | Page |
|---|---|
| `chat-widget` | streaming chat with citations and conversation memory |
| `extract-widget` | upload documents, see extracted fields with evidence |
| `summary-widget` | upload, get a summary |
| `classify-widget` | try classification |
| `notes-widget` | upload a recording or transcript, get meeting notes |
| `content-widget` | briefs, drafts and reviews |
| `insights-widget` | ask questions about data, see the SQL |
| `agent-widget` | give an agent a task, follow its runs |

Every app also has an approvals page at `/apps/APP/_approvals/` (needs the `approver` role).

**Sign-in on these pages:** see [Sign-in](../operate/sign-in.md#2-sign-in-on-the-apps-pages).

## Your own page in the app

```yaml
ui: ./ui           # files in ./ui are served at /apps/APP/
```

`ui/index.html`:

```html
<!doctype html>
<meta charset="utf-8">
<title>HR help</title>
<script type="module" src="/_sdk/aiapp.js"></script>
<h1>Ask HR</h1>
<aiapp-chat app="hr-bot" heading="HR assistant" placeholder="Ask about leave, benefits…"></aiapp-chat>
```

## Web components on any page

Every server serves the component bundle at `/_sdk/aiapp.js`:

```html
<script type="module" src="https://ai.contoso.com/_sdk/aiapp.js"></script>

<aiapp-chat app="hr-bot" heading="HR assistant"></aiapp-chat>
<aiapp-upload app="invoices" route="/extract" accept=".pdf,.png,.jpg" wait="60"></aiapp-upload>
<aiapp-approvals app="support" refresh="15"></aiapp-approvals>
```

| Element | What it does | Events |
|---|---|---|
| `<aiapp-chat>` | streams answers, links `[n]` citations, keeps a conversation per tab (`memory="none"` turns that off). Attributes: `route`, `intro`, `heading`, `placeholder` | `aiapp-answer`, `aiapp-error`, `aiapp-auth-required` |
| `<aiapp-upload>` | uploads a file by drag and drop or picker, shows the result | `aiapp-result`, `aiapp-error` |
| `<aiapp-approvals>` | lists steps waiting for a person, with approve and reject | `aiapp-decided` |

**Pages on another website** need that origin allowed in the app:

```yaml
cors:
  origins: ["https://intranet.contoso.com"]
```

**Theming:** CSS variables `--aiapp-accent`, `--aiapp-bg`, `--aiapp-fg`, `--aiapp-muted`, `--aiapp-border`, `--aiapp-radius`, `--aiapp-font`, `--aiapp-height`, and `::part(...)`. Dark mode follows the system unless `theme="light"`.

**Signing in from your page:** give the element a token provider, for example with MSAL for Entra ID:

```js
document.querySelector("aiapp-chat").tokenProvider = async () =>
  (await msal.acquireTokenSilent({ scopes: ["api://hr-bot/.default"] })).accessToken;
```

`api-key="…"` works too, but anyone can read a key in a web page: keep that for internal tools.
