import http from "node:http";

// A fake app server: routes is {"POST /apps/shop/chat": (req, body, res) => ...}.
export async function fakeServer(routes) {
  const seen = [];
  const srv = http.createServer(async (req, res) => {
    let body = "";
    for await (const c of req) body += c;
    seen.push({ method: req.method, url: req.url, headers: req.headers, body });
    const h = routes[`${req.method} ${req.url.split("?")[0]}`];
    if (!h) { res.writeHead(404, { "Content-Type": "application/json" }); res.end('{"error":"route not found"}'); return; }
    await h(req, body, res);
  });
  await new Promise((r) => srv.listen(0, "127.0.0.1", r));
  return { url: `http://127.0.0.1:${srv.address().port}`, seen, close: () => new Promise((r) => srv.close(r)) };
}

export function sse(res, events, { split = false } = {}) {
  res.writeHead(200, { "Content-Type": "text/event-stream", "X-Invocation-Id": "inv1", "X-Trace-Id": "t".repeat(32) });
  let out = "";
  for (const [event, data] of events) {
    out += (event ? `event: ${event}\n` : "") + String(data).split("\n").map((l) => "data: " + l).join("\n") + "\n\n";
  }
  if (!split) { res.end(out); return; }
  // Byte by byte, to exercise chunk boundaries.
  let i = 0;
  const t = setInterval(() => {
    if (i >= out.length) { clearInterval(t); res.end(); return; }
    res.write(out.slice(i, i + 3));
    i += 3;
  }, 1);
}
