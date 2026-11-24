// The browser bundle the server serves at /_sdk/aiapp.js: the client plus
// the web components, registered on load.
export * from "./index.js";
export { AIAppApprovals, AIAppChat, AIAppUpload, defineElements } from "./elements.js";
import { AIAppClient, AIAppError } from "./client.js";
import { ConsoleClient } from "./console.js";

(globalThis as unknown as { AIApp?: unknown }).AIApp = { AIAppClient, AIAppError, ConsoleClient };
