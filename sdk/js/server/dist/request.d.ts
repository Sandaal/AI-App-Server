/** The authenticated caller, as established by the core. */
export declare class Principal {
    readonly subject: string;
    readonly roles: string[];
    readonly claims: Record<string, string>;
    constructor(subject?: string, roles?: string[], claims?: Record<string, string>);
    get authenticated(): boolean;
    /** The caller's tenant when the app keeps tenants apart (auth.oidc.tenant_isolation), else "". */
    get tenant(): string;
    /** True if the caller has one of roles; admin has them all. */
    hasRole(...roles: string[]): boolean;
}
/** One topic record (for subscription handlers: `req.event`). */
export declare class Event {
    readonly topic: string;
    readonly offset: number;
    readonly key: string;
    readonly time: string;
    readonly headers: Record<string, string>;
    readonly value: Buffer;
    readonly delivery: number;
    readonly partition: number;
    constructor(topic: string, offset: number, key: string, time: string, headers: Record<string, string>, value: Buffer, delivery?: number, partition?: number);
    get text(): string;
    json<T = any>(): T | null;
}
/** One HTTP request routed to a handler. Header names are lower-case. */
export declare class Request {
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
    constructor(msg: any);
    /** The body decoded as UTF-8. */
    get text(): string;
    /** The body parsed as JSON (null for an empty body). */
    json<T = any>(): T | null;
    /** For a subscription handler: the delivered record (the value is the body). */
    get event(): Event | null;
}
export interface ResponseInit {
    status?: number;
    headers?: Record<string, string>;
    contentType?: string;
}
/** Return this from a handler to control the status code and headers. */
export declare class Response {
    readonly body: unknown;
    readonly status: number;
    readonly headers: Record<string, string>;
    readonly contentType?: string;
    constructor(body?: unknown, init?: ResponseInit);
}
