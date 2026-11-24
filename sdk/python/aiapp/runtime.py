"""Worker runtime: serves the Worker gRPC service for one app.

The core starts it as::

    python -m aiapp.runtime --listen ADDR --host ADDR --app NAME --worker-id ID

in the app's directory. The per-worker token arrives in AIAPP_WORKER_TOKEN (never
on the command line, where other local users could read it). The runtime exits
when its stdin closes, so workers never outlive the core that started them.
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
import inspect
import json
import logging
import os
import sys
import threading
from typing import Any, Callable

import grpc
from google.protobuf import struct_pb2

from aiapp import __version__, host
from aiapp.app import SpanBuffer, _spawn
from aiapp.host import TOKEN_HEADER
from aiapp.request import Request, Response
from aiapp.v1 import worker_pb2 as pb
from aiapp.v1 import worker_pb2_grpc as pbg
from aiapp.workflow import Suspended

log = logging.getLogger("aiapp.runtime")


def resolve_handler(spec: str) -> Callable[..., Any]:
    """Import ``module:function`` from the app directory."""
    module_name, sep, func_name = spec.partition(":")
    if not sep or not module_name or not func_name:
        raise ValueError(f"handler {spec!r} must look like module:function")
    fn = getattr(importlib.import_module(module_name), func_name, None)
    if not callable(fn):
        raise ValueError(f"handler {spec!r} is not a callable")
    return fn


def to_bytes(item: Any) -> bytes:
    if isinstance(item, bytes):
        return item
    if isinstance(item, str):
        return item.encode("utf-8")
    if isinstance(item, (dict, list)):
        return json.dumps(item).encode("utf-8")
    return str(item).encode("utf-8")


def to_response(result: Any) -> Response:
    if isinstance(result, Response):
        return result
    if result is None:
        return Response(status=204)
    if isinstance(result, (dict, list)):
        return Response(json.dumps(result), content_type="application/json")
    if isinstance(result, bytes):
        return Response(result, content_type="application/octet-stream")
    return Response(str(result), content_type="text/plain; charset=utf-8")


def start_chunk(status: int, headers: dict[str, str], streaming: bool) -> pb.InvokeChunk:
    return pb.InvokeChunk(start=pb.ResponseStart(status=status, headers=headers, streaming=streaming))


def end_chunk() -> pb.InvokeChunk:
    md = struct_pb2.Struct()
    md.update(host.current_metadata.get() or {})
    return pb.InvokeChunk(end=pb.ResponseEnd(metadata=md))


def error_chunk(code: str, message: str) -> pb.InvokeChunk:
    return pb.InvokeChunk(error=pb.Error(code=code, message=message))


class WorkerService(pbg.WorkerServicer):
    def __init__(self, token: str) -> None:
        self._token = token
        self._handlers: dict[str, Callable[..., Any]] = {}
        self.in_flight = 0
        self.draining = False
        self.server: grpc.aio.Server | None = None
        # The core counts us ready when it handles Register, which can be just
        # before its reply (our session token) arrives here: requests wait for it.
        self.connected = asyncio.Event()

    def _authorized(self, context: grpc.aio.ServicerContext) -> bool:
        md = dict(context.invocation_metadata() or ())
        return md.get(TOKEN_HEADER) == self._token

    def _handler(self, spec: str) -> Callable[..., Any]:
        fn = self._handlers.get(spec)
        if fn is None:
            fn = self._handlers[spec] = resolve_handler(spec)
        return fn

    async def Invoke(self, request, context):
        if not self._authorized(context):
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, "invalid worker token")
        if not self.connected.is_set():
            try:
                await asyncio.wait_for(self.connected.wait(), timeout=10)
            except asyncio.TimeoutError:
                await context.abort(grpc.StatusCode.UNAVAILABLE, "worker is not registered with the core yet")
        self.in_flight += 1
        host.current_invocation.set(request.invocation_id)  # each RPC runs in its own task
        host.current_metadata.set({})
        host.current_trace.set(host.parse_traceparent(request.traceparent))
        spans = SpanBuffer(request.invocation_id)
        host.pending_spans.set(spans)
        try:
            try:
                fn = self._handler(request.handler)
            except Exception as e:  # import errors, typos in the manifest
                log.exception("cannot load handler %s", request.handler)
                yield error_chunk("handler_not_found", f"{type(e).__name__}: {e}")
                return
            try:
                result = fn(Request.from_proto(request))
                if inspect.isawaitable(result):
                    result = await result
                if inspect.isasyncgen(result):
                    yield start_chunk(200, {}, True)
                    async for item in result:
                        yield pb.InvokeChunk(data=to_bytes(item))
                    yield end_chunk()
                elif inspect.isgenerator(result):
                    # Sync generators run on the event loop; prefer async handlers for I/O.
                    yield start_chunk(200, {}, True)
                    for item in result:
                        yield pb.InvokeChunk(data=to_bytes(item))
                    yield end_chunk()
                else:
                    resp = to_response(result)
                    headers = dict(resp.headers)
                    if resp.content_type:
                        headers["content-type"] = resp.content_type
                    yield start_chunk(resp.status, headers, False)
                    body = to_bytes(resp.body)
                    if body:
                        yield pb.InvokeChunk(data=body)
                    yield end_chunk()
            except asyncio.CancelledError:
                raise
            except Suspended as e:  # a workflow waiting for an approval: not a failure
                log.info("%s (invocation %s)", e, request.invocation_id)
                yield error_chunk(Suspended.code, str(e))
            except Exception as e:
                log.exception("handler %s failed (invocation %s)", request.handler, request.invocation_id)
                yield error_chunk("handler_exception", f"{type(e).__name__}: {e}")
        finally:
            self.in_flight -= 1
            spans.closed = True  # spans that end later (detached tasks) are sent as they end
            if spans.spans:
                _spawn(spans.flush())  # after the response: spans never delay it

    async def Health(self, request, context):
        if not self._authorized(context):
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, "invalid worker token")
        return pb.HealthResponse(ready=not self.draining, in_flight=self.in_flight)

    async def Drain(self, request, context):
        if not self._authorized(context):
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, "invalid worker token")
        self.draining = True
        grace = request.grace_seconds or 10
        log.info("draining (grace %ss)", grace)
        asyncio.get_running_loop().create_task(self.server.stop(grace))
        return pb.DrainResponse()


MAX_MESSAGE = 32 << 20


def exit_when_stdin_closes() -> None:
    """The core holds our stdin open; EOF means it is gone, so stop immediately."""

    def watch() -> None:
        try:
            while sys.stdin.buffer.read(4096):
                pass
        except (OSError, ValueError):
            pass
        os._exit(0)

    threading.Thread(target=watch, name="parent-watch", daemon=True).start()


def apply_limits() -> None:
    """Per-worker limits the core asks for (Unix): the largest file a handler
    may write, so one app can't fill the disk with a single runaway file."""
    n = int(os.environ.get("AIAPP_WORKER_MAX_FILE_BYTES") or 0)
    if n <= 0:
        return
    try:
        import resource  # noqa: PLC0415  (Unix only)
        import signal  # noqa: PLC0415

        signal.signal(signal.SIGXFSZ, signal.SIG_IGN)  # writes past the limit raise OSError instead
        resource.setrlimit(resource.RLIMIT_FSIZE, (n, n))
    except (ImportError, AttributeError, ValueError, OSError) as e:
        log.warning("could not set the file size limit: %s", e)


def preload_handlers() -> None:
    """Import every handler the manifest names before registering, so a
    version with a broken import never becomes ready (the old one keeps
    serving)."""
    try:
        m = json.loads(os.environ.get("AIAPP_MANIFEST") or "{}")
    except ValueError:
        return
    specs = [r.get("handler") for r in m.get("routes") or []]
    for key in ("subscriptions", "cron", "guardrails"):
        specs += [e.get("handler") for e in m.get(key) or [] if isinstance(e, dict)]
    for spec in dict.fromkeys(s for s in specs if s):
        try:
            resolve_handler(spec)
        except Exception as e:
            raise RuntimeError(f"handler {spec} can't be loaded: {type(e).__name__}: {e}") from e


async def serve(args: argparse.Namespace, token: str) -> None:
    apply_limits()
    preload_handlers()
    svc = WorkerService(token)
    # Requests can carry recordings and images (up to 25 MB): raise gRPC's 4 MB default.
    limits = [("grpc.max_receive_message_length", MAX_MESSAGE), ("grpc.max_send_message_length", MAX_MESSAGE)]
    server = grpc.aio.server(options=limits)
    svc.server = server
    pbg.add_WorkerServicer_to_server(svc, server)
    server.add_insecure_port(args.listen)
    await server.start()

    channel = grpc.aio.insecure_channel(args.host, options=limits)
    v = sys.version_info
    resp = await pbg.HostStub(channel).Register(
        pb.RegisterRequest(
            app=args.app,
            worker_id=args.worker_id,
            runtime=f"python{v.major}.{v.minor}",
            sdk_version=__version__,
        ),
        metadata=((TOKEN_HEADER, token),),
        timeout=10,
    )
    host.connect(channel, resp.session_token)
    svc.connected.set()
    log.info("worker %s registered for app %s on %s", args.worker_id, args.app, args.listen)
    try:
        await server.wait_for_termination()
    finally:
        await channel.close()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="aiapp.runtime")
    parser.add_argument("--listen", required=True, help="gRPC address to serve, e.g. unix:/run/w1.sock")
    parser.add_argument("--host", required=True, help="gRPC address of the core's Host service")
    parser.add_argument("--app", required=True)
    parser.add_argument("--worker-id", required=True)
    args = parser.parse_args(argv)

    token = os.environ.pop("AIAPP_WORKER_TOKEN", "")
    if not token:
        sys.exit("AIAPP_WORKER_TOKEN is not set; workers are started by `aiapp serve`")

    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stderr,
        format="%(levelname)s %(name)s: %(message)s",
    )
    sys.path.insert(0, os.getcwd())  # handlers live in the app directory
    exit_when_stdin_closes()
    code = 0
    try:
        asyncio.run(serve(args, token))
    except KeyboardInterrupt:
        pass
    except BaseException:
        log.exception("worker failed")
        code = 1
    # Skip interpreter finalization: the stdin watcher is blocked in read(), and
    # finalizing around it aborts with "could not acquire lock for <stdin>".
    logging.shutdown()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)


if __name__ == "__main__":
    main()
