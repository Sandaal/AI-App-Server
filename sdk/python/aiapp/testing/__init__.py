"""Test apps with `aiapp test`.

Put tests in the app's ``tests/`` folder::

    from aiapp.testing import AppTest

    class LeaveQuestions(AppTest):
        def test_answers_from_the_policy(self):
            self.models.reply("Employees get 25 days of paid leave [1].", when="leave")
            r = self.client.chat("How many days of leave do I get?")
            self.assertIn("25 days", r.text)
            self.assertEqual(r.citations[0]["source"], "README.md")
            self.assertIn("25 days of paid annual leave", self.models.last.system)  # the passage reached the model

``aiapp test`` starts a throwaway server, deploys a copy of the app with every
model pointed at scripted fakes (:class:`FakeModels`), and runs the tests.
Everything else is real: routes, workers, storage, document search, jobs,
workflows and guardrails.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from aiapp.testing.models import Call, FakeModels, embed

__all__ = ["AppTest", "Call", "ChatResult", "Client", "FakeModels", "Harness", "Response", "embed", "harness"]

TEST_ENV = "aiapp-test"


@dataclass
class Response:
    status: int
    headers: dict[str, str]
    text: str

    def json(self) -> Any:
        return json.loads(self.text)

    @property
    def invocation_id(self) -> str:
        return self.headers.get("x-invocation-id", "")


@dataclass
class ChatResult:
    status: int
    text: str
    citations: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    events: list[tuple[str, str]] = field(default_factory=list)
    invocation_id: str = ""


class Client:
    """Calls the app under test over HTTP, like a real client."""

    def __init__(self, base: str, app: str, headers: dict[str, str] | None = None):
        self.base = base.rstrip("/")
        self.app = app
        self.headers = dict(headers or {})

    def url(self, route: str, query: dict | None = None) -> str:
        u = f"{self.base}/apps/{self.app}{route if route.startswith('/') else '/' + route}"
        if query:
            u += "?" + urllib.parse.urlencode(query)
        return u

    def request(self, method: str, route: str, body: bytes | None = None, headers: dict | None = None,
                query: dict | None = None, timeout: float = 120) -> Response:
        req = urllib.request.Request(self.url(route, query), data=body, method=method,
                                     headers={**self.headers, **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return Response(r.status, {k.lower(): v for k, v in r.headers.items()}, r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            return Response(e.code, {k.lower(): v for k, v in e.headers.items()}, e.read().decode("utf-8", "replace"))

    def post(self, route: str, json_body: Any = None, *, data: bytes | str | None = None, headers: dict | None = None,
             query: dict | None = None, timeout: float = 120) -> Response:
        """POST JSON (json_body) or raw data."""
        h = dict(headers or {})
        if json_body is not None:
            body = json.dumps(json_body).encode()
            h.setdefault("Content-Type", "application/json")
        else:
            body = data.encode() if isinstance(data, str) else data
        return self.request("POST", route, body, h, query, timeout)

    def get(self, route: str, *, headers: dict | None = None, query: dict | None = None) -> Response:
        return self.request("GET", route, None, headers, query)

    def upload(self, route: str, path_or_bytes, filename: str | None = None, *, query: dict | None = None,
               content_type: str = "application/octet-stream") -> Response:
        """POST a file's bytes with X-Filename, as the upload pages do."""
        if isinstance(path_or_bytes, (bytes, bytearray)):
            data, name = bytes(path_or_bytes), filename or "upload.bin"
        else:
            with open(path_or_bytes, "rb") as f:
                data = f.read()
            name = filename or os.path.basename(str(path_or_bytes))
        return self.request("POST", route, data, {"X-Filename": name, "Content-Type": content_type}, query)

    def chat(self, message: str, *, session: str | None = None, route: str = "/chat", headers: dict | None = None) -> ChatResult:
        """Asks a streaming chat route and collects the answer (applying guardrail replacements)."""
        h = {"Content-Type": "application/json", "Accept": "text/event-stream", **(headers or {})}
        if session:
            h["X-Session-Id"] = session
        r = self.request("POST", route, json.dumps({"message": message}).encode(), h)
        res = ChatResult(r.status, "", invocation_id=r.invocation_id)
        if r.status >= 400 or "text/event-stream" not in r.headers.get("content-type", ""):
            res.text = r.text
            return res
        for block in r.text.replace("\r\n", "\n").split("\n\n"):
            event, data = "message", []
            for line in block.split("\n"):
                if line.startswith("event:"):
                    event = line[6:].strip()
                elif line.startswith("data:"):
                    data.append(line[6:] if line.startswith("data: ") else line[5:])
            if not data and event == "message":
                continue
            d = "\n".join(data)
            res.events.append((event, d))
            if event == "message":
                res.text += d
            elif event == "replace":
                res.text = d
            elif event == "end":
                res.metadata = json.loads(d or "{}")
                res.citations = res.metadata.get("citations") or []
        return res


class Harness:
    """The deployed test copy of the app, its fake models and its server."""

    def __init__(self) -> None:
        env = os.environ
        missing = [k for k in ("AIAPP_TEST_URL", "AIAPP_TEST_APP_DIR", "AIAPP_TEST_BIN") if not env.get(k)]
        if missing:
            raise RuntimeError("run these tests with `aiapp test` (it starts the server they need)")
        self.url = env["AIAPP_TEST_URL"]
        self.dir = env["AIAPP_TEST_APP_DIR"]
        self.bin = env["AIAPP_TEST_BIN"]
        self.app = env["AIAPP_TEST_APP"]
        self.model_names = [m for m in env.get("AIAPP_TEST_MODELS", "").split(",") if m]
        self.models = FakeModels()
        self.client = Client(self.url, self.app)
        self._deployed = False

    def cli(self, *args: str, check: bool = True) -> str:
        """Runs an aiapp command against the test server and returns its output."""
        p = subprocess.run([self.bin, *args], capture_output=True, text=True, timeout=600)
        if check and p.returncode != 0:
            raise AssertionError(f"aiapp {' '.join(args)} failed:\n{p.stdout}{p.stderr}")
        return p.stdout + p.stderr

    def deploy(self) -> None:
        """Deploys the test copy with every model on the fakes (once)."""
        if self._deployed:
            return
        base = self.models.start()
        lines = ["# written by aiapp test: every model answers from the test's script", "models:"]
        for name in self.model_names:
            lines.append(f"  {name}: {{use: '', provider: openai-compatible, endpoint: '{base}', model: {name}, "
                         f"api_key_env: '', fallback: '', cache: false}}")
        with open(os.path.join(self.dir, f"ai-app.{TEST_ENV}.yaml"), "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        self.cli("deploy", self.dir, "--env", TEST_ENV)
        self._deployed = True

    def wait_jobs(self, timeout: float = 60) -> None:
        """Waits until the app has no queued or running jobs."""
        end = time.time() + timeout
        while time.time() < end:
            out = self.cli("jobs", self.app, check=False)
            if "queued" not in out and "running" not in out:
                return
            time.sleep(0.3)
        raise AssertionError("jobs still running after %ss" % timeout)

    def key(self, *roles: str, name: str = "test") -> str:
        """Creates an API key (with roles) and returns it."""
        args = ["key", "create", self.app, "--name", name]
        for r in roles:
            args += ["--role", r]
        out = self.cli(*args)
        for word in out.split():
            if word.startswith("aiapp_"):
                return word.strip(".,")
        raise AssertionError("no key in: " + out)

    def logs(self, limit: int = 50) -> list[dict]:
        """The app's recent audit records (model calls, guardrail decisions)."""
        out = self.cli("logs", self.app, "--json", "--limit", str(limit))
        return [json.loads(line) for line in out.splitlines() if line.startswith("{")]


_harness: Harness | None = None


def harness() -> Harness:
    """The shared harness (the app is deployed on first use)."""
    global _harness
    if _harness is None:
        _harness = Harness()
    _harness.deploy()
    return _harness


class AppTest(unittest.TestCase):
    """Base class for app tests: ``self.client``, ``self.models``, ``self.harness``.
    Model scripts are cleared before each test."""

    harness: Harness
    client: Client
    models: FakeModels

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.harness = harness()
        cls.client = cls.harness.client
        cls.models = cls.harness.models

    def setUp(self) -> None:
        super().setUp()
        self.models.reset()

