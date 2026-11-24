export interface ClientOptions {
    /** App name, as in ai-app.yaml. */
    app: string;
    /** Server URL, e.g. https://ai.contoso.com. Default: the page's origin. */
    baseUrl?: string;
    /** An API key (aiapp key create). Avoid on public pages: anyone can read it. */
    apiKey?: string;
    /** A sign-in (OIDC) access token, or a function that returns a fresh one. */
    token?: string | (() => string | undefined | Promise<string | undefined>);
    /** Conversation id sent as X-Session-Id (chat memory). */
    sessionId?: string;
    /** fetch to use (default: globalThis.fetch). */
    fetch?: typeof fetch;
}
export interface Citation {
    n: number;
    source: string;
    page?: string | number | null;
    score?: number;
    [key: string]: unknown;
}
/** One event of a streamed answer. */
export type StreamEvent = {
    type: "text";
    text: string;
}
/** A guardrail changed or withheld the answer: show this text instead. */
 | {
    type: "replace";
    text: string;
} | {
    type: "end";
    metadata: Record<string, unknown>;
};
export interface ChatResult {
    text: string;
    citations: Citation[];
    metadata: Record<string, unknown>;
    invocationId: string;
    traceId: string;
}
export interface RequestOptions {
    sessionId?: string;
    signal?: AbortSignal;
    headers?: Record<string, string>;
    /** Query string parameters, e.g. {wait: 60}. */
    query?: Record<string, string | number | boolean>;
}
export interface Approval {
    id: string;
    app: string;
    job: string;
    key: string;
    title: string;
    details?: unknown;
    state: string;
    by?: string;
    comment?: string;
    created_at: string;
    expires_at: string;
}
/** An error answer from the server, with its code (invalid_api_key, rate_limited, blocked_by_guardrail...). */
export declare class AIAppError extends Error {
    readonly status: number;
    readonly code: string;
    readonly invocationId: string;
    readonly guardrail?: string;
    readonly retryAfter?: number;
    constructor(status: number, code: string, message: string, invocationId?: string, guardrail?: string, retryAfter?: number);
}
export declare class AIAppClient {
    readonly app: string;
    readonly baseUrl: string;
    sessionId?: string;
    private apiKey?;
    private token?;
    private fetchImpl;
    constructor(opts: ClientOptions);
    /** The app's URL for route (e.g. "/chat"). */
    url(route: string, query?: RequestOptions["query"]): string;
    /** Base URL for OpenAI SDKs: new OpenAI({baseURL: client.openAIBaseURL(), apiKey}). */
    openAIBaseURL(): string;
    private authHeader;
    /** Sends a request and returns the response, throwing AIAppError for 4xx/5xx. */
    request(method: string, route: string, body?: BodyInit | null, opts?: RequestOptions): Promise<Response>;
    /** POSTs JSON (or nothing) to a route and returns the parsed reply (text if it isn't JSON). */
    call<T = unknown>(route: string, body?: unknown, opts?: RequestOptions): Promise<T>;
    /** GETs a route and returns the parsed reply. */
    get<T = unknown>(route: string, opts?: RequestOptions): Promise<T>;
    /** POSTs JSON to a streaming route and yields its events. */
    stream(route: string, body: unknown, opts?: RequestOptions): AsyncGenerator<StreamEvent, void, undefined>;
    /**
     * Asks a chat route (knowledge-chat, customer-support, code-assistant...)
     * and resolves with the whole answer; onText sees the text as it grows.
     */
    chat(message: string, opts?: RequestOptions & {
        route?: string;
        onText?: (text: string) => void;
    }): Promise<ChatResult>;
    /** Uploads a file's bytes to a route (document-extraction, summarization, meeting-notes...). */
    upload<T = unknown>(route: string, file: Blob | ArrayBuffer | Uint8Array, opts?: RequestOptions & {
        filename?: string;
        contentType?: string;
    }): Promise<T>;
    /** Workflow approvals for people with the approver role. */
    readonly approvals: {
        pending: () => Promise<{
            approvals: Approval[];
            you: string;
        }>;
        decide: (id: string, approve: boolean, comment?: string) => Promise<Approval>;
    };
}
/** Parses a Server-Sent Events body into {event, data} pairs. */
export declare function sseEvents(body: ReadableStream<Uint8Array>): AsyncGenerator<{
    event: string;
    data: string;
}>;
