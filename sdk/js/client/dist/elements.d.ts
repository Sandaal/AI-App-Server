import { AIAppClient, type Approval, type ChatResult, type Citation } from "./client.js";
/** Shared attributes: app, base-url, api-key; property tokenProvider for sign-in tokens. */
declare abstract class AIAppElement extends HTMLElement {
    static get observedAttributes(): string[];
    protected root: ShadowRoot;
    private _client?;
    /** Returns a sign-in access token (e.g. from MSAL); used instead of api-key. */
    tokenProvider?: () => string | undefined | Promise<string | undefined>;
    /** fetch to use (tests, proxies). */
    fetchImpl?: typeof fetch;
    constructor();
    attributeChangedCallback(): void;
    get client(): AIAppClient;
    protected emit(name: string, detail: unknown): void;
    protected errorText(e: unknown): string;
}
export declare function escapeHTML(s: string): string;
/** Escapes text, keeps line breaks, bold and inline code, and links [n] to citations. */
export declare function renderAnswer(text: string, citations?: Citation[]): string;
/**
 * <aiapp-chat app="hr-bot" heading="HR assistant" placeholder="Ask about leave..." route="/chat">
 * Streams answers with citations. Attribute memory="none" sends no session id;
 * the default keeps one conversation per app in sessionStorage.
 * Events: aiapp-answer (ChatResult), aiapp-error ({error}), aiapp-auth-required.
 */
export declare class AIAppChat extends AIAppElement {
    private log;
    private input;
    private send;
    private busy;
    connectedCallback(): void;
    private session;
    /** Starts a new conversation. */
    reset(): void;
    private bubble;
    /** Sends a message as if typed (also usable from page code). */
    ask(message: string): Promise<ChatResult | undefined>;
    private submit;
}
/**
 * <aiapp-upload app="invoices" route="/extract" accept=".pdf,.png" wait="60" label="Drop an invoice">
 * Sends a file and shows the result. Events: aiapp-result ({result, file}), aiapp-error.
 */
export declare class AIAppUpload extends AIAppElement {
    private out;
    private fileInput;
    connectedCallback(): void;
    /** Uploads a file (also usable from page code). */
    send(file: Blob, filename?: string): Promise<unknown>;
}
/**
 * <aiapp-approvals app="support" refresh="15">
 * Lists workflow steps waiting for a person, with approve and reject. The
 * caller needs the approver role (an API key with --role approver, or a
 * sign-in token whose roles map to approver). Events: aiapp-decided ({approval}).
 */
export declare class AIAppApprovals extends AIAppElement {
    private list;
    private timer?;
    connectedCallback(): void;
    disconnectedCallback(): void;
    /** Reloads the pending list. */
    refresh(): Promise<Approval[]>;
    private render;
}
/** Registers the elements (done automatically when this module loads). */
export declare function defineElements(registry?: CustomElementRegistry): void;
export {};
