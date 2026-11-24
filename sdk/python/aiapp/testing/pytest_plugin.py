"""pytest fixtures for app tests (``aiapp test --pytest``)::

    def test_answers_from_the_policy(aiapp_client, aiapp_models):
        aiapp_models.reply("Employees get 25 days of paid leave [1].", when="leave")
        r = aiapp_client.chat("How many days of leave do I get?")
        assert "25 days" in r.text
        assert "25 days of paid annual leave" in aiapp_models.last.system

    def test_needs_a_role(aiapp_client, aiapp_key):
        key = aiapp_key("approver")
        assert aiapp_client.get("/_approvals/api", headers={"Authorization": "Bearer " + key}).status == 200

Fixtures:

- ``aiapp``: the :class:`~aiapp.testing.Harness` (the deployed test copy;
  ``aiapp.cli(...)``, ``aiapp.wait_jobs()``, ``aiapp.logs()``), shared by the session.
- ``aiapp_models``: the scripted fake models, cleared before each test.
- ``aiapp_client``: an HTTP client for the app's routes.
- ``aiapp_key``: makes API keys: ``aiapp_key("approver")``.

``aiapp test --pytest`` loads this plugin (``-p aiapp.testing.pytest_plugin``).
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from aiapp.testing import Client, FakeModels, Harness, harness


@pytest.fixture(scope="session")
def aiapp() -> Harness:
    """The test server's deployed copy of the app (deployed once per session)."""
    return harness()


@pytest.fixture
def aiapp_models(aiapp: Harness) -> FakeModels:
    """The scripted models, with every script cleared before the test."""
    aiapp.models.reset()
    return aiapp.models


@pytest.fixture
def aiapp_client(aiapp: Harness, aiapp_models: FakeModels) -> Client:
    """A client for the app's routes (models cleared first)."""
    return aiapp.client


@pytest.fixture
def aiapp_key(aiapp: Harness) -> Callable[..., str]:
    """Creates API keys with roles: ``aiapp_key("approver", name="reviewer")``."""

    def make(*roles: str, name: str = "test") -> str:
        return aiapp.key(*roles, name=name)

    return make
