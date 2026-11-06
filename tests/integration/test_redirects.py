"""Integration test cases for redirects raised by the views (#208) and /secret (#209).

The views raise redirects (web.HTTPSeeOther) instead of returning them, as
returning is deprecated in aiohttp. A redirect raised inside a
`try: ... except Exception` would be caught as an error, so the views that
have one let redirects (web.HTTPRedirection) through first. These tests take an action
whose redirect comes from inside such a try, and check that it arrives.
"""

import ast
from pathlib import Path

import pytest
from aiohttp.test_utils import TestClient as _TestClient
from yarl import URL

from event_service_gui.adapters import EventsAdapter, RaceplansAdapter
from event_service_gui.views import contestants, raceclasses

from .test_system_status import login

VIEWS = Path("event_service_gui/views")
EVENT = {"id": "e1", "name": "Test", "timezone": "Europe/Oslo", "organiser": "X"}


def location(resp) -> tuple[str, dict]:
    """Path and query of the redirect target."""
    url = URL(resp.headers["Location"])
    return url.path, dict(url.query)


async def returns(value):
    return value


@pytest.fixture
async def admin(client: _TestClient) -> _TestClient:
    await login(client, "admin")
    return client


@pytest.mark.integration
async def test_events_delete_redirects(
    admin: _TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(EventsAdapter, "delete_event", lambda *_: returns(204))
    resp = await admin.post(
        "/events", data={"delete": "1", "event_id": "e1"}, allow_redirects=False
    )
    assert resp.status == 303
    assert location(resp) == ("/", {"informasjon": "Arrangement er slettet 204."})


@pytest.mark.integration
async def test_raceclasses_update_order_redirects(
    admin: _TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(raceclasses, "update_order", lambda *_: returns("Lagret"))
    resp = await admin.post(
        "/raceclasses",
        data={"update_order": "1", "event_id": "e1"},
        allow_redirects=False,
    )
    assert resp.status == 303
    assert location(resp) == ("/tasks", {"event_id": "e1", "informasjon": "Lagret"})


@pytest.mark.integration
async def test_raceplans_generate_redirects(
    admin: _TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(RaceplansAdapter, "generate_raceplan", lambda *_: returns("OK"))
    resp = await admin.post(
        "/raceplans",
        data={"generate_raceplan": "1", "event_id": "e1"},
        allow_redirects=False,
    )
    assert resp.status == 303
    assert location(resp) == (
        "/tasks",
        {"event_id": "e1", "informasjon": "Opprettet kjøreplan - OK"},
    )


@pytest.mark.integration
async def test_contestants_create_one_redirects(
    admin: _TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(contestants, "get_event", lambda *_: returns(EVENT))
    monkeypatch.setattr(
        contestants,
        "create_one_contestant",
        lambda *_: returns("/contestants?event_id=e1&informasjon=Lagt+til"),
    )
    resp = await admin.post(
        "/contestants",
        data={"create_one": "1", "event_id": "e1"},
        allow_redirects=False,
    )
    assert resp.status == 303
    assert location(resp) == (
        "/contestants",
        {"event_id": "e1", "informasjon": "Lagt til"},
    )


@pytest.mark.integration
@pytest.mark.parametrize(
    ("error", "expected_path"),
    [("500 Internal Server Error", "/events"), ("401 Unauthorized", "/login")],
)
async def test_events_errors_still_handled(
    admin: _TestClient, monkeypatch: pytest.MonkeyPatch, error: str, expected_path: str
) -> None:
    """A real error is still caught: an error message, or login on 401."""

    async def fail(*_):
        raise Exception(error)

    monkeypatch.setattr(EventsAdapter, "delete_event", fail)
    resp = await admin.post(
        "/events", data={"delete": "1", "event_id": "e1"}, allow_redirects=False
    )
    assert resp.status == 303
    path, query = location(resp)
    assert path == expected_path
    if expected_path == "/events":
        assert query["informasjon"].startswith("Det har oppstått en feil")


@pytest.mark.integration
def test_no_returned_http_exceptions_in_views() -> None:
    """HTTP exceptions must be raised: returning them is deprecated in aiohttp."""
    returned = [
        f"{path.name}:{node.lineno}"
        for path in sorted(VIEWS.glob("*.py"))
        for node in ast.walk(ast.parse(path.read_text()))
        if isinstance(node, ast.Return)
        and isinstance(node.value, ast.Call)
        and ast.unparse(node.value.func).startswith("web.HTTP")
    ]
    assert returned == []


@pytest.mark.integration
async def test_secret_route_removed(admin: _TestClient) -> None:
    resp = await admin.get("/secret", allow_redirects=False)
    assert resp.status == 404
