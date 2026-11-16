"""Integration test cases for coming back to the right page after login.

After a form post (e.g. Flytt on the start list), the login page used to
come back to the path of the post, e.g. /start_edit, without event and
class. Now it comes back to the page the form was on, from the Referer
header, if that page is on this site.
"""

from http import HTTPStatus

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient as _TestClient
from aiohttp.test_utils import make_mocked_request
from yarl import URL

from event_service_gui.views.utils import return_path

from .test_config_access import EVENT_ID, fakes, login, photo_service
from .test_start_edit import FakeRaceService, race_service

__all__ = ["fakes", "photo_service", "race_service"]  # fixtures used below

PAGE = f"/start_edit?event_id={EVENT_ID}&klasse=G16&runde=Q"


def request(method: str, path: str, referer: str | None = None) -> web.Request:
    headers = {"Host": "sprint.example.no"}
    if referer is not None:
        headers["Referer"] = referer
    return make_mocked_request(method, path, headers=headers)


@pytest.mark.integration
@pytest.mark.parametrize(
    ("method", "path", "referer", "expected"),
    [
        # a page: itself
        ("GET", PAGE, "https://sprint.example.no/", PAGE),
        # a form post: the page the form was on
        ("POST", "/start_edit", f"https://sprint.example.no{PAGE}", PAGE),
        ("POST", "/start_edit", "https://sprint.example.no/tasks", "/tasks"),
        # no Referer, or one from another site: the path of the post
        ("POST", "/start_edit", None, "/start_edit"),
        ("POST", "/start_edit", f"https://evil.example.com{PAGE}", "/start_edit"),
        # not to the login page, or to a path a browser may take as a host
        ("POST", "/start_edit", "https://sprint.example.no/login?x=1", "/start_edit"),
        ("POST", "/start_edit", "https://sprint.example.no//evil.com/", "/start_edit"),
    ],
)
def test_return_path(
    method: str, path: str, referer: str | None, expected: str
) -> None:
    assert return_path(request(method, path, referer)) == expected


def move_form(service: FakeRaceService) -> dict:
    return {
        "event_id": EVENT_ID,
        "klasse": "G16",
        "runde": "Q",
        "race_id": "qa1",
        "start_id": service.start_id("qa1", 2),
        "bib": "2",
        "new_heat": "qa2",
        "move_start": " Flytt ",
    }


async def post_from_page(client: _TestClient, form: dict) -> URL:
    """Post the form as the browser does from the start list page."""
    resp = await client.post(
        "/start_edit",
        data=form,
        headers={"Referer": str(client.make_url(PAGE))},
        allow_redirects=False,
    )
    assert resp.status == HTTPStatus.SEE_OTHER
    return URL(resp.headers["Location"])


@pytest.mark.integration
async def test_expired_login_during_move_comes_back_to_the_start_list(
    client: _TestClient, race_service: FakeRaceService
) -> None:
    await login(client, "result-admin")
    race_service.create_error = web.HTTPBadRequest(reason="Error - 401: Unauthorized.")

    url = await post_from_page(client, move_form(race_service))

    assert url.path == "/login"
    assert url.query["next"] == PAGE
    assert url.query["informasjon"].startswith(
        "Innloggingen er utløpt under flyttingen."
    )


@pytest.mark.integration
async def test_form_post_when_logged_out_comes_back_to_the_page(
    client: _TestClient, race_service: FakeRaceService
) -> None:
    url = await post_from_page(client, move_form(race_service))

    assert url.path == "/login"
    assert url.query["next"] == PAGE
    # nothing was changed
    assert race_service.bibs("qa1") == {1: 1, 2: 2, 3: 3}
