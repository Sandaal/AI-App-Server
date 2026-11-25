import { Event } from "./request.js";
export type Message = {
    role: string;
    content?: string;
    tool_call_id?: string;
    tool_calls?: ToolCall[];
    images?: ImageInput[];
};
export type ToolCall = {
    id: string;
    name: string;
    arguments: Record<string, unknown>;
};
export type ImageInput = Buffer | Uint8Array | {
    data: Buffer | Uint8Array;
    mimeType?: string;
};
/** A provider call failed after the core's retries and fallback. */
export declare class ModelError extends Error {
    code: string;
    retryable: boolean;
    constructor(code: string, message: string, retryable?: boolean);
}
export interface ChatOptions {
    system?: string;
    history?: Message[];
    messages?: Message[];
    temperature?: number;
    maxTokens?: number;
    images?: ImageInput[];
}
/** A tool the model may call: a function plus its description and JSON Schema parameters. */
export interface Tool {
    name: string;
    description: string;
    parameters: Record<string, unknown>;
    fn: (args: any) => unknown;
}
/** Declares a tool: `app.tool({ name, description, parameters }, fn)`. */
export declare function tool(spec: {
    name: string;
    description: string;
    parameters?: Record<string, unknown>;
}, fn: (args: any) => unknown): Tool;
export interface AgentResult {
    text: string;
    steps: {
        tool: string;
        arguments: unknown;
        result: string | null;
        error: string | null;
    }[];
    messages: Message[];
}
/** A logical model from the manifest's `models:` section. */
export declare class Model {
    readonly name: string;
    constructor(name: string);
    /** Yields the answer as it streams. */
    stream(user?: string, o?: ChatOptions): AsyncGenerator<string>;
    /** Returns the whole answer as one string. */
    complete(user?: string, o?: ChatOptions): Promise<string>;
    /** Asks for JSON matching schema (a JSON Schema object) and returns it parsed. */
    json<T = any>(user: string | undefined, o: ChatOptions & {
        schema: Record<string, unknown>;
        name?: string;
    }): Promise<T>;
    /** One model turn with tools offered: { text, calls }. */
    turn(messages: Message[], o?: {
        tools?: {
            name: string;
            description?: string;
            parameters?: unknown;
        }[];
        system?: string;
        temperature?: number;
    }): Promise<{
        text: string;
        calls: ToolCall[];
    }>;
    /**
     * Lets the model use tools until it can answer. With mcp (default true),
     * the app's MCP servers' tools are offered too. A failing tool is reported
     * to the model as an error rather than thrown.
     */
    run(user: string | undefined, o?: {
        tools?: Tool[];
        mcp?: boolean;
        system?: string;
        history?: Message[];
        maxSteps?: number;
        temperature?: number;
    }): Promise<AgentResult>;
    /** Embeds texts with this (embedding) model. */
    embed(inputs: string[]): Promise<number[][]>;
    /** Turns a recording into text with this (speech-to-text) model. */
    transcribe(audio: Buffer, o?: {
        filename?: string;
        language?: string;
        prompt?: string;
    }): Promise<{
        text: string;
        language: string;
        durationSeconds: number;
    }>;
}
/** The app's private key-value store and data structures (values are Buffers; strings are UTF-8). */
export declare class KV {
    get(key: string, o?: {
        namespace?: string;
    }): Promise<Buffer | null>;
    /** Stores value; ttl (seconds) > 0 makes it expire. */
    put(key: string, value: Buffer | string, o?: {
        namespace?: string;
        ttl?: number;
    }): Promise<void>;
    delete(key: string, o?: {
        namespace?: string;
    }): Promise<void>;
    private op;
    /** Compare-and-set: write value only if the current value equals expected (null: only if absent). value null deletes. */
    cas(key: string, expected: Buffer | string | null, value: Buffer | string | null, o?: {
        namespace?: string;
        ttl?: number;
    }): Promise<boolean>;
    incr(key: string, by?: number, o?: {
        namespace?: string;
    }): Promise<number>;
    expire(key: string, ttl: number, o?: {
        namespace?: string;
    }): Promise<boolean>;
    hset(key: string, fields: Record<string, Buffer | string>, o?: {
        namespace?: string;
    }): Promise<number>;
    hget(key: string, field: string, o?: {
        namespace?: string;
    }): Promise<Buffer | null>;
    hgetall(key: string, o?: {
        namespace?: string;
    }): Promise<Record<string, Buffer>>;
    rpush(key: string, values: (Buffer | string)[], o?: {
        namespace?: string;
    }): Promise<number>;
    lpush(key: string, values: (Buffer | string)[], o?: {
        namespace?: string;
    }): Promise<number>;
    lrange(key: string, start?: number, stop?: number, o?: {
        namespace?: string;
    }): Promise<Buffer[]>;
    sadd(key: string, members: string[], o?: {
        namespace?: string;
    }): Promise<number>;
    smembers(key: string, o?: {
        namespace?: string;
    }): Promise<string[]>;
}
/** Conversation memory: the last messages of each session. */
export declare class Memory {
    private kv;
    static readonly namespace = "memory";
    static readonly maxMessages = 40;
    static readonly ttl: number;
    constructor(kv: KV);
    history(sessionId: string, last?: number): Promise<Message[]>;
    append(sessionId: string, user: string, assistant: string): Promise<void>;
    clear(sessionId: string): Promise<void>;
}
export interface Hit {
    id: string;
    score: number;
    text: string;
    metadata: Record<string, string>;
    similarity: number;
    keyword: number;
}
/** The app's private vector collections; ingested documents are in "sources". */
export declare class Vectors {
    /** Best matches first. mode: "vector" (meaning), "keyword" (BM25) or "hybrid". */
    search(collection: string, query: string | number[], o?: {
        k?: number;
        filter?: Record<string, string>;
        mode?: "vector" | "keyword" | "hybrid";
    }): Promise<Hit[]>;
    /** records: { id, text, vector?, metadata? }. Missing vectors are embedded. */
    upsert(collection: string, records: {
        id: string;
        text?: string;
        vector?: number[];
        metadata?: Record<string, unknown>;
    }[]): Promise<number>;
}
export interface Job {
    id: string;
    name: string;
    state: string;
    attempts: number;
    maxAttempts: number;
    lastError: string;
    result: unknown;
}
/** Durable background jobs declared under `jobs:`. */
export declare class Jobs {
    /** Queues a job. With key, an unfinished job with the same key is returned instead of a duplicate. */
    enqueue(name: string, payload?: unknown, o?: {
        delay?: number;
        key?: string;
    }): Promise<Job>;
    get(id: string): Promise<Job>;
}
export interface EventBatch {
    records: Event[];
    nextOffset: number;
    partition: number;
    assigned: number[];
}
/** Event topics: publish, and read with consumer groups. */
export declare class Events {
    publish(topic: string, value: unknown, o?: {
        key?: string;
        headers?: Record<string, string>;
    }): Promise<number>;
    publishMany(topic: string, values: unknown[], o?: {
        key?: string;
        headers?: Record<string, string>;
    }): Promise<number>;
    /** Records after consumer's committed position; call ack(batch, consumer) once handled. */
    fetch(topic: string, consumer: string, o?: {
        member?: string;
        limit?: number;
        wait?: number;
    }): Promise<EventBatch>;
    ack(b: EventBatch, consumer: string): Promise<void>;
}
/** Read-only SQL over the databases under `insights:`. */
export declare class SQL {
    query(database: string, query: string): Promise<{
        columns: string[];
        rows: unknown[][];
        truncated: boolean;
    }>;
}
/** Finished spans of one invocation, sent to the core in batches. */
export declare class SpanBuffer {
    readonly invocation: string;
    spans: object[];
    closed: boolean;
    constructor(invocation: string);
    add(rec: object): void;
    flush(): Promise<void>;
}
/** A step in the request's trace; see app.span(). */
export declare class Span {
    readonly name: string;
    readonly attrs: Record<string, unknown>;
    error: string;
    traceId: string;
    spanId: string;
    parentId: string;
    private start;
    constructor(name: string, attrs?: Record<string, unknown>);
    set(key: string, value: unknown): this;
    fail(message: string): this;
    get traceparent(): string;
    /** Runs fn inside the span: calls made in it (models, storage, tools) become its children. */
    run<T>(fn: (span: Span) => T | Promise<T>): Promise<T>;
}
export declare class App {
    readonly models: Record<string, Model>;
    readonly kv: KV;
    readonly memory: Memory;
    readonly vectors: Vectors;
    readonly jobs: Jobs;
    readonly events: Events;
    readonly sql: SQL;
    /** Declares a tool for app.models.X.run: `app.tool({ name, description, parameters }, fn)`. */
    tool: typeof tool;
    /** Runs fn as a step of the request's trace: `await app.span("rerank", { k: 8 }, async (s) => ...)`. */
    span<T>(name: string, attrs: Record<string, unknown>, fn: (span: Span) => T | Promise<T>): Promise<T>;
    /** `{ traceparent }` for the current request or span, to send to services you call. */
    traceHeaders(): Record<string, string>;
    /** The app's parsed ai-app.yaml, as the core loaded it. */
    get manifest(): Record<string, any>;
    /** The app's MCP tools: [{ name, description, parameters }]. */
    mcpTools(): Promise<{
        name: string;
        description: string;
        parameters: unknown;
    }[]>;
    /** Runs one MCP tool through the core: [text, isError]. */
    callMcpTool(name: string, args: Record<string, unknown>): Promise<[string, boolean]>;
}
export declare const app: App;
/** Adds JSON metadata to the current response's end event (e.g. citations). */
export declare function setMetadata(key: string, value: unknown): void;
