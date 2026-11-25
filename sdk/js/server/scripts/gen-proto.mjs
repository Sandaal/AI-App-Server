// Turns core/proto/aiapp/v1/worker.proto into src/proto.json, the descriptor
// the runtime loads (so it needs no .proto files at run time).
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import protobuf from "protobufjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const src = path.resolve(here, "../../../../core/proto/aiapp/v1/worker.proto");
const root = new protobuf.Root();
root.loadSync(src, { keepCase: true });
fs.writeFileSync(path.resolve(here, "../src/proto.json"), JSON.stringify(root.toJSON({ keepComments: false })));
console.log("wrote src/proto.json from", path.relative(process.cwd(), src));
