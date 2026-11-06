"""Integration test cases for error handling in the views (#240 in result-service-gui).

Only a missing or expired login (401) sends the user to the login page. Other
errors send the user to the main page with an understandable message, and the
user is still logged in. If the main page itself fails, an error page is
shown. An event without organiser does not break the pages.
"""

from http import HTTPStatus

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient as _TestClient
from yarl import URL

from event_service_gui.adapters import EventsAdapter
from event_service_gui.views.utils import (
    LOGIN_AGAIN,
    UNEXPECTED_ERROR,
    error_text,
    is_login_error,
    raise_error,
)

from .test_system_status import login

EVENT = {
    "id": "e1",
    "name": "Test",
    "competition_format": "Individual Sprint",
    "date_of_event": "2026-11-06",
    "time_of_event": "12:00:00",
    "timezone": "Europe/Oslo",
    "organiser": "Lyn Ski",
    "webpage": "https://example.com",
    "information": "",
}
PAGE = "/events?event_id=e1"


def location(resp) -> tuple[str, dict]:
    url = URL(resp.headers["Location"])
    return url.path, dict(url.query)


async def returns(value):
    return value


@pytest.fixture
def fail_events_page(monkeypatch: pytest.MonkeyPatch):
    """Let get_event on the events page raise the error set in .error."""

    class State:
        error: Exception = TypeError("'NoneType' object is not subscriptable")

    state = State()

    async def fake_get_event(*_) -> dict:
        raise state.error

    monkeypatch.setattr("event_service_gui.views.events.get_event", fake_get_event)
    return state


@pytest.fixture
def main_page(monkeypatch: pytest.MonkeyPatch):
    """The main page with no backend: one event, or the error set in .error."""

    class State:
        error: Exception | None = None
        event: dict = EVENT

    state = State()

    async def get_all_events(*_) -> list:
        if state.error:
            raise state.error
        return []

    async def get_event(*_) -> dict:
        return state.event

    monkeypatch.setattr(EventsAdapter, "get_all_events", get_all_events)
    monkeypatch.setattr("event_service_gui.views.main.get_event", get_event)
    return state


# --- error_text and is_login_error ---------------------------------------------------


@pytest.mark.integration
def test_error_text() -> None:
    assert error_text(Exception("Klassen mangler")) == (
        "Det har oppstått en feil: Klassen mangler"
    )
    assert error_text(web.HTTPBadRequest(reason="Error - 404: Not found.")) == (
        "Det har oppstått en feil: Error - 404: Not found."
    )
    assert error_text(TypeError("'NoneType' object is not subscriptable")) == (
        UNEXPECTED_ERROR
    )


@pytest.mark.integration
def test_is_login_error() -> None:
    assert is_login_error(web.HTTPBadRequest(reason="401 Unathorized - get_event"))
    assert is_login_error(Exception("Login expired: <ClientResponse 401>"))
    assert not is_login_error(Exception("Klassen mangler"))
    assert not is_login_error(web.HTTPBadRequest(reason="Error - 404: race 401"))


@pytest.mark.integration
def test_raise_error_lets_redirects_through() -> None:
    redirect = web.HTTPSeeOther(location="/login?informasjon=Logg+inn")

    class View:
        request = None

    with pytest.raises(web.HTTPSeeOther) as e:
        raise_error(View(), redirect)  # type: ignore[arg-type]
    assert e.value is redirect


# --- A page that fails -------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.parametrize(
    ("error", "message"),
    [
        (TypeError("'NoneType' object is not subscriptable"), UNEXPECTED_ERROR),
        (Exception("Klassen mangler"), "Det har oppstått en feil: Klassen mangler"),
        (
            web.HTTPBadRequest(reason="Error - 404: Event not found."),
            "Det har oppstått en feil: Error - 404: Event not found.",
        ),
    ],
)
async def test_error_sends_to_main_page_with_message(
    client: _TestClient,
    fail_events_page,
    main_page,
    error: Exception,
    message: str,
) -> None:
    """Not to the login page: the user is still logged in."""
    await login(client, "admin")
    fail_events_page.error = error
    resp = await client.get(PAGE, allow_redirects=False)
    assert resp.status == HTTPStatus.SEE_OTHER
    assert location(resp) == ("/", {"informasjon": message})
    # Still logged in:
    resp = await client.get("/", allow_redirects=False)
    assert resp.status == HTTPStatus.OK
    assert 'href="/logout"' in await resp.text()


@pytest.mark.integration
async def test_expired_login_sends_to_login_page(
    client: _TestClient, fail_events_page
) -> None:
    await login(client, "admin")
    fail_events_page.error = web.HTTPBadRequest(reason="401 Unathorized - get_event")
    resp = await client.get(PAGE, allow_redirects=False)
    assert resp.status == HTTPStatus.SEE_OTHER
    assert location(resp) == ("/login", {"informasjon": LOGIN_AGAIN, "next": PAGE})


# --- The main page -----------------------------------------------------------------------


@pytest.mark.integration
async def test_main_page_error_shows_error_page(
    client: _TestClient, main_page
) -> None:
    """The other pages send errors to the main page, so it does not redirect."""
    main_page.error = TypeError("'NoneType' object is not subscriptable")
    await login(client, "admin")
    resp = await client.get("/", allow_redirects=False)
    assert resp.status == HTTPStatus.INTERNAL_SERVER_ERROR
    text = await resp.text()
    assert UNEXPECTED_ERROR in text
    assert 'href="/logout"' in text


@pytest.mark.integration
async def test_main_page_expired_login_sends_to_login_page(
    client: _TestClient, main_page
) -> None:
    main_page.error = Exception("401 Unathorized - get_all_events")
    await login(client, "admin")
    resp = await client.get("/", allow_redirects=False)
    assert resp.status == HTTPStatus.SEE_OTHER
    assert location(resp)[0] == "/login"


# --- Event without organiser ---------------------------------------------------------------


@pytest.mark.integration
async def test_event_without_organiser(client: _TestClient, main_page) -> None:
    """organiser is optional in event-service; the page uses the neutral style."""
    main_page.event = {**EVENT, "organiser": None}
    await login(client, "admin")
    resp = await client.get("/", allow_redirects=False)
    assert resp.status == HTTPStatus.OK
    assert "styles_whitelabel.css" in await resp.text()
