export interface ConsoleOptions {
    /** The console's base URL, ending in "/" (default: relative to the page). */
    baseUrl?: string;
    fetch?: typeof fetch;
}
/** The signed-in person and what their console role allows. */
export interface ConsoleMe {
    subject: string;
    name?: string;
    roles: string[];
    local: boolean;
    can: {
        audit: boolean;
        act: boolean;
    };
    sign_out: boolean;
}
export interface AuditQuery {
    app?: string;
    /** Type prefix, e.g. "model_" or "console_". */
    type?: string;
    subject?: string;
    /** A duration ("24h") or an RFC 3339 time. */
    since?: string;
    limit?: number;
}
/** The header every console action must carry (CSRF). */
export declare const CONSOLE_ACTION_HEADER = "X-Aiapp-Console";
type Query = Record<string, string | number | undefined>;
export declare class ConsoleClient {
    readonly baseUrl: string;
    private readonly fetchImpl;
    constructor(opts?: ConsoleOptions);
    private url;
    private send;
    /** GETs an admin API path the console allows, e.g. "apps" or "apps/hr/jobs". */
    get<T = unknown>(path: string, query?: Query): Promise<T>;
    /** POSTs a console action, e.g. "apps/hr/cron/nightly/run". */
    act<T = unknown>(path: string): Promise<T>;
    /** Who is signed in, and what they may do (401 when the session has ended). */
    me(): Promise<ConsoleMe>;
    /** Signs out of the hosted console; returns the provider's sign-out URL, if any. */
    signOut(): Promise<string>;
    apps(): Promise<{
        apps: Array<Record<string, any>>;
    }>;
    traces(app?: string, limit?: number): Promise<{
        traces: Array<Record<string, any>>;
    }>;
    trace(id: string): Promise<Record<string, any>>;
    gateway(): Promise<Record<string, any>>;
    quota(app: string): Promise<Record<string, any>>;
    versions(app: string): Promise<Record<string, any>>;
    logs(app: string, limit?: number): Promise<{
        records: Array<Record<string, any>>;
    }>;
    evals(app: string, limit?: number): Promise<{
        runs: Array<Record<string, any>>;
    }>;
    evalRun(app: string, id?: string): Promise<Record<string, any>>;
    dead(app: string): Promise<{
        dead: Array<Record<string, any>>;
    }>;
    jobs(app: string): Promise<Record<string, any>>;
    cron(app: string): Promise<Record<string, any>>;
    sources(app: string): Promise<Record<string, any>>;
    topics(app: string): Promise<Record<string, any>>;
    approvals(app: string): Promise<Record<string, any>>;
    /** The server-wide audit log (auditor and admin roles). */
    audit(q?: AuditQuery): Promise<{
        records: Array<Record<string, any>>;
    }>;
    auditExport(): Promise<{
        sinks: Array<Record<string, any>>;
    }>;
    replayDead(app: string, topic: string): Promise<unknown>;
    purgeDead(app: string, topic: string): Promise<unknown>;
    retryJob(app: string, id: string): Promise<unknown>;
    cancelJob(app: string, id: string): Promise<unknown>;
    runCron(app: string, name: string): Promise<unknown>;
    syncSources(app: string): Promise<unknown>;
}
export {};
