import type { Request } from "./request.js";
/** Thrown inside a workflow that must wait (for an approval); the core parks the job. */
export declare class Suspended extends Error {
    static readonly code = "workflow_suspended";
    constructor(message: string);
}
export interface Decision {
    approved: boolean;
    state: string;
    by: string;
    comment: string;
}
export declare class Workflow {
    readonly jobId: string;
    readonly input: any;
    readonly attempt: number;
    constructor(jobId: string, input: any, attempt?: number);
    /** Runs fn once for this workflow and saves its (JSON) result; later runs return the saved result. */
    step<T>(name: string, fn: () => T | Promise<T>): Promise<T>;
    /** Asks a person to approve; while pending, the workflow stops here and runs again once decided or expired. */
    approval(key: string, title: string, details?: unknown, o?: {
        timeout?: number;
    }): Promise<Decision>;
}
/** Turns `async (wf, input) => ...` into a job handler. */
export declare function workflow<T>(fn: (wf: Workflow, input: any) => Promise<T>): (req: Request) => Promise<T>;
