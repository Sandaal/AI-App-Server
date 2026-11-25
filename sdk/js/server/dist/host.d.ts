import { AsyncLocalStorage } from "node:async_hooks";
import * as grpc from "@grpc/grpc-js";
export declare const TOKEN_HEADER = "x-aiapp-token";
export declare const INVOCATION_HEADER = "x-aiapp-invocation";
export declare const MAX_MESSAGE: number;
export declare const proto: any;
/** Per-invocation context, carried across awaits. */
export interface Invocation {
    id: string;
    metadata: Record<string, unknown>;
    trace?: [traceId: string, spanId: string];
    spans?: SpanSink;
}
export interface SpanSink {
    add(rec: unknown): void;
}
export declare const current: AsyncLocalStorage<Invocation>;
/** Runs fn with ctx as the current invocation (spans nest by updating `trace`). */
export declare function withInvocation<T>(ctx: Invocation, fn: () => T): T;
export declare function connect(target: string, token: string): void;
export declare function hostClient(): {
    stub: any;
    token: string;
};
/** gRPC metadata for a Host call: worker token, invocation, trace context. */
export declare function metadata(): grpc.Metadata;
/** Calls a unary Host method and returns its response (as a promise). */
export declare function call<T = any>(method: string, request: object): Promise<T>;
/** Calls a server-streaming Host method and yields its messages. */
export declare function stream<T = any>(method: string, request: object): AsyncGenerator<T>;
/** The storage quota is used up (storage or vectors); reads still work. */
export declare class QuotaExceeded extends Error {
    constructor(message: string);
}
/** A core call failed (bad input, not found, unavailable...). */
export declare class HostError extends Error {
    code: string;
    constructor(code: string, message: string);
}
export declare function toValue(v: unknown): object;
export declare function toStruct(obj: Record<string, unknown> | undefined | null): object;
export declare function fromValue(v: any): unknown;
export declare function fromStruct(s: any): Record<string, unknown>;
export declare function toBytes(v: unknown): Buffer;
