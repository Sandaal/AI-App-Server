// ConsoleClient talks to the server's web console API: the local console
// (`aiapp console`) or the hosted one at /_console/ with sign-in. The
// console page itself is built on it. Reads go to /api/admin/...; actions are
// POSTs with the console's CSRF header; nothing else of the admin API is
// reachable (keys, secrets, deploys and backups stay on the CLI).
import { AIAppError } from "./client.js";
/** The header every console action must carry (CSRF). */
export const CONSOLE_ACTION_HEADER = "X-Aiapp-Console";
export class ConsoleClient {
    constructor(opts = {}) {
        this.baseUrl = opts.baseUrl ?? "";
        const f = opts.fetch || globalThis.fetch;
        if (!f)
            throw new Error("no fetch available; pass one in ConsoleOptions.fetch");
        this.fetchImpl = (input, init) => f(input, init);
    }
    url(path, query) {
        let u = this.baseUrl + path;
        if (query) {
            const q = new URLSearchParams();
            for (const [k, v] of Object.entries(query))
                if (v !== undefined && v !== "")
                    q.set(k, String(v));
            const s = q.toString();
            if (s)
                u += "?" + s;
        }
        return u;
    }
    async send(method, path, query) {
        const init = { method, cache: "no-store" };
        if (method !== "GET") {
            init.headers = { [CONSOLE_ACTION_HEADER]: "1", "Content-Type": "application/json" };
            init.body = "{}";
        }
        const resp = await this.fetchImpl(this.url(path, query), init);
        const text = await resp.text();
        let body = undefined;
        try {
            body = text ? JSON.parse(text) : undefined;
        }
        catch {
            body = text;
        }
        if (!resp.ok) {
            const b = (body && typeof body === "object" ? body : {});
            throw new AIAppError(resp.status, b.error || "http_" + resp.status, b.message || b.error || resp.statusText, "");
        }
        return body;
    }
    /** GETs an admin API path the console allows, e.g. "apps" or "apps/hr/jobs". */
    get(path, query) {
        return this.send("GET", "api/admin/" + path, query);
    }
    /** POSTs a console action, e.g. "apps/hr/cron/nightly/run". */
    act(path) {
        return this.send("POST", "api/admin/" + path);
    }
    /** Who is signed in, and what they may do (401 when the session has ended). */
    me() {
        return this.send("GET", "me");
    }
    /** Signs out of the hosted console; returns the provider's sign-out URL, if any. */
    async signOut() {
        const r = await this.send("POST", "logout");
        return r.end_session || "";
    }
    // Reads.
    apps() { return this.get("apps"); }
    traces(app = "", limit = 100) { return this.get("traces", { limit, app }); }
    trace(id) { return this.get("traces/" + encodeURIComponent(id)); }
    gateway() { return this.get("gateway"); }
    quota(app) { return this.get("quotas/" + encodeURIComponent(app)); }
    versions(app) { return this.get(appPath(app, "versions")); }
    logs(app, limit = 500) { return this.get(appPath(app, "logs"), { limit }); }
    evals(app, limit = 30) { return this.get(appPath(app, "evals"), { limit }); }
    evalRun(app, id = "latest") { return this.get(appPath(app, "evals/" + encodeURIComponent(id))); }
    dead(app) { return this.get(appPath(app, "dead")); }
    jobs(app) { return this.get(appPath(app, "jobs")); }
    cron(app) { return this.get(appPath(app, "cron")); }
    sources(app) { return this.get(appPath(app, "connectors")); }
    topics(app) { return this.get(appPath(app, "topics")); }
    approvals(app) { return this.get(appPath(app, "approvals")); }
    /** The server-wide audit log (auditor and admin roles). */
    audit(q = {}) { return this.get("audit", q); }
    auditExport() { return this.get("audit/export"); }
    // Actions (operator and admin roles).
    replayDead(app, topic) { return this.act(appPath(app, "dead/" + encodeURIComponent(topic) + "/replay")); }
    purgeDead(app, topic) { return this.act(appPath(app, "dead/" + encodeURIComponent(topic) + "/purge")); }
    retryJob(app, id) { return this.act(appPath(app, "jobs/" + encodeURIComponent(id) + "/retry")); }
    cancelJob(app, id) { return this.act(appPath(app, "jobs/" + encodeURIComponent(id) + "/cancel")); }
    runCron(app, name) { return this.act(appPath(app, "cron/" + encodeURIComponent(name) + "/run")); }
    syncSources(app) { return this.act(appPath(app, "connectors/sync")); }
}
function appPath(app, rest) {
    return "apps/" + encodeURIComponent(app) + "/" + rest;
}
