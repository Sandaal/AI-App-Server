// ConsoleClient talks to the server's web console API: the local console
// (`aiapp console`) or the hosted one at /_console/ with sign-in. The
// console page itself is built on it. Reads go to /api/admin/...; actions are
// POSTs with the console's CSRF header; nothing else of the admin API is
// reachable (keys, secrets, deploys and backups stay on the CLI).

import { AIAppError } from "./client.js";

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
  can: { audit: boolean; act: boolean };
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
export const CONSOLE_ACTION_HEADER = "X-Aiapp-Console";

type Query = Record<string, string | number | undefined>;

export class ConsoleClient {
  readonly baseUrl: string;
  private readonly fetchImpl: typeof fetch;

  constructor(opts: ConsoleOptions = {}) {
    this.baseUrl = opts.baseUrl ?? "";
    const f = opts.fetch || (globalThis.fetch as typeof fetch | undefined);
    if (!f) throw new Error("no fetch available; pass one in ConsoleOptions.fetch");
    this.fetchImpl = (input, init) => f(input, init);
  }

  private url(path: string, query?: Query): string {
    let u = this.baseUrl + path;
    if (query) {
      const q = new URLSearchParams();
      for (const [k, v] of Object.entries(query)) if (v !== undefined && v !== "") q.set(k, String(v));
      const s = q.toString();
      if (s) u += "?" + s;
    }
    return u;
  }

  private async send<T>(method: string, path: string, query?: Query): Promise<T> {
    const init: RequestInit = { method, cache: "no-store" };
    if (method !== "GET") {
      init.headers = { [CONSOLE_ACTION_HEADER]: "1", "Content-Type": "application/json" };
      init.body = "{}";
    }
    const resp = await this.fetchImpl(this.url(path, query), init);
    const text = await resp.text();
    let body: unknown = undefined;
    try { body = text ? JSON.parse(text) : undefined; } catch { body = text; }
    if (!resp.ok) {
      const b = (body && typeof body === "object" ? body : {}) as { error?: string; message?: string };
      throw new AIAppError(resp.status, b.error || "http_" + resp.status, b.message || b.error || resp.statusText, "");
    }
    return body as T;
  }

  /** GETs an admin API path the console allows, e.g. "apps" or "apps/hr/jobs". */
  get<T = unknown>(path: string, query?: Query): Promise<T> {
    return this.send<T>("GET", "api/admin/" + path, query);
  }

  /** POSTs a console action, e.g. "apps/hr/cron/nightly/run". */
  act<T = unknown>(path: string): Promise<T> {
    return this.send<T>("POST", "api/admin/" + path);
  }

  /** Who is signed in, and what they may do (401 when the session has ended). */
  me(): Promise<ConsoleMe> {
    return this.send<ConsoleMe>("GET", "me");
  }

  /** Signs out of the hosted console; returns the provider's sign-out URL, if any. */
  async signOut(): Promise<string> {
    const r = await this.send<{ end_session?: string }>("POST", "logout");
    return r.end_session || "";
  }

  // Reads.
  apps() { return this.get<{ apps: Array<Record<string, any>> }>("apps"); }
  traces(app = "", limit = 100) { return this.get<{ traces: Array<Record<string, any>> }>("traces", { limit, app }); }
  trace(id: string) { return this.get<Record<string, any>>("traces/" + encodeURIComponent(id)); }
  gateway() { return this.get<Record<string, any>>("gateway"); }
  quota(app: string) { return this.get<Record<string, any>>("quotas/" + encodeURIComponent(app)); }
  versions(app: string) { return this.get<Record<string, any>>(appPath(app, "versions")); }
  logs(app: string, limit = 500) { return this.get<{ records: Array<Record<string, any>> }>(appPath(app, "logs"), { limit }); }
  evals(app: string, limit = 30) { return this.get<{ runs: Array<Record<string, any>> }>(appPath(app, "evals"), { limit }); }
  evalRun(app: string, id = "latest") { return this.get<Record<string, any>>(appPath(app, "evals/" + encodeURIComponent(id))); }
  dead(app: string) { return this.get<{ dead: Array<Record<string, any>> }>(appPath(app, "dead")); }
  jobs(app: string) { return this.get<Record<string, any>>(appPath(app, "jobs")); }
  cron(app: string) { return this.get<Record<string, any>>(appPath(app, "cron")); }
  sources(app: string) { return this.get<Record<string, any>>(appPath(app, "connectors")); }
  topics(app: string) { return this.get<Record<string, any>>(appPath(app, "topics")); }
  approvals(app: string) { return this.get<Record<string, any>>(appPath(app, "approvals")); }
  /** The server-wide audit log (auditor and admin roles). */
  audit(q: AuditQuery = {}) { return this.get<{ records: Array<Record<string, any>> }>("audit", q as Query); }
  auditExport() { return this.get<{ sinks: Array<Record<string, any>> }>("audit/export"); }

  // Actions (operator and admin roles).
  replayDead(app: string, topic: string) { return this.act(appPath(app, "dead/" + encodeURIComponent(topic) + "/replay")); }
  purgeDead(app: string, topic: string) { return this.act(appPath(app, "dead/" + encodeURIComponent(topic) + "/purge")); }
  retryJob(app: string, id: string) { return this.act(appPath(app, "jobs/" + encodeURIComponent(id) + "/retry")); }
  cancelJob(app: string, id: string) { return this.act(appPath(app, "jobs/" + encodeURIComponent(id) + "/cancel")); }
  runCron(app: string, name: string) { return this.act(appPath(app, "cron/" + encodeURIComponent(name) + "/run")); }
  syncSources(app: string) { return this.act(appPath(app, "connectors/sync")); }
}

function appPath(app: string, rest: string): string {
  return "apps/" + encodeURIComponent(app) + "/" + rest;
}
