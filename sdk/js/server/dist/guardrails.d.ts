import type { Request } from "./request.js";
export interface Check {
    stage: string;
    route: string;
    texts: string[];
    metadata: Record<string, unknown>;
}
/** The texts to check (input: the request's text fields; output: the answer) and the end metadata. */
export declare function check(req: Request): Check;
export declare function allow(): {
    action: string;
};
/** Continue with these texts instead (as many as check.texts). */
export declare function redact(texts: string[], reason?: string): {
    action: string;
    texts: string[];
    reason: string;
};
/** Stop. reason goes to the audit log; message, if given, is what the caller sees. */
export declare function block(reason?: string, message?: string): {
    action: string;
    reason: string;
    message: string;
} | {
    action: string;
    reason: string;
    message?: undefined;
};
