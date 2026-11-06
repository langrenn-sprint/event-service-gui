"""Integration test cases for activation links (#222).

Admin creates a user without password and gets an activation link to give to
the user. The link is /activate#<code>: browsers never send the part after #
to a server, so the code is not in access logs. The user sets the password on
the activation page, and is sent to the login page. A user without password
gets a clear message when trying to log in.
"""

import json
from datetime import UTC, datetime, timedelta

import pytest
from aiohttp.test_utils import TestClient as _TestClient
from aioresponses import aioresponses
from yarl import URL

from event_service_gui.adapters import UserAdapter
from event_service_gui.adapters.user_adapter import (
    INVALID_ACTIVATION,
    NOT_ACTIVATED,
    PASSWORD_TOO_SHORT,
)
from event_service_gui.views.activate import ACTIVATED, MISSING_CODE, NOT_EQUAL
from event_service_gui.views.users import activation_status

from .test_system_status import USER_SERVICE_URL, login

USERS_URL = f"{USER_SERVICE_URL}/users"
ACTIVATE_URL = f"{USER_SERVICE_URL}/activate"
EXPIRES = "2026-11-08T14:00:00Z"
ACTIVATION = {"user_id": "u1", "code": "hemmelig-kode", "expires": EXPIRES}


def mock_user_service() -> aioresponses:
    """Mock calls to user-service; calls to the test server pass through."""
    return aioresponses(passthrough=["http://127.0.0.1"])


def requests_to(mocked: aioresponses, url: str) -> list:
    """Return the JSON bodies sent to the url."""
    return [
        call.kwargs.get("json")
        for (method, request_url), calls in mocked.requests.items()
        if str(request_url) == url and method == "POST"
        for call in calls
    ]


def location(resp) -> tuple[str, dict]:
    url = URL(resp.headers["Location"])
    return url.path, dict(url.query)


def later(hours: int) -> str:
    return (datetime.now(UTC) + timedelta(hours=hours)).isoformat()


# --- Creating a user ---------------------------------------------------------------------


@pytest.mark.integration
async def test_create_user_without_password_shows_link_once(
    client: _TestClient,
) -> None:
    await login(client, "admin")
    form = {"create": "1", "newrole": "event-admin", "newusername": "ola"}
    with mock_user_service() as mocked:
        mocked.post(
            USERS_URL,
            status=201,
            headers={"Location": "/users/u1"},
            payload=ACTIVATION,
        )
        mocked.get(USERS_URL, payload=[], repeat=True)
        resp = await client.post("/users", data=form, allow_redirects=False)
        assert resp.status == 303
        # the code is never in a URL:
        assert "hemmelig-kode" not in resp.headers["Location"]
        assert location(resp) == (
            "/users",
            {"informasjon": "Brukeren ola er opprettet."},
        )

        first = await (await client.get("/users")).text()
        second = await (await client.get("/users")).text()

    assert requests_to(mocked, USERS_URL) == [
        {"role": "event-admin", "username": "ola"}
    ]
    assert 'data-path="/activate#hemmelig-kode"' in first
    assert "Aktiveringslenke for ola" in first
    assert "08.11.2026 kl. 15:00" in first  # Oslo time
    assert "hemmelig-kode" not in second


@pytest.mark.integration
async def test_create_user_with_password(client: _TestClient) -> None:
    await login(client, "admin")
    form = {
        "create": "1",
        "newrole": "admin",
        "newusername": "test",
        "newpassword": "et-langt-passord",
    }
    with mock_user_service() as mocked:
        mocked.post(USERS_URL, status=201, headers={"Location": "/users/u2"})
        resp = await client.post("/users", data=form, allow_redirects=False)

    assert location(resp)[1] == {"informasjon": "Ny bruker opprettet med id u2"}
    assert requests_to(mocked, USERS_URL) == [
        {"role": "admin", "username": "test", "password": "et-langt-passord"}
    ]


@pytest.mark.integration
async def test_create_user_with_too_short_password(client: _TestClient) -> None:
    await login(client, "admin")
    form = {
        "create": "1",
        "newrole": "admin",
        "newusername": "t",
        "newpassword": "kort",
    }
    with mock_user_service() as mocked:
        resp = await client.post("/users", data=form, allow_redirects=False)

    assert location(resp)[1] == {"informasjon": PASSWORD_TOO_SHORT}
    assert requests_to(mocked, USERS_URL) == []


@pytest.mark.integration
async def test_new_activation_link(client: _TestClient) -> None:
    """Admin makes a new link, e.g. to reset a forgotten password."""
    await login(client, "admin")
    form = {"new_activation": "1", "id": "u1", "username": "ola"}
    with mock_user_service() as mocked:
        mocked.post(f"{USERS_URL}/u1/activation", status=201, payload=ACTIVATION)
        mocked.get(USERS_URL, payload=[])
        resp = await client.post("/users", data=form, allow_redirects=False)
        page = await (await client.get("/users")).text()

    assert location(resp)[1] == {"informasjon": "Ny aktiveringslenke for ola er laget."}
    assert 'data-path="/activate#hemmelig-kode"' in page


@pytest.mark.integration
async def test_users_page_shows_status_and_buttons(client: _TestClient) -> None:
    await login(client, "admin")
    users = [
        {"id": "u1", "username": "kari", "role": "admin", "activated": True},
        {
            "id": "u2",
            "username": "ola",
            "role": "event-admin",
            "activated": False,
            "activation_expires": later(24),
        },
    ]
    with mock_user_service() as mocked:
        mocked.get(USERS_URL, payload=users)
        page = await (await client.get("/users")).text()

    assert "Ikke aktivert (lenken er gyldig til" in page
    assert 'value="Nullstill passord"' in page
    assert 'value="Ny aktiveringslenke"' in page


@pytest.mark.integration
@pytest.mark.parametrize(
    ("user", "expected"),
    [
        ({"activated": True}, "Aktivert"),
        ({}, "Aktivert"),  # from a user-service without activation
        ({"activated": True, "activation_expires": later(-1)}, "Aktivert"),
        ({"activated": False}, "Ikke aktivert"),
        (
            {"activated": False, "activation_expires": later(-1)},
            "Ikke aktivert (lenken er utløpt)",
        ),
    ],
)
def test_activation_status(user: dict, expected: str) -> None:
    assert activation_status(user) == expected


@pytest.mark.integration
def test_activation_status_pending() -> None:
    assert activation_status(
        {"activated": True, "activation_expires": later(2)}
    ).startswith("Aktivert (ny lenke gyldig til ")


# --- The activation page -----------------------------------------------------------------


@pytest.mark.integration
async def test_activation_page_without_login(client: _TestClient) -> None:
    resp = await client.get("/activate", allow_redirects=False)
    assert resp.status == 200
    assert resp.headers["Cache-Control"] == "no-store"
    text = await resp.text()
    assert 'name="password"' in text
    assert 'name="confirm"' in text
    assert 'minlength="10"' in text


async def activate(client: _TestClient, **form: str):  # noqa: ANN201
    return await client.post("/activate", data=form, allow_redirects=False)


@pytest.mark.integration
async def test_activate(client: _TestClient) -> None:
    with mock_user_service() as mocked:
        mocked.post(ACTIVATE_URL, status=204)
        resp = await activate(
            client, code="kode", password="et-langt-passord", confirm="et-langt-passord"
        )

    assert resp.status == 303
    assert location(resp) == ("/login", {"informasjon": ACTIVATED})
    assert requests_to(mocked, ACTIVATE_URL) == [
        {"code": "kode", "password": "et-langt-passord"}
    ]


@pytest.mark.integration
@pytest.mark.parametrize(
    ("form", "message"),
    [
        (
            {"code": "kode", "password": "et-langt-passord", "confirm": "et-annet"},
            NOT_EQUAL,
        ),
        ({"code": "kode", "password": "kort", "confirm": "kort"}, PASSWORD_TOO_SHORT),
        (
            {"code": "", "password": "et-langt-passord", "confirm": "et-langt-passord"},
            MISSING_CODE,
        ),
    ],
)
async def test_activate_checked_before_user_service(
    client: _TestClient, form: dict, message: str
) -> None:
    with mock_user_service() as mocked:
        resp = await activate(client, **form)

    assert resp.status == 200
    assert message in await resp.text()
    assert requests_to(mocked, ACTIVATE_URL) == []


@pytest.mark.integration
@pytest.mark.parametrize(
    ("status", "message"),
    [
        (400, INVALID_ACTIVATION),
        (422, PASSWORD_TOO_SHORT),
        (500, "Det har oppstått en feil. Prøv igjen senere."),
    ],
)
async def test_activate_refused_by_user_service(
    client: _TestClient, status: int, message: str
) -> None:
    with mock_user_service() as mocked:
        mocked.post(ACTIVATE_URL, status=status, payload={"detail": "x"})
        resp = await activate(
            client, code="kode", password="et-langt-passord", confirm="et-langt-passord"
        )

    assert resp.status == 200
    text = await resp.text()
    assert message in text
    assert 'value="kode"' in text  # the user can try again without the link


# --- Login -------------------------------------------------------------------------------


@pytest.mark.integration
async def test_login_not_activated(client: _TestClient) -> None:
    with mock_user_service() as mocked:
        mocked.post(f"{USER_SERVICE_URL}/login", status=403)
        resp = await client.post(
            "/login", data={"username": "ola", "password": "x"}, allow_redirects=False
        )

    assert resp.status == 200
    assert NOT_ACTIVATED in await resp.text()


# --- UserAdapter --------------------------------------------------------------------------


@pytest.mark.integration
async def test_adapter_create_user_without_password() -> None:
    with mock_user_service() as mocked:
        mocked.post(
            USERS_URL, status=201, headers={"Location": "/users/u1"}, payload=ACTIVATION
        )
        result = await UserAdapter().create_user("token", "admin", "ola", "")

    assert result == ("u1", ACTIVATION)
    assert "password" not in json.dumps(requests_to(mocked, USERS_URL))


@pytest.mark.integration
async def test_adapter_create_activation_errors() -> None:
    with mock_user_service() as mocked:
        mocked.post(f"{USERS_URL}/u1/activation", status=404)
        with pytest.raises(Exception, match="Fant ikke brukeren"):
            await UserAdapter().create_activation("token", "u1")
