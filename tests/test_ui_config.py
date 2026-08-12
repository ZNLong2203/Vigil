"""The bundled UI has to be able to reach the API it ships with.

This is the test that was missing when the deployed page spent its whole life
showing committed fixtures. Nothing was broken in a way anything could see: the
key never made it into the JavaScript bundle, so every reader fell back, and
falling back is a designed behaviour that labels itself honestly. A green suite,
a healthy /health, correct-looking screens, and not one live request.

So this asserts the contract the browser depends on, from the outside: the key
is fetchable without already having the key, and it is the same key the rest of
the API demands.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from vigil.api import app, require_api_key
from vigil.config import get_settings


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("VIGIL_API_KEY", "test-key-1234")
    get_settings.cache_clear()
    yield TestClient(app)
    get_settings.cache_clear()


def test_ui_config_needs_no_key(client: TestClient) -> None:
    """Requiring the key to fetch the key is a loop with no way in."""
    response = client.get("/ui-config")
    assert response.status_code == 200


def test_ui_config_hands_out_the_key_the_api_accepts(client: TestClient) -> None:
    """The point of the endpoint: what it returns must open the other routes.

    Two independently plausible keys — one baked at build time, one demanded at
    runtime — is exactly how the UI ended up authenticating with an empty string
    against a service expecting a real one.
    """
    key = client.get("/ui-config").json()["api_key"]
    assert key == "test-key-1234"

    # A request with no key is refused before any handler runs, so this costs
    # nothing and proves the gate is actually on the route.
    assert client.get("/runs").status_code == 401

    # And the key just handed out satisfies that gate. Asserted against the
    # dependency rather than through a route: every authenticated endpoint talks
    # to Firestore, and a unit test that needs a database to answer a question
    # about authentication is a unit test that will one day fail for reasons
    # having nothing to do with authentication.
    require_api_key(x_api_key=key)

    with pytest.raises(HTTPException):
        require_api_key(x_api_key="not-the-key")


def test_public_ui_off_withholds_the_key(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """VIGIL_PUBLIC_UI=0 is the switch for a build with nothing live behind it."""
    monkeypatch.setenv("VIGIL_PUBLIC_UI", "0")
    get_settings.cache_clear()
    assert client.get("/ui-config").json()["api_key"] is None
