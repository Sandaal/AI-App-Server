// AIAppClient calls one AI App Server app from a browser or Node 18+.

export interface ClientOptions {
  /** App name, as in ai-app.yaml. */
  app: string;
  /** Server URL, e.g. https://ai.contoso.com. Default: the page's origin. */
  baseUrl?: string;
  /** An API key (aiapp key create). Avoid on public pages: anyone can read it. */
  apiKey?: string;
  /** A sign-in (OIDC) access token, or a function that returns a fresh one. */
  token?: string | (() => string | undefined | Promise<string | undefined>);
  /** Conversation id sent as X-Session-Id (chat memory). */
  sessionId?: string;
  /** fetch to use (default: globalThis.fetch). */
  fetch?: typeof fetch;
}

export interface Citation {
  n: number;
  source: string;
  page?: string | number | null;
  score?: number;
  [key: string]: unknown;
}

/** One event of a streamed answer. */
export type StreamEvent =
  | { type: "text"; text: string }
  /** A guardrail changed or withheld the answer: show this text instead. */
  | { type: "replace"; text: string }
  | { type: "end"; metadata: Record<string, unknown> };

export interface ChatResult {
  text: string;
  citations: Citation[];
  metadata: Record<string, unknown>;
  invocationId: string;
  traceId: string;
}

export interface RequestOptions {
  sessionId?: string;
  signal?: AbortSignal;
  headers?: Record<string, string>;
  /** Query string parameters, e.g. {wait: 60}. */
  query?: Record<string, string | number | boolean>;
}

export interface Approval {
  id: string;
  app: string;
  job: string;
  key: string;
  title: string;
  details?: unknown;
  state: string;
  by?: string;
  comment?: string;
  created_at: string;
  expires_at: string;
}

/** An error answer from the server, with its code (invalid_api_key, rate_limited, blocked_by_guardrail...). */
export class AIAppError extends Error {
  readonly status: number;
  readonly code: string;
  readonly invocationId: string;
  readonly guardrail?: string;
  readonly retryAfter?: number;
  constructor(status: number, code: string, message: string, invocationId = "", guardrail?: string, retryAfter?: number) {
    super(message || code || `HTTP ${status}`);
    this.name = "AIAppError";
    this.status = status;
    this.code = code;
    this.invocationId = invocationId;
    this.guardrail = guardrail;
    this.retryAfter = retryAfter;
  }
}

function defaultBase(): string {
  const loc = (globalThis as { location?: Location }).location;
  return loc && loc.origin && loc.origin !== "null" ? loc.origin : "http://127.0.0.1:8080";
}

export class AIAppClient {
  readonly app: string;
  readonly baseUrl: string;
  sessionId?: string;
  private apiKey?: string;
  private token?: ClientOptions["token"];
  private fetchImpl: typeof fetch;

  constructor(opts: ClientOptions) {
    if (!opts || !opts.app) throw new Error("AIAppClient needs an app name");
    this.app = opts.app;
    this.baseUrl = (opts.baseUrl || defaultBase()).replace(/\/+$/, "");
    this.apiKey = opts.apiKey;
    this.token = opts.token;
    this.sessionId = opts.sessionId;
    const f = opts.fetch || (globalThis.fetch as typeof fetch | undefined);
    if (!f) throw new Error("no fetch available; pass one in ClientOptions.fetch");
    this.fetchImpl = (input, init) => f(input, init); // keep `this` unbound for window.fetch
  }

  /** The app's URL for route (e.g. "/chat"). */
  url(route: string, query?: RequestOptions["query"]): string {
    const path = route.startsWith("/") ? route : "/" + route;
    let u = `${this.baseUrl}/apps/${encodeURIComponent(this.app)}${path}`;
    if (query) {
      const q = new URLSearchParams();
      for (const [k, v] of Object.entries(query)) q.set(k, String(v));
      const s = q.toString();
      if (s) u += (u.includes("?") ? "&" : "?") + s;
    }
    return u;
  }

  /** Base URL for OpenAI SDKs: new OpenAI({baseURL: client.openAIBaseURL(), apiKey}). */
  openAIBaseURL(): string {
    return `${this.baseUrl}/apps/${encodeURIComponent(this.app)}/v1`;
  }

  private async authHeader(): Promise<string | undefined> {
    const t = typeof this.token === "function" ? await this.token() : this.token;
    if (t) return "Bearer " + t;
    if (this.apiKey) return "Bearer " + this.apiKey;
    return undefined;
  }

  /** Sends a request and returns the response, throwing AIAppError for 4xx/5xx. */
  async request(method: string, route: string, body?: BodyInit | null, opts: RequestOptions = {}): Promise<Response> {
    const headers: Record<string, string> = { ...(opts.headers || {}) };
    const auth = await this.authHeader();
    if (auth) headers["Authorization"] = auth;
    const session = opts.sessionId ?? this.sessionId;
    if (session) headers["X-Session-Id"] = session;
    const resp = await this.fetchImpl(this.url(route, opts.query), { method, headers, body: body ?? undefined, signal: opts.signal });
    if (!resp.ok) throw await errorFrom(resp);
    return resp;
  }

  /** POSTs JSON (or nothing) to a route and returns the parsed reply (text if it isn't JSON). */
  async call<T = unknown>(route: string, body?: unknown, opts: RequestOptions = {}): Promise<T> {
    const init = body === undefined ? null : JSON.stringify(body);
    const headers = { ...(opts.headers || {}) };
    if (init !== null) headers["Content-Type"] = "application/json";
    const resp = await this.request("POST", route, init, { ...opts, headers });
    return (await readBody(resp)) as T;
  }

  /** GETs a route and returns the parsed reply. */
  async get<T = unknown>(route: string, opts: RequestOptions = {}): Promise<T> {
    return (await readBody(await this.request("GET", route, null, opts))) as T;
  }

  /** POSTs JSON to a streaming route and yields its events. */
  async *stream(route: string, body: unknown, opts: RequestOptions = {}): AsyncGenerator<StreamEvent, void, undefined> {
    const resp = await this.request("POST", route, JSON.stringify(body), {
      ...opts, headers: { "Content-Type": "application/json", Accept: "text/event-stream", ...(opts.headers || {}) },
    });
    const id = resp.headers.get("X-Invocation-Id") || "";
    if (!resp.body) throw new AIAppError(502, "no_body", "the response has no body", id);
    for await (const ev of sseEvents(resp.body)) {
      switch (ev.event) {
        case "message":
          yield { type: "text", text: ev.data };
          break;
        case "replace":
          yield { type: "replace", text: ev.data };
          break;
        case "end": {
          let metadata: Record<string, unknown> = {};
          try { metadata = JSON.parse(ev.data || "{}"); } catch { /* keep empty */ }
          yield { type: "end", metadata };
          return;
        }
        case "error": {
          let code = "stream_error";
          try { code = JSON.parse(ev.data).error || code; } catch { /* keep default */ }
          throw new AIAppError(502, code, "the answer was cut off (" + code + ")", id);
        }
      }
    }
  }

  /**
   * Asks a chat route (knowledge-chat, customer-support, code-assistant...)
   * and resolves with the whole answer; onText sees the text as it grows.
   */
  async chat(message: string, opts: RequestOptions & { route?: string; onText?: (text: string) => void } = {}): Promise<ChatResult> {
    const route = opts.route || "/chat";
    const resp = await this.request("POST", route, JSON.stringify({ message }), {
      ...opts, headers: { "Content-Type": "application/json", Accept: "text/event-stream", ...(opts.headers || {}) },
    });
    const result: ChatResult = { text: "", citations: [], metadata: {}, invocationId: resp.headers.get("X-Invocation-Id") || "",
      traceId: resp.headers.get("X-Trace-Id") || "" };
    const ctype = resp.headers.get("Content-Type") || "";
    if (!ctype.includes("text/event-stream") || !resp.body) { // a non-streaming route
      const b = await readBody(resp);
      result.text = typeof b === "string" ? b : String((b as { answer?: unknown })?.answer ?? JSON.stringify(b));
      opts.onText?.(result.text);
      return result;
    }
    for await (const ev of sseEvents(resp.body)) {
      if (ev.event === "message") result.text += ev.data;
      else if (ev.event === "replace") result.text = ev.data;
      else if (ev.event === "end") {
        try { result.metadata = JSON.parse(ev.data || "{}"); } catch { /* keep empty */ }
        result.citations = Array.isArray(result.metadata.citations) ? (result.metadata.citations as Citation[]) : [];
        break;
      } else if (ev.event === "error") {
        let code = "stream_error";
        try { code = JSON.parse(ev.data).error || code; } catch { /* keep default */ }
        throw new AIAppError(502, code, "the answer was cut off (" + code + ")", result.invocationId);
      }
      opts.onText?.(result.text);
    }
    opts.onText?.(result.text);
    return result;
  }

  /** Uploads a file's bytes to a route (document-extraction, summarization, meeting-notes...). */
  async upload<T = unknown>(route: string, file: Blob | ArrayBuffer | Uint8Array,
    opts: RequestOptions & { filename?: string; contentType?: string } = {}): Promise<T> {
    const name = opts.filename || (typeof File !== "undefined" && file instanceof File ? file.name : "upload.bin");
    const type = opts.contentType || (typeof Blob !== "undefined" && file instanceof Blob && file.type) || "application/octet-stream";
    const body = file instanceof Uint8Array ? new Blob([file as BlobPart]) : (file as BodyInit);
    const resp = await this.request("POST", route, body, {
      ...opts, headers: { "Content-Type": type, "X-Filename": name, ...(opts.headers || {}) },
    });
    return (await readBody(resp)) as T;
  }

  /** Workflow approvals for people with the approver role. */
  readonly approvals = {
    pending: async (): Promise<{ approvals: Approval[]; you: string }> =>
      (await readBody(await this.request("GET", "/_approvals/pending"))) as { approvals: Approval[]; you: string },
    decide: async (id: string, approve: boolean, comment = ""): Promise<Approval> =>
      (await readBody(await this.request("POST", "/_approvals/decide", JSON.stringify({ id, approve, comment }),
        { headers: { "Content-Type": "application/json" } }))) as Approval,
  };
}

async function readBody(resp: Response): Promise<unknown> {
  const text = await resp.text();
  if ((resp.headers.get("Content-Type") || "").includes("json") || /^[[{]/.test(text.trim())) {
    try { return JSON.parse(text); } catch { /* not JSON after all */ }
  }
  return text;
}

async function errorFrom(resp: Response): Promise<AIAppError> {
  let code = "http_" + resp.status, message = "", guardrail: string | undefined;
  try {
    const b = await resp.json();
    const e = b.error;
    if (e && typeof e === "object") { code = e.type || code; message = e.message || ""; } // OpenAI shape
    else { code = e || code; message = b.message || ""; guardrail = b.guardrail; }
  } catch { /* not JSON */ }
  const ra = Number(resp.headers.get("Retry-After"));
  return new AIAppError(resp.status, code, message || defaultMessage(resp.status, code), resp.headers.get("X-Invocation-Id") || "",
    guardrail, Number.isFinite(ra) && ra > 0 ? ra : undefined);
}

function defaultMessage(status: number, code: string): string {
  if (status === 401) return "This app needs an API key or sign-in.";
  if (status === 403) return "You don't have access to this.";
  if (status === 429) return "Too many requests. Wait a moment and try again.";
  return code;
}

/** Parses a Server-Sent Events body into {event, data} pairs. */
export async function* sseEvents(body: ReadableStream<Uint8Array>): AsyncGenerator<{ event: string; data: string }> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (value) buf += decoder.decode(value, { stream: true });
      let m: RegExpExecArray | null;
      while ((m = /\r?\n\r?\n/.exec(buf))) {
        const block = buf.slice(0, m.index);
        buf = buf.slice(m.index + m[0].length);
        let event = "message";
        const data: string[] = [];
        for (const line of block.split(/\r?\n/)) {
          if (line.startsWith("event:")) event = line.slice(6).trim();
          else if (line.startsWith("data:")) data.push(line.slice(line.startsWith("data: ") ? 6 : 5));
        }
        if (data.length || event !== "message") yield { event, data: data.join("\n") };
      }
      if (done) return;
    }
  } finally {
    reader.releaseLock();
  }
}
