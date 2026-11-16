"""Integration test cases for expired login in requests from the pages (#230).

The pages call some endpoints with XMLHttpRequest, e.g. to register DNS/DNF
or star a photo. Before, an expired login gave a redirect to /login, which
the request followed silently, or "Det har oppstått en feil: See Other". The
registration was not saved, and the user was not told. Now these endpoints
answer 401 with JSON, and the pages show a message with a link to log in.
"""

import json
import re
from http import HTTPStatus
from pathlib import Path

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient as _TestClient

from event_service_gui.views.utils import LOGIN_AGAIN

from .test_config_access import EVENT_ID, fakes, login, photo_service

__all__ = ["fakes", "photo_service"]  # fixtures used by the tests below

# The ways the adapters report 401 from a backend service.
BACKEND_401 = [
    Exception("401 Unathorized - get_event"),
    Exception("Login expired: <ClientResponse 401>"),
    web.HTTPBadRequest(reason="Error - 401: Unauthorized."),
    web.HTTPBadRequest(reason="get_contestant_by_bib failed - 401 - Unauthorized"),
]

# The requests the pages make, as (method, path, form).
REQUESTS = {
    "resultat_update": (
        "post",
        "/resultat_update",
        {"action": "generate_resultlist", "event_id": EVENT_ID, "raceclass": "G11"},
    ),
    "photo_update": ("post", "/photo_update", {"action": "star_on", "photo_id": "p1"}),
    "video_events": (
        "post",
        "/video_events",
        {"action": "status", "event_id": EVENT_ID},
    ),
    "resultat_edit_new": (
        "post",
        "/resultat_edit_new",
        {"event_id": EVENT_ID, "race_id": "r1", "update_result": "1", "ajax": "true"},
    ),
    "timing_info": (
        "get",
        f"/timing_info?action=DNS&event_id={EVENT_ID}&race_order=1",
        {},
    ),
}


async def send(client: _TestClient, name: str):  # noqa: ANN201
    method, path, form = REQUESTS[name]
    if method == "get":
        return await client.get(path, allow_redirects=False)
    return await client.post(path, data=form, allow_redirects=False)


async def assert_login_expired(resp) -> None:  # noqa: ANN001
    assert resp.status == HTTPStatus.UNAUTHORIZED
    assert resp.headers["Cache-Control"] == "no-store"
    assert resp.content_type == "application/json"
    assert json.loads(await resp.text()) == {
        "error": "unauthorized",
        "informasjon": LOGIN_AGAIN,
    }


@pytest.mark.integration
@pytest.mark.parametrize("name", list(REQUESTS))
async def test_not_logged_in_gives_401(client: _TestClient, name: str) -> None:
    """Before, a redirect to /login or "Det har oppstått en feil: See Other"."""
    await assert_login_expired(await send(client, name))


@pytest.fixture(params=BACKEND_401, ids=lambda e: str(e).split(" ")[0])
def backend_401(
    monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> None:
    """Let the backend services answer 401 in each of the endpoints."""

    async def fail(*_: object, **__: object) -> dict:
        raise request.param

    views = "event_service_gui.views"
    for target in [
        f"{views}.resultat_update.get_event",
        f"{views}.resultat_edit_new.get_event",
        f"{views}.photo_update.FotoService.star_photo",
        f"{views}.video_events.ConfigAdapter.get_config",
        f"{views}.timing_info.get_dns",
    ]:
        monkeypatch.setattr(target, fail)


@pytest.mark.integration
@pytest.mark.parametrize("name", list(REQUESTS))
async def test_backend_401_gives_401(
    client: _TestClient, fakes, backend_401, name: str
) -> None:
    """A login that expires in user-service during the request is also 401."""
    await login(client, "result-admin")
    await assert_login_expired(await send(client, name))


@pytest.mark.integration
async def test_result_form_without_ajax_still_goes_to_login(
    client: _TestClient,
) -> None:
    """The form posted the usual way still redirects to the login page."""
    form = dict(REQUESTS["resultat_edit_new"][2])
    del form["ajax"]
    resp = await client.post("/resultat_edit_new", data=form, allow_redirects=False)
    assert resp.status == HTTPStatus.SEE_OTHER
    assert resp.headers["Location"].startswith("/login?")


@pytest.mark.integration
async def test_other_errors_still_answered_as_before(
    client: _TestClient, fakes, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only 401 changes: other errors are still shown on the page."""

    async def fail(*_: object, **__: object) -> dict:
        raise Exception("Kunne ikke lagre")  # noqa: TRY002

    monkeypatch.setattr(
        "event_service_gui.views.photo_update.FotoService.star_photo", fail
    )
    await login(client, "result-admin")
    resp = await send(client, "photo_update")
    assert resp.status == HTTPStatus.OK
    assert await resp.text() == "Det har oppstått en feil: Kunne ikke lagre"


# --- The pages ------------------------------------------------------------------


TEMPLATES = Path("event_service_gui/templates")


@pytest.mark.integration
@pytest.mark.parametrize(
    "template",
    [
        "photos_edit.html",
        "resultat_edit_new.html",
        "timing.html",
        "corrections.html",
        "timing_dash.html",
    ],
)
def test_pages_handle_401(template: str) -> None:
    """Every response handler checks for 401 first."""
    text = (TEMPLATES / template).read_text()
    handlers = re.findall(r"onload = function\(\) \{\s*(.*)", text)
    assert handlers
    assert all(h.startswith("if (login_expired(this.status))") for h in handlers)


@pytest.mark.integration
def test_base_page_has_login_expired() -> None:
    text = (TEMPLATES / "open_base_new.html").read_text()
    assert "function login_expired(status)" in text
    assert '"/login?next=" + encodeURIComponent(' in text
