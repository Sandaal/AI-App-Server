// AIAppClient calls one AI App Server app from a browser or Node 18+.
/** An error answer from the server, with its code (invalid_api_key, rate_limited, blocked_by_guardrail...). */
export class AIAppError extends Error {
    constructor(status, code, message, invocationId = "", guardrail, retryAfter) {
        super(message || code || `HTTP ${status}`);
        this.name = "AIAppError";
        this.status = status;
        this.code = code;
        this.invocationId = invocationId;
        this.guardrail = guardrail;
        this.retryAfter = retryAfter;
    }
}
function defaultBase() {
    const loc = globalThis.location;
    return loc && loc.origin && loc.origin !== "null" ? loc.origin : "http://127.0.0.1:8080";
}
export class AIAppClient {
    constructor(opts) {
        /** Workflow approvals for people with the approver role. */
        this.approvals = {
            pending: async () => (await readBody(await this.request("GET", "/_approvals/pending"))),
            decide: async (id, approve, comment = "") => (await readBody(await this.request("POST", "/_approvals/decide", JSON.stringify({ id, approve, comment }), { headers: { "Content-Type": "application/json" } }))),
        };
        if (!opts || !opts.app)
            throw new Error("AIAppClient needs an app name");
        this.app = opts.app;
        this.baseUrl = (opts.baseUrl || defaultBase()).replace(/\/+$/, "");
        this.apiKey = opts.apiKey;
        this.token = opts.token;
        this.sessionId = opts.sessionId;
        const f = opts.fetch || globalThis.fetch;
        if (!f)
            throw new Error("no fetch available; pass one in ClientOptions.fetch");
        this.fetchImpl = (input, init) => f(input, init); // keep `this` unbound for window.fetch
    }
    /** The app's URL for route (e.g. "/chat"). */
    url(route, query) {
        const path = route.startsWith("/") ? route : "/" + route;
        let u = `${this.baseUrl}/apps/${encodeURIComponent(this.app)}${path}`;
        if (query) {
            const q = new URLSearchParams();
            for (const [k, v] of Object.entries(query))
                q.set(k, String(v));
            const s = q.toString();
            if (s)
                u += (u.includes("?") ? "&" : "?") + s;
        }
        return u;
    }
    /** Base URL for OpenAI SDKs: new OpenAI({baseURL: client.openAIBaseURL(), apiKey}). */
    openAIBaseURL() {
        return `${this.baseUrl}/apps/${encodeURIComponent(this.app)}/v1`;
    }
    async authHeader() {
        const t = typeof this.token === "function" ? await this.token() : this.token;
        if (t)
            return "Bearer " + t;
        if (this.apiKey)
            return "Bearer " + this.apiKey;
        return undefined;
    }
    /** Sends a request and returns the response, throwing AIAppError for 4xx/5xx. */
    async request(method, route, body, opts = {}) {
        const headers = { ...(opts.headers || {}) };
        const auth = await this.authHeader();
        if (auth)
            headers["Authorization"] = auth;
        const session = opts.sessionId ?? this.sessionId;
        if (session)
            headers["X-Session-Id"] = session;
        const resp = await this.fetchImpl(this.url(route, opts.query), { method, headers, body: body ?? undefined, signal: opts.signal });
        if (!resp.ok)
            throw await errorFrom(resp);
        return resp;
    }
    /** POSTs JSON (or nothing) to a route and returns the parsed reply (text if it isn't JSON). */
    async call(route, body, opts = {}) {
        const init = body === undefined ? null : JSON.stringify(body);
        const headers = { ...(opts.headers || {}) };
        if (init !== null)
            headers["Content-Type"] = "application/json";
        const resp = await this.request("POST", route, init, { ...opts, headers });
        return (await readBody(resp));
    }
    /** GETs a route and returns the parsed reply. */
    async get(route, opts = {}) {
        return (await readBody(await this.request("GET", route, null, opts)));
    }
    /** POSTs JSON to a streaming route and yields its events. */
    async *stream(route, body, opts = {}) {
        const resp = await this.request("POST", route, JSON.stringify(body), {
            ...opts, headers: { "Content-Type": "application/json", Accept: "text/event-stream", ...(opts.headers || {}) },
        });
        const id = resp.headers.get("X-Invocation-Id") || "";
        if (!resp.body)
            throw new AIAppError(502, "no_body", "the response has no body", id);
        for await (const ev of sseEvents(resp.body)) {
            switch (ev.event) {
                case "message":
                    yield { type: "text", text: ev.data };
                    break;
                case "replace":
                    yield { type: "replace", text: ev.data };
                    break;
                case "end": {
                    let metadata = {};
                    try {
                        metadata = JSON.parse(ev.data || "{}");
                    }
                    catch { /* keep empty */ }
                    yield { type: "end", metadata };
                    return;
                }
                case "error": {
                    let code = "stream_error";
                    try {
                        code = JSON.parse(ev.data).error || code;
                    }
                    catch { /* keep default */ }
                    throw new AIAppError(502, code, "the answer was cut off (" + code + ")", id);
                }
            }
        }
    }
    /**
     * Asks a chat route (knowledge-chat, customer-support, code-assistant...)
     * and resolves with the whole answer; onText sees the text as it grows.
     */
    async chat(message, opts = {}) {
        const route = opts.route || "/chat";
        const resp = await this.request("POST", route, JSON.stringify({ message }), {
            ...opts, headers: { "Content-Type": "application/json", Accept: "text/event-stream", ...(opts.headers || {}) },
        });
        const result = { text: "", citations: [], metadata: {}, invocationId: resp.headers.get("X-Invocation-Id") || "",
            traceId: resp.headers.get("X-Trace-Id") || "" };
        const ctype = resp.headers.get("Content-Type") || "";
        if (!ctype.includes("text/event-stream") || !resp.body) { // a non-streaming route
            const b = await readBody(resp);
            result.text = typeof b === "string" ? b : String(b?.answer ?? JSON.stringify(b));
            opts.onText?.(result.text);
            return result;
        }
        for await (const ev of sseEvents(resp.body)) {
            if (ev.event === "message")
                result.text += ev.data;
            else if (ev.event === "replace")
                result.text = ev.data;
            else if (ev.event === "end") {
                try {
                    result.metadata = JSON.parse(ev.data || "{}");
                }
                catch { /* keep empty */ }
                result.citations = Array.isArray(result.metadata.citations) ? result.metadata.citations : [];
                break;
            }
            else if (ev.event === "error") {
                let code = "stream_error";
                try {
                    code = JSON.parse(ev.data).error || code;
                }
                catch { /* keep default */ }
                throw new AIAppError(502, code, "the answer was cut off (" + code + ")", result.invocationId);
            }
            opts.onText?.(result.text);
        }
        opts.onText?.(result.text);
        return result;
    }
    /** Uploads a file's bytes to a route (document-extraction, summarization, meeting-notes...). */
    async upload(route, file, opts = {}) {
        const name = opts.filename || (typeof File !== "undefined" && file instanceof File ? file.name : "upload.bin");
        const type = opts.contentType || (typeof Blob !== "undefined" && file instanceof Blob && file.type) || "application/octet-stream";
        const body = file instanceof Uint8Array ? new Blob([file]) : file;
        const resp = await this.request("POST", route, body, {
            ...opts, headers: { "Content-Type": type, "X-Filename": name, ...(opts.headers || {}) },
        });
        return (await readBody(resp));
    }
}
async function readBody(resp) {
    const text = await resp.text();
    if ((resp.headers.get("Content-Type") || "").includes("json") || /^[[{]/.test(text.trim())) {
        try {
            return JSON.parse(text);
        }
        catch { /* not JSON after all */ }
    }
    return text;
}
async function errorFrom(resp) {
    let code = "http_" + resp.status, message = "", guardrail;
    try {
        const b = await resp.json();
        const e = b.error;
        if (e && typeof e === "object") {
            code = e.type || code;
            message = e.message || "";
        } // OpenAI shape
        else {
            code = e || code;
            message = b.message || "";
            guardrail = b.guardrail;
        }
    }
    catch { /* not JSON */ }
    const ra = Number(resp.headers.get("Retry-After"));
    return new AIAppError(resp.status, code, message || defaultMessage(resp.status, code), resp.headers.get("X-Invocation-Id") || "", guardrail, Number.isFinite(ra) && ra > 0 ? ra : undefined);
}
function defaultMessage(status, code) {
    if (status === 401)
        return "This app needs an API key or sign-in.";
    if (status === 403)
        return "You don't have access to this.";
    if (status === 429)
        return "Too many requests. Wait a moment and try again.";
    return code;
}
/** Parses a Server-Sent Events body into {event, data} pairs. */
export async function* sseEvents(body) {
    const reader = body.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    try {
        for (;;) {
            const { value, done } = await reader.read();
            if (value)
                buf += decoder.decode(value, { stream: true });
            let m;
            while ((m = /\r?\n\r?\n/.exec(buf))) {
                const block = buf.slice(0, m.index);
                buf = buf.slice(m.index + m[0].length);
                let event = "message";
                const data = [];
                for (const line of block.split(/\r?\n/)) {
                    if (line.startsWith("event:"))
                        event = line.slice(6).trim();
                    else if (line.startsWith("data:"))
                        data.push(line.slice(line.startsWith("data: ") ? 6 : 5));
                }
                if (data.length || event !== "message")
                    yield { event, data: data.join("\n") };
            }
            if (done)
                return;
        }
    }
    finally {
        reader.releaseLock();
    }
}
