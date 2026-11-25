// What handlers receive (Request) and may return (Response).
/** The authenticated caller, as established by the core. */
export class Principal {
    subject;
    roles;
    claims;
    constructor(subject = "", roles = [], claims = {}) {
        this.subject = subject;
        this.roles = roles;
        this.claims = claims;
    }
    get authenticated() { return this.subject !== ""; }
    /** The caller's tenant when the app keeps tenants apart (auth.oidc.tenant_isolation), else "". */
    get tenant() { return this.claims["aiapp_tenant"] ?? ""; }
    /** True if the caller has one of roles; admin has them all. */
    hasRole(...roles) {
        return this.roles.includes("admin") || roles.some((r) => this.roles.includes(r));
    }
}
/** One topic record (for subscription handlers: `req.event`). */
export class Event {
    topic;
    offset;
    key;
    time;
    headers;
    value;
    delivery;
    partition;
    constructor(topic, offset, key, time, headers, value, delivery = 1, partition = 0) {
        this.topic = topic;
        this.offset = offset;
        this.key = key;
        this.time = time;
        this.headers = headers;
        this.value = value;
        this.delivery = delivery;
        this.partition = partition;
    }
    get text() { return this.value.toString("utf8"); }
    json() { return this.value.length ? JSON.parse(this.text) : null; }
}
/** One HTTP request routed to a handler. Header names are lower-case. */
export class Request {
    method;
    route;
    headers;
    body;
    sessionId;
    invocationId;
    principal;
    query;
    /** W3C trace context of the core's span for this call. */
    traceparent;
    constructor(msg) {
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
    get text() { return this.body.toString("utf8"); }
    /** The body parsed as JSON (null for an empty body). */
    json() { return this.body.length ? JSON.parse(this.text) : null; }
    /** For a subscription handler: the delivered record (the value is the body). */
    get event() {
        const h = this.headers;
        if (!("x-aiapp-topic" in h))
            return null;
        const own = {};
        for (const [k, v] of Object.entries(h))
            if (k.startsWith("x-aiapp-header-"))
                own[k.slice("x-aiapp-header-".length)] = v;
        return new Event(h["x-aiapp-topic"], Number(h["x-aiapp-offset"] ?? 0), h["x-aiapp-key"] ?? "", h["x-aiapp-time"] ?? "", own, this.body, Number(h["x-aiapp-delivery"] || 1), Number(h["x-aiapp-partition"] || 0));
    }
}
/** Return this from a handler to control the status code and headers. */
export class Response {
    body;
    status;
    headers;
    contentType;
    constructor(body = "", init = {}) {
        this.body = body;
        this.status = init.status ?? 200;
        this.headers = init.headers ?? {};
        this.contentType = init.contentType;
    }
}
