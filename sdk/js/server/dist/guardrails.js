// Write guardrails in JavaScript. A guardrail is a handler named in ai-app.yaml:
//
//   guardrails:
//     - no-competitors: { handler: "guards:competitors", stage: both }
//
//   import { guardrails } from "@aiapp-server/server";
//   export async function competitors(req) {
//     const check = guardrails.check(req);
//     if (check.texts.some((t) => t.toLowerCase().includes("fabrikam")))
//       return guardrails.block("mentions a competitor", "I can only talk about Contoso.");
//     return guardrails.allow();
//   }
/** The texts to check (input: the request's text fields; output: the answer) and the end metadata. */
export function check(req) {
    const d = req.json() ?? {};
    return { stage: d.stage ?? "", route: d.route ?? "", texts: [...(d.texts ?? [])], metadata: { ...(d.metadata ?? {}) } };
}
export function allow() { return { action: "allow" }; }
/** Continue with these texts instead (as many as check.texts). */
export function redact(texts, reason = "") { return { action: "redact", texts, reason }; }
/** Stop. reason goes to the audit log; message, if given, is what the caller sees. */
export function block(reason = "", message) {
    return message ? { action: "block", reason, message } : { action: "block", reason };
}
