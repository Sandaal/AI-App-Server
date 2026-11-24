"""A scripted, OpenAI-compatible model server for tests.

`aiapp test` points every model in the app at it, so handlers run unchanged
against replies the test chooses:

    self.models.reply("You get 25 days of leave [1].", when="leave")
    self.models.json({"label": "billing", "confidence": 0.9, "reason": "refund"})
    self.models.tool_call("lookup_order", {"id": "A-1"}, then="Order A-1 has shipped.")
    self.models.fail(503)            # the next call fails, to test fallbacks

Embeddings are deterministic word-overlap vectors, so document search finds
passages that share words with the question. Every request is recorded in
``self.models.calls`` for assertions.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable

DIM = 256
DEFAULT_REPLY = "This is a scripted test reply."
_WORD = re.compile(r"[a-z0-9]+")


_STOP = set("""a an and are as at be by can could did do does for from get got has have how i if in into is it its
me my no not of on or our so than that the their them then there these they this to too us was we were what when
where which who why will with would you your about any""".split())


def _words(text: str) -> set[str]:
    out = set()
    for w in _WORD.findall(text.lower()):
        if w in _STOP:
            continue
        if len(w) > 3 and w.endswith("s"):
            w = w[:-1]
        out.add(w)
    return out


def embed(text: str) -> list[float]:
    """Word-presence vector without stopwords: texts that share words are
    close, unrelated ones are near 0, like a (very) small embedding model."""
    v = [0.0] * DIM
    for w in _words(text):
        v[int.from_bytes(hashlib.blake2b(w.encode(), digest_size=4).digest(), "big") % DIM] += 1.0
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


@dataclass
class Call:
    """One request the app made to a model."""

    kind: str  # chat | embed | transcribe
    model: str
    messages: list[dict] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    schema: dict | None = None
    inputs: list[str] = field(default_factory=list)

    @property
    def prompt(self) -> str:
        """The last user message."""
        for m in reversed(self.messages):
            if m.get("role") == "user":
                c = m.get("content")
                return c if isinstance(c, str) else " ".join(p.get("text", "") for p in c or [] if isinstance(p, dict))
        return ""

    @property
    def system(self) -> str:
        return "\n".join(str(m.get("content", "")) for m in self.messages if m.get("role") == "system")


@dataclass
class _Rule:
    when: Callable[[Call], bool]
    reply: Any  # str | dict (JSON) | ("tool", name, args) | ("fail", status)
    times: int | None
    model: str | None

    def matches(self, call: Call) -> bool:
        return (self.times is None or self.times > 0) and (self.model is None or self.model == call.model) and self.when(call)


def _matcher(when) -> Callable[[Call], bool]:
    if when is None:
        return lambda c: True
    if callable(when):
        return when
    if isinstance(when, re.Pattern):
        return lambda c: bool(when.search(c.prompt))
    needle = str(when).lower()
    if needle.startswith("system:"):
        sys_needle = needle[len("system:"):].strip()
        return lambda c: sys_needle in c.system.lower()
    return lambda c: needle in c.prompt.lower()


class FakeModels:
    """The scripted models. Rules are tried in the order added; the first match answers."""

    def __init__(self) -> None:
        self._rules: list[_Rule] = []
        self._lock = threading.Lock()
        self.calls: list[Call] = []
        self.transcripts: list[str] = []
        self._server: ThreadingHTTPServer | None = None

    # --- scripting ---------------------------------------------------------
    def reply(self, text: str, when=None, *, model: str | None = None, times: int | None = None) -> "FakeModels":
        """Answer with text. when: a substring of the user's message (or "system:..."), a regex, or fn(call)."""
        self._add(when, text, times, model)
        return self

    def json(self, obj: Any, when=None, *, model: str | None = None, times: int | None = None) -> "FakeModels":
        """Answer structured-output calls (app.models.X.json) with obj."""
        self._add(when, {"__json__": obj}, times, model)
        return self

    def tool_call(self, name: str, arguments: dict | None = None, when=None, *, then: str | None = None,
                  model: str | None = None) -> "FakeModels":
        """Call a tool once; with then=, answer with that text after the tool result comes back."""
        self._add(when, ("tool", name, arguments or {}), 1, model)
        if then is not None:
            self._add(lambda c: bool(c.messages) and c.messages[-1].get("role") == "tool", then, 1, model)
        return self

    def fail(self, status: int = 500, when=None, *, times: int | None = 1, model: str | None = None) -> "FakeModels":
        """Make matching calls fail with an HTTP status (once by default)."""
        self._add(when, ("fail", status), times, model)
        return self

    def transcript(self, text: str) -> "FakeModels":
        """What speech-to-text returns next (in order; the last one repeats)."""
        self.transcripts.append(text)
        return self

    def reset(self) -> None:
        with self._lock:
            self._rules.clear()
            self.calls.clear()
            self.transcripts.clear()

    def _add(self, when, reply, times, model) -> None:
        with self._lock:
            self._rules.append(_Rule(_matcher(when), reply, times, model))

    # --- assertions ----------------------------------------------------------
    def chat_calls(self) -> list[Call]:
        return [c for c in self.calls if c.kind == "chat"]

    @property
    def last(self) -> Call:
        chats = self.chat_calls()
        if not chats:
            raise AssertionError("the app made no chat model calls")
        return chats[-1]

    # --- serving -------------------------------------------------------------
    def _answer(self, call: Call):
        with self._lock:
            self.calls.append(call)
            for r in self._rules:
                if r.matches(call):
                    if r.times is not None:
                        r.times -= 1
                    return r.reply
        if call.schema is not None:
            return {"__json__": _example(call.schema)}
        return DEFAULT_REPLY

    def start(self) -> str:
        """Starts the server and returns its base URL (…/v1)."""
        models = self

        class H(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *a):  # quiet
                pass

            def _json(self, status: int, obj) -> None:
                b = json.dumps(obj).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(b)))
                self.end_headers()
                self.wfile.write(b)

            def do_POST(self):
                raw = self.rfile.read(int(self.headers.get("Content-Length") or 0))
                path = self.path.split("?")[0]
                if path.endswith("/embeddings"):
                    body = json.loads(raw)
                    inputs = body.get("input") or []
                    inputs = [inputs] if isinstance(inputs, str) else inputs
                    with models._lock:
                        models.calls.append(Call("embed", body.get("model", ""), inputs=list(inputs)))
                    data = [{"index": i, "embedding": embed(t)} for i, t in enumerate(inputs)]
                    return self._json(200, {"data": data, "model": body.get("model", ""),
                                            "usage": {"prompt_tokens": sum(len(t.split()) for t in inputs)}})
                if path.endswith("/audio/transcriptions"):
                    with models._lock:
                        text = (models.transcripts.pop(0) if len(models.transcripts) > 1 else
                                (models.transcripts[0] if models.transcripts else "This is a test recording."))
                        models.calls.append(Call("transcribe", ""))
                    return self._json(200, {"text": text, "language": "en", "duration": 12.0,
                                            "segments": [{"start": 0.0, "end": 12.0, "text": text}]})
                if not path.endswith("/chat/completions"):
                    return self._json(404, {"error": {"message": "not a model endpoint"}})
                body = json.loads(raw)
                rf = body.get("response_format") or {}
                call = Call("chat", body.get("model", ""), messages=body.get("messages") or [],
                            tools=[t["function"]["name"] for t in body.get("tools") or []],
                            schema=(rf.get("json_schema") or {}).get("schema") if rf.get("type") == "json_schema" else None)
                reply = models._answer(call)
                if isinstance(reply, tuple) and reply[0] == "fail":
                    return self._json(reply[1], {"error": {"message": f"scripted failure {reply[1]}"}})
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Connection", "close")
                self.end_headers()

                def send(obj) -> None:
                    self.wfile.write(b"data: " + json.dumps(obj).encode() + b"\n\n")

                mdl = body.get("model", "scripted")
                prompt_tokens = sum(len(str(m.get("content", "")).split()) for m in call.messages)
                if isinstance(reply, tuple) and reply[0] == "tool":
                    send({"model": mdl, "choices": [{"delta": {"tool_calls": [{"index": 0, "id": "call_1", "function": {
                        "name": reply[1], "arguments": json.dumps(reply[2])}}]}}]})
                    out_tokens = 5
                else:
                    text = json.dumps(reply["__json__"]) if isinstance(reply, dict) and "__json__" in reply else str(reply)
                    for piece in re.findall(r"\S+\s*|\s+", text) or [""]:
                        send({"model": mdl, "choices": [{"delta": {"content": piece}}]})
                    out_tokens = len(text.split())
                send({"model": mdl, "choices": [], "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": out_tokens}})
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()
                self.close_connection = True

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self._server.daemon_threads = True
        threading.Thread(target=self._server.serve_forever, name="fake-models", daemon=True).start()
        return f"http://127.0.0.1:{self._server.server_address[1]}/v1"

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()


def _example(schema: dict) -> Any:
    """A value that satisfies a JSON schema: the default reply to structured calls."""
    t = schema.get("type")
    if "enum" in schema:
        return schema["enum"][0]
    if "const" in schema:
        return schema["const"]
    if isinstance(t, list):
        t = next((x for x in t if x != "null"), t[0] if t else "string")
    if t == "object" or "properties" in schema:
        props = schema.get("properties") or {}
        return {k: _example(v) for k, v in props.items()}
    if t == "array":
        return [_example(schema.get("items") or {})] if schema.get("minItems") else []
    if t == "number":
        return 0.5 if (schema.get("maximum") or 2) <= 1 else 1.0
    if t == "integer":
        return 1
    if t == "boolean":
        return True
    return "test"
