// What handlers receive (Request) and may return (Response).

/** The authenticated caller, as established by the core. */
export class Principal {
  readonly subject: string;
  readonly roles: string[];
  readonly claims: Record<string, string>;
  constructor(subject = "", roles: string[] = [], claims: Record<string, string> = {}) {
    this.subject = subject; this.roles = roles; this.claims = claims;
  }
  get authenticated(): boolean { return this.subject !== ""; }
  /** The caller's tenant when the app keeps tenants apart (auth.oidc.tenant_isolation), else "". */
  get tenant(): string { return this.claims["aiapp_tenant"] ?? ""; }
  /** True if the caller has one of roles; admin has them all. */
  hasRole(...roles: string[]): boolean {
    return this.roles.includes("admin") || roles.some((r) => this.roles.includes(r));
  }
}

/** One topic record (for subscription handlers: `req.event`). */
export class Event {
  constructor(
    readonly topic: string, readonly offset: number, readonly key: string, readonly time: string,
    readonly headers: Record<string, string>, readonly value: Buffer, readonly delivery = 1, readonly partition = 0,
  ) {}
  get text(): string { return this.value.toString("utf8"); }
  json<T = any>(): T | null { return this.value.length ? JSON.parse(this.text) : null; }
}

/** One HTTP request routed to a handler. Header names are lower-case. */
export class Request {
  readonly method: string;
  readonly route: string;
  readonly headers: Record<string, string>;
  readonly body: Buffer;
  readonly sessionId: string;
  readonly invocationId: string;
  readonly principal: Principal;
  readonly query: Record<string, string>;
  /** W3C trace context of the core's span for this call. */
  readonly traceparent: string;

  constructor(msg: any) {
    this.method = msg.method ?? "";
    this.route = msg.route ?? "";
    this.headers = Object.fromEntries(Object.entries(msg.headers ?? {}).map(([k, v]) => [k.toLowerCase(), String(v)]));
    this.body = Buffer.from(msg.body ?? []);
    this.sessionId = msg.session_id ?? "";
    this.invocationId = msg.invocation_id ?? "";
    const p = msg.principal ?? {};
    this.principal = new Principal(p.subject ?? "", p.roles ?? [], p.claims ?? {});
    this.query = Object.fromEntries(new URLSearchParams(msg.query ?? "").entries());
    this.traceparent = msg.traceparent ?? "";
  }

  /** The body decoded as UTF-8. */
  get text(): string { return this.body.toString("utf8"); }

  /** The body parsed as JSON (null for an empty body). */
  json<T = any>(): T | null { return this.body.length ? JSON.parse(this.text) : null; }

  /** For a subscription handler: the delivered record (the value is the body). */
  get event(): Event | null {
    const h = this.headers;
    if (!("x-aiapp-topic" in h)) return null;
    const own: Record<string, string> = {};
    for (const [k, v] of Object.entries(h)) if (k.startsWith("x-aiapp-header-")) own[k.slice("x-aiapp-header-".length)] = v;
    return new Event(h["x-aiapp-topic"], Number(h["x-aiapp-offset"] ?? 0), h["x-aiapp-key"] ?? "", h["x-aiapp-time"] ?? "",
      own, this.body, Number(h["x-aiapp-delivery"] || 1), Number(h["x-aiapp-partition"] || 0));
  }
}

export interface ResponseInit {
  status?: number;
  headers?: Record<string, string>;
  contentType?: string;
}

/** Return this from a handler to control the status code and headers. */
export class Response {
  readonly body: unknown;
  readonly status: number;
  readonly headers: Record<string, string>;
  readonly contentType?: string;
  constructor(body: unknown = "", init: ResponseInit = {}) {
    this.body = body;
    this.status = init.status ?? 200;
    this.headers = init.headers ?? {};
    this.contentType = init.contentType;
  }
}
