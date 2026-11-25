// Durable workflows with checkpointed steps and human approvals, like the
// Python SDK's @app.workflow:
//
//   export const refund = workflow(async (wf, input) => {
//     const order = await wf.step("lookup", () => lookupOrder(input.order_id));
//     const d = await wf.approval("refund", `Refund ${order.total}?`, order);
//     if (!d.approved) return { refunded: false };
//     await wf.step("pay", () => pay(order));
//     return { refunded: true };
//   });
//
// Declare it as a job (jobs: [{ name: refund, handler: "handlers:refund" }])
// and start it with app.jobs.enqueue("refund", {...}). Each step's result is
// saved, so after a restart, retry or approval completed steps return their
// saved result; code between steps must be deterministic.

import { app } from "./app.js";
import { call } from "./host.js";
import type { Request } from "./request.js";

const CHECKPOINTS = "_workflows";
const CHECKPOINT_TTL = 30 * 24 * 3600;

/** Thrown inside a workflow that must wait (for an approval); the core parks the job. */
export class Suspended extends Error {
  static readonly code = "workflow_suspended";
  constructor(message: string) { super(message); this.name = "Suspended"; }
}

export interface Decision { approved: boolean; state: string; by: string; comment: string }

export class Workflow {
  constructor(readonly jobId: string, readonly input: any, readonly attempt = 1) {}

  /** Runs fn once for this workflow and saves its (JSON) result; later runs return the saved result. */
  async step<T>(name: string, fn: () => T | Promise<T>): Promise<T> {
    const key = `${this.jobId}/${name}`;
    const saved = await app.kv.get(key, { namespace: CHECKPOINTS });
    if (saved) return JSON.parse(saved.toString("utf8")).value as T;
    const result = await fn();
    await app.kv.put(key, JSON.stringify({ value: result ?? null }), { namespace: CHECKPOINTS, ttl: CHECKPOINT_TTL });
    return result;
  }

  /** Asks a person to approve; while pending, the workflow stops here and runs again once decided or expired. */
  async approval(key: string, title: string, details?: unknown, o: { timeout?: number } = {}): Promise<Decision> {
    const info = await call("ApprovalRequest", {
      job_id: this.jobId, key, title, details_json: details === undefined ? "" : JSON.stringify(details),
      timeout_s: String(Math.round(o.timeout ?? 7 * 24 * 3600)),
    });
    if (info.state === "pending") throw new Suspended(`waiting for approval ${info.id}: ${title}`);
    return { approved: info.state === "approved", state: info.state, by: info.by, comment: info.comment };
  }
}

/** Turns `async (wf, input) => ...` into a job handler. */
export function workflow<T>(fn: (wf: Workflow, input: any) => Promise<T>): (req: Request) => Promise<T> {
  return async (req: Request) => {
    const jobId = req.headers["x-aiapp-job-id"];
    if (!jobId) throw new Error(`${fn.name || "this handler"} is a workflow: run it as a job (app.jobs.enqueue), not as a route`);
    const wf = new Workflow(jobId, req.json(), Number(req.headers["x-aiapp-job-attempt"] || 1));
    return fn(wf, wf.input);
  };
}
