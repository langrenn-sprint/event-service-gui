"""Integration test cases for user administration (#199).

Only admin may manage users: user-service answers 403 to everybody else. The
GUI hides the "Brukere" menu link, rejects GET and POST /users with a clear
message, and UserAdapter turns a 403 from user-service into a clear error.
"""

from collections.abc import Iterator

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient as _TestClient
from aioresponses import aioresponses
from yarl import URL

from event_service_gui.adapters import EventsAdapter, UserAdapter
from event_service_gui.adapters.user_adapter import (
    NO_ACCESS_CREATE,
    NO_ACCESS_DELETE,
    NO_ACCESS_READ,
)
from event_service_gui.views.users import NO_ACCESS

from .test_system_status import USER_SERVICE_URL, login

USERS_URL = f"{USER_SERVICE_URL}/users"
OTHER_ROLES = ["event-admin", "result-admin", "contestant-admin", ""]
MENU_LINK = 'id="myUsers"'


def location(resp) -> tuple[str, dict]:
    """Path and query of the redirect target."""
    url = URL(resp.headers["Location"])
    return url.path, dict(url.query)


def mock_user_service() -> aioresponses:
    """Mock calls to user-service; calls to the test server pass through.

    Used after login, as login mocks user-service itself.
    """
    return aioresponses(passthrough=["http://127.0.0.1"])


@pytest.fixture
def mocked() -> Iterator[aioresponses]:
    """Mocked user-service for the adapter tests, which do not log in."""
    with mock_user_service() as m:
        yield m


def user_service_calls(mocked: aioresponses) -> list:
    return [key for key in mocked.requests if str(key[1]).startswith(USERS_URL)]


# --- Menu link ----------------------------------------------------------------


async def start_page(client: _TestClient, monkeypatch: pytest.MonkeyPatch) -> str:
    async def no_events(*_) -> list:
        return []

    monkeypatch.setattr(EventsAdapter, "get_all_events", no_events)
    resp = await client.get("/")
    assert resp.status == 200
    return await resp.text()


@pytest.mark.integration
async def test_menu_link_shown_for_admin(
    client: _TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    await login(client, "admin")
    assert MENU_LINK in await start_page(client, monkeypatch)


@pytest.mark.integration
@pytest.mark.parametrize("role", OTHER_ROLES)
async def test_menu_link_hidden_for_other_roles(
    client: _TestClient, monkeypatch: pytest.MonkeyPatch, role: str
) -> None:
    await login(client, role)
    text = await start_page(client, monkeypatch)
    assert MENU_LINK not in text
    assert "/logout" in text  # the rest of the user menu is still there


# --- Access to /users ---------------------------------------------------------


@pytest.mark.integration
async def test_users_page_requires_login(client: _TestClient) -> None:
    resp = await client.get("/users", allow_redirects=False)
    assert resp.status == 303
    assert location(resp)[0] == "/login"


@pytest.mark.integration
@pytest.mark.parametrize("role", OTHER_ROLES)
async def test_users_page_rejected_for_other_roles(
    client: _TestClient, role: str
) -> None:
    await login(client, role)
    with mock_user_service() as mocked:
        resp = await client.get("/users", allow_redirects=False)
        assert resp.status == 303
        path, query = location(resp)
        assert path == "/login"
        assert query["informasjon"] == NO_ACCESS
        assert user_service_calls(mocked) == []


@pytest.mark.integration
@pytest.mark.parametrize("role", OTHER_ROLES)
@pytest.mark.parametrize(
    "form",
    [
        {
            "create": "1",
            "newrole": "admin",
            "newusername": "u",
            "newpassword": "p" * 10,
        },
        {"delete": "1", "id": "u1"},
    ],
)
async def test_users_post_rejected_for_other_roles(
    client: _TestClient, role: str, form: dict
) -> None:
    await login(client, role)
    with mock_user_service() as mocked:
        resp = await client.post("/users", data=form, allow_redirects=False)
        assert resp.status == 303
        path, query = location(resp)
        assert path == "/login"
        assert query["informasjon"] == NO_ACCESS
        # Nothing is sent to user-service:
        assert user_service_calls(mocked) == []


@pytest.mark.integration
async def test_users_page_admin(client: _TestClient) -> None:
    await login(client, "admin")
    with mock_user_service() as mocked:
        mocked.get(
            USERS_URL, payload=[{"id": "u1", "username": "kari", "role": "admin"}]
        )
        resp = await client.get("/users", allow_redirects=False)
        assert resp.status == 200
        assert "kari" in await resp.text()


@pytest.mark.integration
async def test_users_form_offers_the_roles_in_user_service(
    client: _TestClient,
) -> None:
    await login(client, "admin")
    resp = await client.get("/users?new=1", allow_redirects=False)
    assert resp.status == 200
    text = await resp.text()
    for role in ("admin", "event-admin", "result-admin", "contestant-admin"):
        assert f'<option value="{role}">' in text
    for role in ("user-admin", "race-office", "race-result"):
        assert f'value="{role}"' not in text


# --- 403 and other errors from user-service, as admin -------------------------


@pytest.mark.integration
async def test_users_page_shows_forbidden_from_user_service(
    client: _TestClient,
) -> None:
    await login(client, "admin")
    with mock_user_service() as mocked:
        mocked.get(USERS_URL, status=403)
        resp = await client.get("/users", allow_redirects=False)
        assert resp.status == 200
        assert NO_ACCESS_READ in await resp.text()


@pytest.mark.integration
async def test_users_page_login_on_401_from_user_service(client: _TestClient) -> None:
    await login(client, "admin")
    with mock_user_service() as mocked:
        mocked.get(USERS_URL, status=401)
        resp = await client.get("/users", allow_redirects=False)
        assert resp.status == 303
        assert location(resp)[0] == "/login"


@pytest.mark.integration
async def test_users_page_error_from_user_service(client: _TestClient) -> None:
    await login(client, "admin")
    with mock_user_service() as mocked:
        mocked.get(USERS_URL, status=500)
        resp = await client.get("/users", allow_redirects=False)
        assert resp.status == 303
        path, query = location(resp)
        assert path == "/"
        assert "Get users failed." in query["informasjon"]


@pytest.mark.integration
@pytest.mark.parametrize(
    ("form", "method", "url", "message"),
    [
        (
            {
                "create": "1",
                "newrole": "admin",
                "newusername": "u",
                "newpassword": "p" * 10,
            },
            "post",
            USERS_URL,
            NO_ACCESS_CREATE,
        ),
        ({"delete": "1", "id": "u1"}, "delete", f"{USERS_URL}/u1", NO_ACCESS_DELETE),
    ],
)
async def test_users_post_shows_forbidden_from_user_service(
    client: _TestClient,
    form: dict,
    method: str,
    url: str,
    message: str,
) -> None:
    await login(client, "admin")
    with mock_user_service() as mocked:
        getattr(mocked, method)(url, status=403)
        resp = await client.post("/users", data=form, allow_redirects=False)
        assert resp.status == 303
        assert location(resp) == ("/users", {"informasjon": message})


# --- UserAdapter ----------------------------------------------------------------


@pytest.mark.integration
async def test_adapter_create_user_forbidden(mocked: aioresponses) -> None:
    mocked.post(USERS_URL, status=403)
    with pytest.raises(web.HTTPForbidden) as e:
        await UserAdapter().create_user("token", "admin", "u", "p")
    assert e.value.reason == NO_ACCESS_CREATE


@pytest.mark.integration
async def test_adapter_delete_user_forbidden(mocked: aioresponses) -> None:
    mocked.delete(f"{USERS_URL}/u1", status=403)
    with pytest.raises(web.HTTPForbidden) as e:
        await UserAdapter().delete_user("token", "u1")
    assert e.value.reason == NO_ACCESS_DELETE


@pytest.mark.integration
async def test_adapter_get_all_users_forbidden(mocked: aioresponses) -> None:
    mocked.get(USERS_URL, status=403)
    with pytest.raises(web.HTTPForbidden) as e:
        await UserAdapter().get_all_users("token")
    assert e.value.reason == NO_ACCESS_READ


@pytest.mark.integration
@pytest.mark.parametrize(
    ("status", "reason"),
    [(401, "401 Unathorized - get_all_users"), (500, "Get users failed.")],
)
async def test_adapter_get_all_users_errors(
    mocked: aioresponses, status: int, reason: str
) -> None:
    """An error is raised instead of returning an empty list."""
    mocked.get(USERS_URL, status=status)
    with pytest.raises(web.HTTPBadRequest) as e:
        await UserAdapter().get_all_users("token")
    assert e.value.reason == reason


@pytest.mark.integration
async def test_adapter_get_all_users(mocked: aioresponses) -> None:
    users = [{"id": "u1", "username": "kari", "role": "admin"}]
    mocked.get(USERS_URL, payload=users)
    assert await UserAdapter().get_all_users("token") == users
