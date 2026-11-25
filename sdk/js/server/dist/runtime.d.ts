export * from "./index.js";
/** Imports "module:function" from the app directory (module may be a path: lib/handlers:hello). */
export declare function resolveHandler(spec: string): Promise<Function>;
