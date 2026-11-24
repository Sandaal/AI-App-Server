// Web components for AI App Server apps:
//   <aiapp-chat app="hr-bot"></aiapp-chat>
//   <aiapp-upload app="invoices" route="/extract"></aiapp-upload>
//   <aiapp-approvals app="support"></aiapp-approvals>
// Load with <script type="module" src="https://YOUR-SERVER/_sdk/aiapp.js"></script>.
// Theme with CSS variables (--aiapp-accent, --aiapp-bg, --aiapp-fg, --aiapp-muted,
// --aiapp-border, --aiapp-radius, --aiapp-font) and ::part(...).
import { AIAppClient, AIAppError } from "./client.js";
const BASE_STYLE = `
:host { --a: var(--aiapp-accent, #2f6feb); --bg: var(--aiapp-bg, #fff); --fg: var(--aiapp-fg, #1d1d1f);
  --mut: var(--aiapp-muted, #6b6b73); --bd: var(--aiapp-border, #e3e3e8); --r: var(--aiapp-radius, 10px);
  display: block; font: 14px/1.5 var(--aiapp-font, system-ui, -apple-system, "Segoe UI", sans-serif); color: var(--fg); }
@media (prefers-color-scheme: dark) { :host(:not([theme="light"])) { --bg: var(--aiapp-bg, #1d1d20); --fg: var(--aiapp-fg, #ececf1);
  --mut: var(--aiapp-muted, #9a9aa3); --bd: var(--aiapp-border, #2e2e33); --a: var(--aiapp-accent, #6ea0ff); } }
* { box-sizing: border-box; }
.box { background: var(--bg); border: 1px solid var(--bd); border-radius: var(--r); }
button { font: inherit; border: 0; border-radius: calc(var(--r) - 4px); padding: 8px 14px; background: var(--a); color: #fff; cursor: pointer; }
button[disabled] { opacity: .5; cursor: default; }
button.ghost { background: transparent; color: var(--fg); border: 1px solid var(--bd); }
.err { color: #c62828; } .muted { color: var(--mut); }
textarea, input[type=text] { font: inherit; color: var(--fg); background: transparent; border: 1px solid var(--bd); border-radius: calc(var(--r) - 4px); padding: 8px 10px; }
`;
/** Shared attributes: app, base-url, api-key; property tokenProvider for sign-in tokens. */
class AIAppElement extends HTMLElement {
    static get observedAttributes() { return ["app", "base-url", "api-key"]; }
    constructor() {
        super();
        this.root = this.attachShadow({ mode: "open" });
    }
    attributeChangedCallback() { this._client = undefined; }
    get client() {
        if (!this._client) {
            const app = this.getAttribute("app");
            if (!app)
                throw new Error(`<${this.localName}> needs an app attribute`);
            this._client = new AIAppClient({
                app,
                baseUrl: this.getAttribute("base-url") || scriptOrigin(),
                apiKey: this.getAttribute("api-key") || undefined,
                token: this.tokenProvider,
                fetch: this.fetchImpl,
            });
        }
        return this._client;
    }
    emit(name, detail) {
        this.dispatchEvent(new CustomEvent(name, { detail, bubbles: true, composed: true }));
    }
    errorText(e) {
        if (e instanceof AIAppError) {
            if (e.status === 401)
                this.emit("aiapp-auth-required", { error: e });
            return e.message;
        }
        return "Something went wrong. Please try again.";
    }
}
// The origin the bundle was loaded from, so <script src="https://server/_sdk/aiapp.js">
// talks to that server without a base-url attribute.
const SCRIPT_ORIGIN = (() => {
    try {
        return new URL(import.meta.url).origin;
    }
    catch {
        return "";
    }
})();
function scriptOrigin() {
    return SCRIPT_ORIGIN && SCRIPT_ORIGIN !== "null" && SCRIPT_ORIGIN.startsWith("http") ? SCRIPT_ORIGIN : undefined;
}
export function escapeHTML(s) {
    return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
/** Escapes text, keeps line breaks, bold and inline code, and links [n] to citations. */
export function renderAnswer(text, citations = []) {
    const known = new Set(citations.map((c) => c.n));
    return escapeHTML(text)
        .replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>")
        .replace(/`([^`\n]+)`/g, "<code>$1</code>")
        .replace(/\[(\d{1,3})\]/g, (m, n) => (known.has(+n) ? `<sup class="cite" data-n="${n}">[${n}]</sup>` : m))
        .replace(/\n/g, "<br>");
}
function sessionKey(app) { return "aiapp-session:" + app; }
function newSession() {
    const c = globalThis.crypto;
    return c?.randomUUID ? c.randomUUID() : Math.random().toString(36).slice(2) + Date.now().toString(36);
}
/**
 * <aiapp-chat app="hr-bot" heading="HR assistant" placeholder="Ask about leave..." route="/chat">
 * Streams answers with citations. Attribute memory="none" sends no session id;
 * the default keeps one conversation per app in sessionStorage.
 * Events: aiapp-answer (ChatResult), aiapp-error ({error}), aiapp-auth-required.
 */
export class AIAppChat extends AIAppElement {
    constructor() {
        super(...arguments);
        this.busy = false;
    }
    connectedCallback() {
        if (this.log)
            return;
        this.root.innerHTML = `<style>${BASE_STYLE}
      .box { display: flex; flex-direction: column; height: var(--aiapp-height, 480px); }
      header { padding: 10px 14px; border-bottom: 1px solid var(--bd); font-weight: 600; }
      .log { flex: 1; overflow: auto; padding: 12px 14px; display: flex; flex-direction: column; gap: 10px; }
      .msg { max-width: 85%; padding: 8px 12px; border-radius: var(--r); white-space: normal; word-wrap: break-word; }
      .user { align-self: flex-end; background: var(--a); color: #fff; }
      .bot { align-self: flex-start; background: color-mix(in srgb, var(--fg) 6%, transparent); }
      .cite { color: var(--a); cursor: default; }
      .sources { margin-top: 6px; font-size: 12px; color: var(--mut); }
      .sources li { margin: 0; }
      form { display: flex; gap: 8px; padding: 10px; border-top: 1px solid var(--bd); }
      textarea { flex: 1; resize: none; min-height: 40px; max-height: 140px; }
      .empty { color: var(--mut); margin: auto; text-align: center; }
      code { font-size: 12px; }
    </style>
    <div class="box" part="container">
      ${this.getAttribute("heading") ? `<header part="header">${escapeHTML(this.getAttribute("heading"))}</header>` : ""}
      <div class="log" part="log" role="log" aria-live="polite"><div class="empty">${escapeHTML(this.getAttribute("intro") || "Ask a question.")}</div></div>
      <form part="form"><textarea rows="1" part="input" aria-label="Message"></textarea><button part="send">Send</button></form>
    </div>`;
        this.log = this.root.querySelector(".log");
        this.input = this.root.querySelector("textarea");
        this.send = this.root.querySelector("button");
        this.input.placeholder = this.getAttribute("placeholder") || "Type a message";
        this.root.querySelector("form").addEventListener("submit", (e) => { e.preventDefault(); this.submit(); });
        this.input.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                this.submit();
            }
        });
    }
    session() {
        var _a;
        if (this.getAttribute("memory") === "none")
            return undefined;
        const key = sessionKey(this.getAttribute("app") || "");
        try {
            let s = sessionStorage.getItem(key);
            if (!s) {
                s = newSession();
                sessionStorage.setItem(key, s);
            }
            return s;
        }
        catch {
            return (_a = this)._s || (_a._s = newSession());
        }
    }
    /** Starts a new conversation. */
    reset() {
        try {
            sessionStorage.removeItem(sessionKey(this.getAttribute("app") || ""));
        }
        catch { /* none */ }
        this._s = undefined;
        this.log.innerHTML = "";
    }
    bubble(cls, html) {
        this.log.querySelector(".empty")?.remove();
        const el = document.createElement("div");
        el.className = "msg " + cls;
        el.setAttribute("part", "message " + cls);
        el.innerHTML = html;
        this.log.appendChild(el);
        this.log.scrollTop = this.log.scrollHeight;
        return el;
    }
    /** Sends a message as if typed (also usable from page code). */
    async ask(message) {
        const q = message.trim();
        if (!q || this.busy)
            return undefined;
        this.busy = true;
        this.send.disabled = true;
        this.bubble("user", escapeHTML(q).replace(/\n/g, "<br>"));
        const el = this.bubble("bot", '<span class="muted">…</span>');
        try {
            const res = await this.client.chat(q, {
                route: this.getAttribute("route") || "/chat",
                sessionId: this.session(),
                onText: (t) => { el.innerHTML = renderAnswer(t); this.log.scrollTop = this.log.scrollHeight; },
            });
            el.innerHTML = renderAnswer(res.text, res.citations);
            if (res.citations.length) {
                const used = res.citations.filter((c) => res.text.includes(`[${c.n}]`));
                const list = (used.length ? used : res.citations).map((c) => `<li>[${c.n}] ${escapeHTML(String(c.source))}${c.page ? `, page ${escapeHTML(String(c.page))}` : ""}</li>`).join("");
                el.insertAdjacentHTML("beforeend", `<ul class="sources" part="sources">${list}</ul>`);
            }
            this.emit("aiapp-answer", res);
            return res;
        }
        catch (e) {
            el.innerHTML = `<span class="err">${escapeHTML(this.errorText(e))}</span>`;
            this.emit("aiapp-error", { error: e });
            return undefined;
        }
        finally {
            this.busy = false;
            this.send.disabled = false;
        }
    }
    submit() {
        const v = this.input.value;
        this.input.value = "";
        void this.ask(v);
    }
}
/**
 * <aiapp-upload app="invoices" route="/extract" accept=".pdf,.png" wait="60" label="Drop an invoice">
 * Sends a file and shows the result. Events: aiapp-result ({result, file}), aiapp-error.
 */
export class AIAppUpload extends AIAppElement {
    connectedCallback() {
        if (this.out)
            return;
        this.root.innerHTML = `<style>${BASE_STYLE}
      .drop { padding: 22px; text-align: center; border-style: dashed; cursor: pointer; }
      .drop.over { border-color: var(--a); }
      .out { margin-top: 10px; }
      pre { margin: 0; padding: 10px; overflow: auto; font: 12px ui-monospace, Menlo, Consolas, monospace; }
      input[type=file] { display: none; }
    </style>
    <div class="box drop" part="dropzone" tabindex="0" role="button">
      <div>${escapeHTML(this.getAttribute("label") || "Drop a file here, or click to choose one")}</div>
      <div class="muted" part="hint"></div>
      <input type="file">
    </div>
    <div class="out" part="result" aria-live="polite"></div>`;
        this.out = this.root.querySelector(".out");
        this.fileInput = this.root.querySelector("input");
        const drop = this.root.querySelector(".drop");
        if (this.getAttribute("accept")) {
            this.fileInput.accept = this.getAttribute("accept");
            this.root.querySelector(".muted").textContent = this.getAttribute("accept");
        }
        drop.addEventListener("click", () => this.fileInput.click());
        drop.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ")
            this.fileInput.click(); });
        drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("over"); });
        drop.addEventListener("dragleave", () => drop.classList.remove("over"));
        drop.addEventListener("drop", (e) => {
            e.preventDefault();
            drop.classList.remove("over");
            const f = e.dataTransfer?.files?.[0];
            if (f)
                void this.send(f);
        });
        this.fileInput.addEventListener("change", () => { const f = this.fileInput.files?.[0]; if (f)
            void this.send(f); });
    }
    /** Uploads a file (also usable from page code). */
    async send(file, filename) {
        const name = filename || file.name || "upload.bin";
        this.out.innerHTML = `<span class="muted">Sending ${escapeHTML(name)}…</span>`;
        try {
            const wait = this.getAttribute("wait");
            const result = await this.client.upload(this.getAttribute("route") || "/", file, {
                filename: name, query: wait ? { wait } : undefined,
            });
            this.out.innerHTML = `<div class="box"><pre part="output">${escapeHTML(typeof result === "string" ? result : JSON.stringify(result, null, 2))}</pre></div>`;
            this.emit("aiapp-result", { result, file: name });
            return result;
        }
        catch (e) {
            this.out.innerHTML = `<span class="err">${escapeHTML(this.errorText(e))}</span>`;
            this.emit("aiapp-error", { error: e });
            return undefined;
        }
    }
}
/**
 * <aiapp-approvals app="support" refresh="15">
 * Lists workflow steps waiting for a person, with approve and reject. The
 * caller needs the approver role (an API key with --role approver, or a
 * sign-in token whose roles map to approver). Events: aiapp-decided ({approval}).
 */
export class AIAppApprovals extends AIAppElement {
    connectedCallback() {
        if (!this.list) {
            this.root.innerHTML = `<style>${BASE_STYLE}
        .item { padding: 12px 14px; margin-bottom: 10px; }
        .title { font-weight: 600; }
        pre { margin: 8px 0; padding: 8px; overflow: auto; font: 12px ui-monospace, Menlo, Consolas, monospace;
          background: color-mix(in srgb, var(--fg) 5%, transparent); border-radius: 6px; }
        .row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
        .row input { flex: 1; min-width: 140px; }
      </style><div part="list" aria-live="polite"><span class="muted">Loading…</span></div>`;
            this.list = this.root.querySelector("[part=list]");
        }
        void this.refresh();
        const every = Number(this.getAttribute("refresh") || 0);
        if (every > 0 && !this.timer)
            this.timer = setInterval(() => void this.refresh(), every * 1000);
    }
    disconnectedCallback() {
        if (this.timer)
            clearInterval(this.timer);
        this.timer = undefined;
    }
    /** Reloads the pending list. */
    async refresh() {
        try {
            const { approvals } = await this.client.approvals.pending();
            this.render(approvals || []);
            return approvals || [];
        }
        catch (e) {
            this.list.innerHTML = `<span class="err">${escapeHTML(this.errorText(e))}</span>`;
            return [];
        }
    }
    render(items) {
        if (!items.length) {
            this.list.innerHTML = `<div class="box item muted">Nothing is waiting for a decision.</div>`;
            return;
        }
        this.list.innerHTML = items.map((a) => `<div class="box item" part="approval" data-id="${escapeHTML(a.id)}">
      <div class="title">${escapeHTML(a.title)}</div>
      <div class="muted">${escapeHTML(a.key)} · expires ${escapeHTML(new Date(a.expires_at).toLocaleString())}</div>
      ${a.details ? `<pre>${escapeHTML(JSON.stringify(a.details, null, 2))}</pre>` : ""}
      <div class="row"><input type="text" placeholder="Comment (optional)" aria-label="Comment">
        <button data-approve="true" part="approve">Approve</button><button class="ghost" data-approve="false" part="reject">Reject</button></div>
    </div>`).join("");
        this.list.querySelectorAll("button").forEach((b) => b.addEventListener("click", async () => {
            const item = b.closest(".item");
            const comment = item.querySelector("input").value;
            item.querySelectorAll("button").forEach((x) => (x.disabled = true));
            try {
                const decided = await this.client.approvals.decide(item.dataset.id, b.dataset.approve === "true", comment);
                this.emit("aiapp-decided", { approval: decided });
                await this.refresh();
            }
            catch (e) {
                item.insertAdjacentHTML("beforeend", `<div class="err">${escapeHTML(this.errorText(e))}</div>`);
                item.querySelectorAll("button").forEach((x) => (x.disabled = false));
            }
        }));
    }
}
/** Registers the elements (done automatically when this module loads). */
export function defineElements(registry = customElements) {
    if (!registry.get("aiapp-chat"))
        registry.define("aiapp-chat", AIAppChat);
    if (!registry.get("aiapp-upload"))
        registry.define("aiapp-upload", AIAppUpload);
    if (!registry.get("aiapp-approvals"))
        registry.define("aiapp-approvals", AIAppApprovals);
}
if (typeof customElements !== "undefined")
    defineElements();
