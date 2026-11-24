"""The ``app`` object handlers use to reach models (and, later, storage).

    from aiapp import app

    async def chat(req):
        async for token in app.models.chat.stream(req.text, system="Be brief."):
            yield token

Every call is a host call to the core, which holds the provider keys, applies
retry and fallback, and records token usage.
"""

from __future__ import annotations

import asyncio
import contextlib
import inspect
import json
import logging
import secrets
import time
import types
import typing
import uuid
from collections.abc import AsyncIterator, Callable, Iterable
from dataclasses import dataclass, field

import grpc
from google.protobuf import struct_pb2

from aiapp import host
from aiapp.request import Event
from aiapp.v1 import worker_pb2 as pb


class ModelError(Exception):
    """A provider call failed after the core's retries and fallback."""

    def __init__(self, code: str, message: str, retryable: bool) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


Message = dict[str, str]  # {"role": ..., "content": ...}


_JSON_TYPES = {str: "string", int: "integer", float: "number", bool: "boolean", list: "array", dict: "object"}


def _type_schema(t) -> dict:
    origin = typing.get_origin(t)
    if origin in (typing.Union, types.UnionType):
        args = [a for a in typing.get_args(t) if a is not type(None)]
        return _type_schema(args[0]) if len(args) == 1 else {}
    if origin is typing.Literal:
        return {"enum": list(typing.get_args(t))}
    if origin in (list, tuple, set):
        args = typing.get_args(t)
        return {"type": "array", "items": _type_schema(args[0]) if args else {}}
    if origin is dict:
        return {"type": "object"}
    return {"type": _JSON_TYPES[t]} if t in _JSON_TYPES else {}


@dataclass
class Tool:
    """A Python function the model may call."""

    name: str
    description: str
    parameters: dict
    fn: Callable

    @classmethod
    def from_function(cls, fn: Callable, name: str | None = None, description: str | None = None) -> "Tool":
        hints = typing.get_type_hints(fn)
        props, required = {}, []
        for pname, param in inspect.signature(fn).parameters.items():
            if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
                continue
            props[pname] = _type_schema(hints.get(pname, str))
            if param.default is inspect.Parameter.empty:
                required.append(pname)
        doc = inspect.getdoc(fn) or ""
        return cls(
            name=name or fn.__name__,
            description=description or doc.split("\n\n")[0].replace("\n", " "),
            parameters={"type": "object", "properties": props, "required": required},
            fn=fn,
        )

    async def call(self, args: dict):
        result = self.fn(**args)
        if inspect.isawaitable(result):
            result = await result
        return result


@dataclass
class AgentResult:
    text: str  # the model's final answer
    steps: list[dict] = field(default_factory=list)  # {"tool", "arguments", "result", "error"}
    messages: list[dict] = field(default_factory=list)  # the whole conversation, for follow-ups


def _as_text(value) -> str:
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, default=str)
    except TypeError:
        return str(value)


_IMAGE_MAGIC = [(b"\x89PNG", "image/png"), (b"\xff\xd8\xff", "image/jpeg"), (b"GIF8", "image/gif")]


def _image_part(image) -> pb.ImagePart:
    """bytes (type detected), (bytes, mime_type), or {"data": ..., "mime_type": ...}."""
    if isinstance(image, dict):
        data, mime = image["data"], image.get("mime_type")
    elif isinstance(image, tuple):
        data, mime = image
    else:
        data, mime = image, None
    data = bytes(data)
    if not mime:
        mime = next((m for magic, m in _IMAGE_MAGIC if data.startswith(magic)), None)
        if mime is None and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            mime = "image/webp"
    if mime not in ("image/png", "image/jpeg", "image/gif", "image/webp"):
        raise ValueError("images must be PNG, JPEG, GIF or WebP (pass (data, mime_type) if detection fails)")
    return pb.ImagePart(mime_type=mime, data=data)


def build_messages(
    user: str | None,
    system: str | None,
    history: Iterable[Message] | None,
    messages: Iterable[Message] | None,
    images: Iterable | None = None,
) -> list[pb.ChatMessage]:
    out: list[pb.ChatMessage] = []
    if system:
        out.append(pb.ChatMessage(role="system", content=system))
    for m in list(history or ()) + list(messages or ()):
        msg = pb.ChatMessage(role=m["role"], content=m.get("content") or "", tool_call_id=m.get("tool_call_id", ""))
        for tc in m.get("tool_calls") or ():
            msg.tool_calls.append(pb.ToolCallMsg(id=tc["id"], name=tc["name"], arguments_json=json.dumps(tc["arguments"])))
        msg.images.extend(_image_part(im) for im in m.get("images") or ())
        out.append(msg)
    if user is not None or images:
        msg = pb.ChatMessage(role="user", content=user or "")
        msg.images.extend(_image_part(im) for im in images or ())
        out.append(msg)
    if not out:
        raise ValueError("give user=, messages= or history=")
    return out


class Model:
    """A logical model from the manifest's ``models:`` section."""

    def __init__(self, name: str) -> None:
        self.name = name

    async def stream(
        self,
        user: str | None = None,
        *,
        system: str | None = None,
        history: Iterable[Message] | None = None,
        messages: Iterable[Message] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        images: Iterable | None = None,
    ) -> AsyncIterator[str]:
        """Yield response text as it streams. ``images`` (bytes, PNG/JPEG/GIF/WebP)
        go with the user message to vision models. Raises ModelError on provider failure."""
        options = struct_pb2.Struct()
        if temperature is not None:
            options["temperature"] = temperature
        if max_tokens is not None:
            options["max_tokens"] = max_tokens
        req = pb.ChatRequest(
            invocation_id=host.current_invocation.get(),
            model=self.name,
            messages=build_messages(user, system, history, messages, images),
            options=options,
        )
        c = host.client()
        async for chunk in _chat_chunks(c, req):
            kind = chunk.WhichOneof("kind")
            if kind == "delta":
                yield chunk.delta
            elif kind == "error":
                raise ModelError(chunk.error.code, chunk.error.message, chunk.error.retryable)

    async def json(
        self,
        user: str | None = None,
        *,
        schema,
        name: str = "output",
        system: str | None = None,
        history: Iterable[Message] | None = None,
        messages: Iterable[Message] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        images: Iterable | None = None,
    ):
        """Ask for JSON matching schema and return it parsed (``images`` as in stream).

        schema is a JSON Schema dict, or a Pydantic model class (then an instance
        of it is returned). The core validates the model's answer and retries
        once with the validation error; ModelError(code="invalid_output") means
        it still did not match.
        """
        model_cls = schema if hasattr(schema, "model_json_schema") else None
        schema_dict = model_cls.model_json_schema() if model_cls else schema
        options = struct_pb2.Struct()
        options.update({"json_schema": schema_dict, "schema_name": name})
        if temperature is not None:
            options["temperature"] = temperature
        if max_tokens is not None:
            options["max_tokens"] = max_tokens
        req = pb.ChatRequest(
            invocation_id=host.current_invocation.get(),
            model=self.name,
            messages=build_messages(user, system, history, messages, images),
            options=options,
        )
        c = host.client()
        text = []
        async for chunk in _chat_chunks(c, req):
            kind = chunk.WhichOneof("kind")
            if kind == "delta":
                text.append(chunk.delta)
            elif kind == "error":
                raise ModelError(chunk.error.code, chunk.error.message, chunk.error.retryable)
        data = json.loads("".join(text))
        return model_cls.model_validate(data) if model_cls else data

    async def run(
        self,
        user: str | None = None,
        *,
        tools: Iterable[Callable | Tool] = (),
        mcp: bool = True,
        system: str | None = None,
        history: Iterable[Message] | None = None,
        max_steps: int = 8,
        temperature: float | None = None,
    ) -> AgentResult:
        """Let the model use tools until it can answer.

        tools are Python functions (or @app.tool ones); with mcp=True the
        app's MCP servers' tools are offered too. Each round the model either
        answers (done) or asks for tool calls, which run and are fed back. A
        failing tool is reported to the model as an error rather than raised.
        """
        local = {t.name: t for t in (x if isinstance(x, Tool) else Tool.from_function(x) for x in tools)}
        offered = [pb.ToolDef(name=t.name, description=t.description, parameters_json=json.dumps(t.parameters))
                   for t in local.values()]
        c = host.client()
        if mcp:
            listed = await c.stub.ToolList(pb.ToolListRequest(), metadata=c.metadata)
            offered += [t for t in listed.tools if t.name not in local]
        convo: list[dict] = list(history or ())
        if user is not None:
            convo.append({"role": "user", "content": user})
        steps: list[dict] = []
        for _ in range(max_steps):
            reply = await self.turn(convo, tools=offered, system=system, temperature=temperature)
            answer, calls = reply["text"], reply["calls"]
            if not calls:
                convo.append({"role": "assistant", "content": answer})
                return AgentResult(answer, steps, convo)
            convo.append({"role": "assistant", "content": answer, "tool_calls": calls})
            for call in calls:
                step = {"tool": call["name"], "arguments": call["arguments"], "result": None, "error": None}
                try:
                    if call["name"] in local:
                        result = _as_text(await local[call["name"]].call(call["arguments"]))
                    else:
                        resp = await c.stub.ToolCall(pb.ToolCallRequest(
                            invocation_id=host.current_invocation.get(), name=call["name"],
                            arguments_json=json.dumps(call["arguments"])), metadata=c.metadata)
                        result = resp.content
                        if resp.is_error:
                            step["error"] = result
                except Exception as e:  # report to the model; it may retry or answer anyway
                    result = f"Error: {type(e).__name__}: {e}"
                    step["error"] = result
                step["result"] = result[:2000]
                steps.append(step)
                convo.append({"role": "tool", "tool_call_id": call["id"], "content": result})
        raise ModelError("max_steps", f"no answer after {max_steps} rounds of tool calls", False)

    async def turn(self, messages: list[dict], *, tools=(), system: str | None = None,
                   temperature: float | None = None) -> dict:
        """One model turn: returns {"text": ..., "calls": [{"id", "name", "arguments"}]}.

        tools are ToolDef messages or {"name", "description", "parameters"}
        dicts. The result is plain JSON, so it can be saved as a workflow step.
        """
        defs = [t if isinstance(t, pb.ToolDef) else pb.ToolDef(
            name=t["name"], description=t.get("description", ""), parameters_json=json.dumps(t.get("parameters") or {}))
            for t in tools]
        options = struct_pb2.Struct()
        if temperature is not None:
            options["temperature"] = temperature
        req = pb.ChatRequest(invocation_id=host.current_invocation.get(), model=self.name,
                             messages=build_messages(None, system, messages, None), options=options, tools=defs)
        c = host.client()
        text, calls = [], []
        async for chunk in _chat_chunks(c, req):
            kind = chunk.WhichOneof("kind")
            if kind == "delta":
                text.append(chunk.delta)
            elif kind == "tool_call":
                tc = chunk.tool_call
                calls.append({"id": tc.id, "name": tc.name, "arguments": json.loads(tc.arguments_json or "{}")})
            elif kind == "error":
                raise ModelError(chunk.error.code, chunk.error.message, chunk.error.retryable)
        return {"text": "".join(text), "calls": calls}

    async def complete(self, user: str | None = None, **kwargs) -> str:
        """Return the whole response as one string."""
        return "".join([t async for t in self.stream(user, **kwargs)])

    async def transcribe(
        self, audio: bytes, *, filename: str = "audio.mp3", language: str | None = None, prompt: str | None = None,
    ) -> Transcript:
        """Turn a recording (mp3, m4a, wav, webm, ogg, flac; up to 25 MB) into text.
        ``language`` is an ISO-639-1 hint; ``prompt`` lists names and terms to spell right."""
        c = host.client()
        try:
            r = await c.stub.Transcribe(
                pb.TranscribeRequest(invocation_id=host.current_invocation.get(), model=self.name, audio=bytes(audio),
                                     filename=filename, language=language or "", prompt=prompt or ""),
                metadata=c.metadata,
            )
        except grpc.aio.AioRpcError as e:
            _raise_budget(e)
            if e.code() in (grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.INVALID_ARGUMENT, grpc.StatusCode.NOT_FOUND):
                raise ModelError("transcription_error", e.details(), e.code() == grpc.StatusCode.UNAVAILABLE) from None
            raise
        return Transcript(r.text, r.language, r.duration_seconds,
                          [{"start": s.start, "end": s.end, "text": s.text} for s in r.segments])

    async def embed(self, inputs: list[str]) -> list[list[float]]:
        """Embed each input string."""
        c = host.client()
        try:
            resp = await c.stub.Embed(
                pb.EmbedRequest(invocation_id=host.current_invocation.get(), model=self.name, inputs=inputs),
                metadata=c.metadata,
            )
        except grpc.aio.AioRpcError as e:
            _raise_budget(e)
            raise
        return [list(v.values) for v in resp.vectors]


@dataclass(frozen=True)
class Transcript:
    """The text of a recording; segments are timed pieces when the provider gives them."""

    text: str
    language: str = ""
    duration_seconds: float = 0.0
    segments: list[dict] = field(default_factory=list)  # {"start", "end", "text"}


def _raise_budget(e: grpc.aio.AioRpcError) -> None:
    if e.code() == grpc.StatusCode.RESOURCE_EXHAUSTED:
        raise ModelError("budget_exceeded", e.details(), False) from None


async def _chat_chunks(c, req):
    """The ChatStream chunks; a used-up model budget raises ModelError("budget_exceeded")."""
    try:
        async for chunk in c.stub.ChatStream(req, metadata=c.metadata):
            yield chunk
    except grpc.aio.AioRpcError as e:
        _raise_budget(e)
        raise


class _Models:
    def __init__(self) -> None:
        self._models: dict[str, Model] = {}

    def __getitem__(self, name: str) -> Model:
        if name not in self._models:
            self._models[name] = Model(name)
        return self._models[name]

    def __getattr__(self, name: str) -> Model:
        if name.startswith("_"):
            raise AttributeError(name)
        return self[name]


class KVError(Exception):
    """A key-value operation failed (e.g. a key holding the wrong kind of value)."""


class QuotaExceeded(KVError):
    """The app is over a storage or vector quota set by the operator; reads still work."""


class LeaseHeld(KVError):
    """The lease is held by someone else."""


async def _kv_call(fn, request):
    c = host.client()
    try:
        return await fn(c.stub)(request, metadata=c.metadata)
    except grpc.aio.AioRpcError as e:
        if e.code() == grpc.StatusCode.RESOURCE_EXHAUSTED:
            raise QuotaExceeded(e.details()) from None
        if e.code() in (grpc.StatusCode.FAILED_PRECONDITION, grpc.StatusCode.INVALID_ARGUMENT):
            raise KVError(e.details()) from None
        raise


def _b(v: bytes | str) -> bytes:
    return v.encode("utf-8") if isinstance(v, str) else bytes(v)


@dataclass(frozen=True)
class Lease:
    """A held lease. ``token`` grows with every new holder: pass it to the
    systems you write to, so they can reject a holder whose lease expired."""

    key: str
    owner: str
    token: int
    namespace: str = "default"


class KV:
    """The app's private key-value store and data structures.

    Plain values: ``get``, ``put``, ``delete``, ``cas``. Data structures, each
    stored per element and updated atomically: hashes (``hset``...), lists
    (``lpush``...), sets (``sadd``...), sorted sets (``zadd``...), counters
    (``incr``) and leases (``lease``). ``expire``/``ttl``/``type`` apply to
    data structures; ``put(ttl=...)`` sets a plain value's expiry. Values are
    bytes; str is UTF-8 encoded. Every method takes ``namespace=`` (default
    "default").
    """

    async def get(self, key: str, *, namespace: str = "default") -> bytes | None:
        resp = await _kv_call(lambda s: s.KVGet, pb.KVGetRequest(namespace=namespace, key=key))
        return bytes(resp.value) if resp.found else None

    async def put(self, key: str, value: bytes | str, *, namespace: str = "default", ttl: int = 0) -> None:
        """Store value; ttl (seconds) > 0 makes it expire."""
        await _kv_call(
            lambda s: s.KVPut, pb.KVPutRequest(namespace=namespace, key=key, value=_b(value), ttl_seconds=ttl)
        )

    async def delete(self, key: str, *, namespace: str = "default") -> None:
        """Delete the plain value and any data structure named key."""
        await _kv_call(lambda s: s.KVDelete, pb.KVDeleteRequest(namespace=namespace, key=key))
        await self._op("delete", key, namespace)

    async def _op(self, op: str, key: str, namespace: str, **fields) -> pb.KVOpResponse:
        return await _kv_call(lambda s: s.KVOp, pb.KVOpRequest(namespace=namespace, key=key, op=op, **fields))

    # --- plain values ---

    async def cas(
        self, key: str, expected: bytes | str | None, value: bytes | str | None, *,
        namespace: str = "default", ttl: float = 0,
    ) -> bool:
        """Compare-and-set: write value only if the current value equals
        expected (None: only if the key doesn't exist). value None deletes.
        Returns whether the write happened."""
        f = {"ttl_ms": int(ttl * 1000)}
        if expected is None:
            f["expect_absent"] = True
        else:
            f["expected"] = _b(expected)
        if value is None:
            f["delete_value"] = True
        else:
            f["value"] = _b(value)
        return (await self._op("cas", key, namespace, **f)).ok

    # --- any data structure ---

    async def type(self, key: str, *, namespace: str = "default") -> str | None:
        """'hash', 'list', 'set', 'zset', 'counter' or 'lease'; None if missing."""
        return (await self._op("type", key, namespace)).text or None

    async def expire(self, key: str, ttl: float, *, namespace: str = "default") -> bool:
        """Expire the data structure after ttl seconds (0 removes the expiry)."""
        return (await self._op("expire", key, namespace, ttl_ms=int(ttl * 1000))).ok

    async def ttl(self, key: str, *, namespace: str = "default") -> float | None:
        """Seconds until the structure expires; -1 if it never does; None if missing."""
        r = await self._op("ttl", key, namespace)
        if not r.ok:
            return None
        return -1 if r.n < 0 else r.n / 1000

    async def len(self, key: str, *, namespace: str = "default") -> int:
        """Number of elements in a hash, list, set or sorted set (0 if missing)."""
        return (await self._op("len", key, namespace)).n

    # --- counters ---

    async def incr(self, key: str, by: int = 1, *, namespace: str = "default") -> int:
        """Atomically add by (may be negative) and return the new value."""
        return (await self._op("incr", key, namespace, delta=float(by))).n

    # --- hashes ---

    async def hset(self, key: str, fields: dict[str, bytes | str], *, namespace: str = "default") -> int:
        """Set fields; returns how many were new."""
        names = list(fields)
        return (await self._op("hset", key, namespace, fields=names, values=[_b(fields[n]) for n in names])).n

    async def hget(self, key: str, field: str, *, namespace: str = "default") -> bytes | None:
        r = await self._op("hget", key, namespace, fields=[field])
        return bytes(r.value) if r.ok else None

    async def hgetall(self, key: str, *, namespace: str = "default") -> dict[str, bytes]:
        r = await self._op("hgetall", key, namespace)
        return {f: bytes(v) for f, v in zip(r.fields, r.values)}

    async def hdel(self, key: str, *fields: str, namespace: str = "default") -> int:
        return (await self._op("hdel", key, namespace, fields=list(fields))).n

    # --- lists ---

    async def lpush(self, key: str, *values: bytes | str, namespace: str = "default") -> int:
        """Insert at the head (the last value given ends up first); returns the length."""
        return (await self._op("lpush", key, namespace, values=[_b(v) for v in values])).n

    async def rpush(self, key: str, *values: bytes | str, namespace: str = "default") -> int:
        """Append at the tail; returns the length."""
        return (await self._op("rpush", key, namespace, values=[_b(v) for v in values])).n

    async def lpop(self, key: str, count: int = 1, *, namespace: str = "default") -> list[bytes]:
        return [bytes(v) for v in (await self._op("lpop", key, namespace, count=count)).values]

    async def rpop(self, key: str, count: int = 1, *, namespace: str = "default") -> list[bytes]:
        return [bytes(v) for v in (await self._op("rpop", key, namespace, count=count)).values]

    async def lrange(self, key: str, start: int = 0, stop: int = -1, *, namespace: str = "default") -> list[bytes]:
        """Elements start..stop inclusive; negative indexes count from the end."""
        return [bytes(v) for v in (await self._op("lrange", key, namespace, start=start, stop=stop)).values]

    # --- sets ---

    async def sadd(self, key: str, *members: str, namespace: str = "default") -> int:
        return (await self._op("sadd", key, namespace, fields=list(members))).n

    async def srem(self, key: str, *members: str, namespace: str = "default") -> int:
        return (await self._op("srem", key, namespace, fields=list(members))).n

    async def sismember(self, key: str, member: str, *, namespace: str = "default") -> bool:
        return (await self._op("sismember", key, namespace, fields=[member])).ok

    async def smembers(self, key: str, *, namespace: str = "default") -> list[str]:
        return list((await self._op("smembers", key, namespace)).fields)

    # --- sorted sets ---

    async def zadd(self, key: str, members: dict[str, float], *, namespace: str = "default") -> int:
        """Set scores; returns how many members were new."""
        names = list(members)
        return (await self._op("zadd", key, namespace, fields=names, scores=[float(members[n]) for n in names])).n

    async def zincrby(self, key: str, member: str, by: float, *, namespace: str = "default") -> float:
        return (await self._op("zincrby", key, namespace, fields=[member], delta=float(by))).score

    async def zscore(self, key: str, member: str, *, namespace: str = "default") -> float | None:
        r = await self._op("zscore", key, namespace, fields=[member])
        return r.score if r.ok else None

    async def zrem(self, key: str, *members: str, namespace: str = "default") -> int:
        return (await self._op("zrem", key, namespace, fields=list(members))).n

    async def zrange(
        self, key: str, start: int = 0, stop: int = -1, *, reverse: bool = False, namespace: str = "default"
    ) -> list[tuple[str, float]]:
        """Members by rank (lowest score first, or highest with reverse=True)."""
        r = await self._op("zrange", key, namespace, start=start, stop=stop, reverse=reverse)
        return list(zip(r.fields, r.scores))

    async def zrangebyscore(
        self, key: str, min: float = float("-inf"), max: float = float("inf"), *,
        offset: int = 0, limit: int = 0, reverse: bool = False, namespace: str = "default",
    ) -> list[tuple[str, float]]:
        """Members with min <= score <= max."""
        r = await self._op("zrangebyscore", key, namespace, min=min, max=max, offset=offset, count=limit, reverse=reverse)
        return list(zip(r.fields, r.scores))

    # --- leases ---

    async def acquire(self, key: str, ttl: float, *, owner: str | None = None, namespace: str = "default") -> Lease | None:
        """Take or renew a lease for ttl seconds. Returns it, or None if someone else holds it."""
        owner = owner or _OWNER
        r = await self._op("acquire", key, namespace, owner=owner, ttl_ms=int(ttl * 1000))
        return Lease(key, owner, r.n, namespace) if r.ok else None

    async def release(self, lease: Lease) -> bool:
        """Free the lease if it is still held with this token."""
        return (await self._op("release", lease.key, lease.namespace, owner=lease.owner, token=lease.token)).ok

    @contextlib.asynccontextmanager
    async def lease(self, key: str, ttl: float, *, owner: str | None = None, namespace: str = "default"):
        """``async with app.kv.lease("nightly-report", 60) as lease:`` runs the
        block only while holding the lease (raises LeaseHeld otherwise) and
        releases it afterwards. Keep the block shorter than ttl, or renew with
        ``acquire`` using the same owner."""
        got = await self.acquire(key, ttl, owner=owner, namespace=namespace)
        if got is None:
            raise LeaseHeld(f"lease {key!r} is held by someone else")
        try:
            yield got
        finally:
            await self.release(got)


# Default lease owner: unique per worker process.
_OWNER = f"worker-{uuid.uuid4().hex[:12]}"


@dataclass(frozen=True)
class Hit:
    id: str
    score: float  # ranking score for the mode used (cosine, BM25, or fused)
    text: str
    metadata: dict[str, str]
    similarity: float = 0.0  # cosine similarity to the query, when known
    keyword: float = 0.0  # BM25 score; 0 when no query word matched


def _struct(d: dict | None) -> struct_pb2.Struct:
    s = struct_pb2.Struct()
    if d:
        s.update(d)
    return s


class Vectors:
    """The app's private vector collections. Ingested documents are in "sources"."""

    async def search(
        self,
        collection: str,
        query: str | list[float],
        k: int = 5,
        *,
        filter: dict[str, str] | None = None,
        mode: str = "vector",
    ) -> list[Hit]:
        """Best matches first.

        mode="vector" ranks by meaning (a text query is embedded with the app's
        "embedding" model), "keyword" by shared words (BM25, no embedding call),
        and "hybrid" fuses both, which finds exact terms like product codes that
        embeddings blur.
        """
        req = pb.VectorSearchRequest(collection=collection, k=k, filter=_struct(filter), mode=mode)
        if isinstance(query, str):
            req.query_text = query
        else:
            req.query_vector.values.extend(query)
        c = host.client()
        resp = await c.stub.VectorSearch(req, metadata=c.metadata)
        return [
            Hit(h.id, h.score, h.text, {k: str(v) for k, v in h.metadata.items()}, h.similarity, h.keyword)
            for h in resp.hits
        ]

    async def upsert(self, collection: str, records: list[dict]) -> int:
        """records: [{"id", "text", optional "vector", optional "metadata"}]. Missing vectors are embedded."""
        out = []
        for r in records:
            rec = pb.VectorRecord(id=r["id"], text=r.get("text", ""), metadata=_struct(r.get("metadata")))
            if r.get("vector"):
                rec.vector.values.extend(r["vector"])
            out.append(rec)
        c = host.client()
        resp = await c.stub.VectorUpsert(
            pb.VectorUpsertRequest(collection=collection, records=out), metadata=c.metadata
        )
        return resp.upserted


@dataclass(frozen=True)
class Job:
    id: str
    name: str
    state: str  # queued | running | done | dead | canceled
    attempts: int
    max_attempts: int
    last_error: str
    result: object  # the handler's JSON result, once done


def _job(info) -> Job:
    result = json.loads(info.result) if info.result else None
    return Job(info.id, info.name, info.state, info.attempts, info.max_attempts, info.last_error, result)


def _event_bytes(value) -> bytes:
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    if isinstance(value, str):
        return value.encode("utf-8")
    return json.dumps(value).encode("utf-8")


@dataclass(frozen=True)
class EventBatch:
    """Records read from a topic; continue (or commit) from ``next_offset``."""

    records: list[Event]
    next_offset: int
    partition: int = 0
    assigned: list[int] | None = None  # consumer groups: the partitions this member owns


class Events:
    """The app's event topics: append-only, ordered, replayable.

    Publish with ``publish``. Process them either by declaring a subscription
    in ai-app.yaml (the server delivers each record to a handler, in order and
    at least once), or by pulling: ``fetch`` from a named consumer's position
    and ``commit`` when done. ``read`` replays from an offset or a time.
    """

    async def publish(self, topic: str, value, *, key: str = "", headers: dict[str, str] | None = None) -> int:
        """Append one record; returns its offset. dicts and lists are sent as JSON."""
        return await self.publish_many(topic, [value], key=key, headers=headers)

    async def publish_many(self, topic: str, values: list, *, key: str = "", headers: dict[str, str] | None = None) -> int:
        """Append several records atomically; returns the first offset."""
        recs = [pb.EventRecord(key=key, headers=headers or {}, value=_event_bytes(v)) for v in values]
        resp = await _kv_call(lambda s: s.EventPublish, pb.EventPublishRequest(topic=topic, records=recs))
        return resp.first_offset

    async def read(
        self, topic: str, *, offset: int = 0, since: float | None = None, latest: bool = False,
        limit: int = 100, wait: float = 0, partition: int = 0,
    ) -> EventBatch:
        """Records from offset, or from the first at/after ``since`` (a unix
        timestamp), or only new ones (``latest``). ``wait`` blocks up to that
        many seconds (max 30) when there is nothing yet. ``partition`` picks
        one partition of a partitioned topic."""
        req = pb.EventReadRequest(topic=topic, from_offset=offset, limit=limit, wait_ms=int(wait * 1000), from_end=latest,
                                  partition=partition)
        if since is not None:
            req.from_time_unix_ms = int(since * 1000)
        return _batch(topic, await _kv_call(lambda s: s.EventRead, req))

    async def fetch(self, topic: str, consumer: str, *, member: str | None = None, limit: int = 100,
                    wait: float = 0) -> EventBatch:
        """Records after consumer's committed position (from the start for a
        new consumer). Call ``ack(batch, consumer)`` once they are handled;
        until then they are fetched again.

        On a partitioned topic, consumer is a group: give each worker its own
        ``member`` id and the server shares the partitions among the live
        members (one that stops fetching for 30 s loses its share). A batch
        comes from one partition (``batch.partition``)."""
        req = pb.EventReadRequest(topic=topic, consumer=consumer, member=member or "", limit=limit, wait_ms=int(wait * 1000))
        return _batch(topic, await _kv_call(lambda s: s.EventRead, req))

    async def commit(self, topic: str, consumer: str, next_offset: int, *, partition: int = 0) -> None:
        await _kv_call(lambda s: s.EventCommit, pb.EventCommitRequest(topic=topic, consumer=consumer, next_offset=next_offset,
                                                                       partition=partition))

    async def ack(self, batch: EventBatch, consumer: str) -> None:
        """Marks a fetched batch done (commits its next offset in its partition)."""
        if batch.records:
            await self.commit(batch.records[0].topic, consumer, batch.next_offset, partition=batch.partition)


def _batch(topic: str, resp) -> EventBatch:
    import datetime

    recs = [
        Event(
            topic=topic, offset=r.offset, key=r.key,
            time=datetime.datetime.fromtimestamp(r.time_unix_ms / 1000, datetime.timezone.utc).isoformat(),
            headers=dict(r.headers), value=bytes(r.value), partition=resp.partition,
        )
        for r in resp.records
    ]
    return EventBatch(recs, resp.next_offset, resp.partition, list(resp.assigned) or None)


class SQLError(Exception):
    """A query was refused (not read-only, unknown table) or failed in the database."""


class SQL:
    """Read-only queries on the databases under ``insights.databases`` in
    ai-app.yaml. The core runs them: one SELECT, a row limit, a time limit."""

    async def query(self, database: str, query: str) -> dict:
        """``{"columns": [...], "rows": [[...]], "truncated": bool}``; raises SQLError."""
        c = host.client()
        try:
            r = await c.stub.SQLQuery(pb.SQLRequest(database=database, query=query), metadata=c.metadata)
        except grpc.aio.AioRpcError as e:
            if e.code() in (grpc.StatusCode.INVALID_ARGUMENT, grpc.StatusCode.FAILED_PRECONDITION, grpc.StatusCode.NOT_FOUND):
                raise SQLError(e.details()) from None
            raise
        return {"columns": list(r.columns), "rows": json.loads(r.rows_json or "[]"), "truncated": r.truncated}

    async def tables(self, database: str) -> list[dict]:
        """The allowed tables: ``[{"name", "columns": ["col type", ...]}]``."""
        c = host.client()
        r = await c.stub.SQLQuery(pb.SQLRequest(database=database, schema=True), metadata=c.metadata)
        return json.loads(r.schema_json or "[]")


class Jobs:
    """Durable background jobs declared under jobs: in ai-app.yaml.

    A job handler is a normal handler; its request body is the payload and its
    JSON return value becomes the result. Failures are retried with backoff;
    jobs survive server restarts.
    """

    async def enqueue(self, name: str, payload=None, *, delay: float = 0, key: str | None = None) -> Job:
        """Queue a job. With key, an unfinished job with the same key is returned instead of a duplicate."""
        c = host.client()
        info = await c.stub.JobEnqueue(
            pb.JobEnqueueRequest(
                name=name,
                payload=json.dumps(payload).encode("utf-8"),
                delay_ms=int(delay * 1000),
                key=key or "",
            ),
            metadata=c.metadata,
        )
        return _job(info)

    async def get(self, job_id: str) -> Job:
        c = host.client()
        return _job(await c.stub.JobGet(pb.JobGetRequest(id=job_id), metadata=c.metadata))


class Memory:
    """Conversation history per session, kept in the app's KV store."""

    namespace = "memory"
    max_messages = 40
    ttl = 30 * 24 * 3600  # forget idle conversations after 30 days

    def __init__(self, kv: KV) -> None:
        self._kv = kv

    async def history(self, session_id: str, last: int = 10) -> list[Message]:
        """The most recent messages, oldest first, as {"role", "content"} dicts."""
        if not session_id:
            return []
        raw = await self._kv.get(session_id, namespace=self.namespace)
        msgs = json.loads(raw) if raw else []
        return msgs[-last:] if last > 0 else msgs

    async def append(self, session_id: str, user: str, assistant: str) -> None:
        if not session_id:
            return
        msgs = await self.history(session_id, last=0)
        msgs += [{"role": "user", "content": user}, {"role": "assistant", "content": assistant}]
        await self._kv.put(
            session_id, json.dumps(msgs[-self.max_messages :]), namespace=self.namespace, ttl=self.ttl
        )

    async def clear(self, session_id: str) -> None:
        await self._kv.delete(session_id, namespace=self.namespace)


_span_log = logging.getLogger("aiapp.spans")
_span_tasks: set = set()  # keeps fire-and-forget uploads alive


class SpanBuffer:
    """Finished spans of one invocation, sent to the core in batches."""

    def __init__(self, invocation: str) -> None:
        self.invocation = invocation
        self.spans: list = []
        self.closed = False

    def add(self, rec) -> None:
        self.spans.append(rec)
        if self.closed or len(self.spans) >= 100:
            _spawn(self.flush())

    async def flush(self) -> None:
        batch, self.spans = self.spans, []
        if not batch:
            return
        try:
            c = host.client()
            await c.stub.RecordSpans(pb.RecordSpansRequest(invocation_id=self.invocation, spans=batch), metadata=c.metadata)
        except Exception as e:  # tracing never fails the handler
            _span_log.debug("could not send %d spans: %s", len(batch), e)

    async def close(self) -> None:
        self.closed = True
        await self.flush()


def _spawn(coro) -> None:
    try:
        task = asyncio.get_running_loop().create_task(coro)
    except RuntimeError:  # no event loop (a sync thread): drop
        coro.close()
        return
    _span_tasks.add(task)
    task.add_done_callback(_span_tasks.discard)


def _attr(v):
    if isinstance(v, (str, bool, int, float)) or v is None:
        return v
    return str(v)


class Span:
    """A step of your handler in the request's trace (``aiapp trace``, the
    console, and your OTLP backend)::

        with app.span("rerank", candidates=len(docs)) as s:
            docs = rerank(docs)
            s.set("kept", len(docs))

    ``async with`` works too. Spans nest, and model, storage and tool calls
    made inside one appear as its children. An exception marks the span
    failed and still propagates. Attribute values should be names, counts
    and ids; don't put prompts or personal data in them."""

    def __init__(self, name: str, attrs: dict) -> None:
        self.name = name
        self.attrs = dict(attrs)
        self.error = ""
        self.trace_id = self.span_id = self.parent_id = ""
        self._token = None
        self._parent = None
        self._start = 0

    def set(self, key: str, value) -> "Span":
        """Add or change an attribute."""
        self.attrs[key] = value
        return self

    def fail(self, message: str) -> "Span":
        """Mark the span failed without raising."""
        self.error = message
        return self

    @property
    def traceparent(self) -> str:
        """W3C trace context for this span, to pass to services you call."""
        return f"00-{self.trace_id}-{self.span_id}-01" if self.span_id else ""

    def __enter__(self) -> "Span":
        self._parent = host.current_trace.get()
        if self._parent:
            self.trace_id, self.parent_id = self._parent
        else:  # outside a traced request: start a trace
            self.trace_id = secrets.token_hex(16)
        self.span_id = secrets.token_hex(8)
        self._token = host.current_trace.set((self.trace_id, self.span_id))
        self._start = time.time_ns()
        return self

    def __exit__(self, et, ev, tb) -> bool:
        end = time.time_ns()
        try:
            host.current_trace.reset(self._token)
        except ValueError:  # exited in another context (e.g. a generator moved tasks)
            host.current_trace.set(self._parent)
        if ev is not None and not self.error:
            self.error = f"{et.__name__}: {ev}"
        attrs = struct_pb2.Struct()
        attrs.update({str(k): _attr(v) for k, v in self.attrs.items()})
        rec = pb.SpanRecord(trace_id=self.trace_id, span_id=self.span_id, parent_span_id=self.parent_id, name=self.name,
                            start_unix_nano=self._start, end_unix_nano=end, attributes=attrs, error=self.error)
        buf = host.pending_spans.get()
        if buf is None:  # outside an invocation (startup, a detached task): send on its own
            buf = SpanBuffer(host.current_invocation.get())
            buf.closed = True
        buf.add(rec)
        return False

    async def __aenter__(self) -> "Span":
        return self.__enter__()

    async def __aexit__(self, et, ev, tb) -> bool:
        return self.__exit__(et, ev, tb)


class App:
    @staticmethod
    def workflow(fn):
        """Decorator for durable workflows; see aiapp.workflow."""
        from aiapp.workflow import workflow

        return workflow(fn)

    def tool(self, fn: Callable | None = None, *, name: str | None = None, description: str | None = None):
        """Decorator: make a function usable as a tool (schema from its type hints, description from its docstring)."""

        def wrap(f: Callable) -> Tool:
            return Tool.from_function(f, name, description)

        return wrap(fn) if fn is not None else wrap

    @staticmethod
    def span(name: str, **attributes) -> Span:
        """A span in the request's trace: ``with app.span("rerank", docs=12) as s: ...``"""
        return Span(name, attributes)

    @staticmethod
    def trace_headers() -> dict[str, str]:
        """``{"traceparent": ...}`` for the current request or span, to send to
        services you call over HTTP so their spans join this trace ({} if untraced)."""
        tr = host.current_trace.get()
        return {"traceparent": f"00-{tr[0]}-{tr[1]}-01"} if tr else {}

    @property
    def manifest(self) -> dict:
        """The app's parsed ai-app.yaml, as the core loaded it."""
        import os

        return json.loads(os.environ.get("AIAPP_MANIFEST") or "{}")

    async def mcp_tools(self) -> list[dict]:
        """The app's MCP tools as {"name", "description", "parameters"} dicts."""
        c = host.client()
        listed = await c.stub.ToolList(pb.ToolListRequest(), metadata=c.metadata)
        return [{"name": t.name, "description": t.description, "parameters": json.loads(t.parameters_json or "{}")}
                for t in listed.tools]

    async def call_mcp_tool(self, name: str, arguments: dict) -> tuple[str, bool]:
        """Run one MCP tool through the core; returns (text, is_error)."""
        c = host.client()
        resp = await c.stub.ToolCall(pb.ToolCallRequest(invocation_id=host.current_invocation.get(), name=name,
                                                        arguments_json=json.dumps(arguments)), metadata=c.metadata)
        return resp.content, resp.is_error

    def __init__(self) -> None:
        self.models = _Models()
        self.kv = KV()
        self.vectors = Vectors()
        self.memory = Memory(self.kv)
        self.jobs = Jobs()
        self.events = Events()
        self.sql = SQL()


app = App()
