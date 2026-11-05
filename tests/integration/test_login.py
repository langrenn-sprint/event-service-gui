"""Integration test cases for login, token expiry and session cookie (#205)."""

import base64
import json
import time
from urllib.parse import parse_qs, urlsplit

import pytest
from aiohttp import ClientResponse
from aiohttp.test_utils import TestClient as _TestClient
from aiohttp_session import Session
from aioresponses import aioresponses

from event_service_gui import create_app
from event_service_gui.adapters import UserAdapter
from event_service_gui.views.utils import login_location, safe_next_path

USER_SERVICE_URL = "http://user-service:8080"


def make_token(claims: dict) -> str:
    def b64(data: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")

    return f"{b64({'alg': 'HS256', 'typ': 'JWT'})}.{b64(claims)}.signature"


def valid_token(**claims) -> str:
    return make_token({"username": "tester", "exp": time.time() + 3600, **claims})


async def login(
    client: _TestClient, token: str, next_path: str | None = None
) -> ClientResponse:
    data = {"username": "tester", "password": "pw"}
    if next_path is not None:
        data["next"] = next_path
    with aioresponses(passthrough=["http://127.0.0.1"]) as m:
        m.post(f"{USER_SERVICE_URL}/login", payload={"token": token})
        return await client.post("/login", data=data, allow_redirects=False)


def query_of(location: str) -> dict:
    return {k: v[0] for k, v in parse_qs(urlsplit(location).query).items()}


# --- isloggedin -------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.parametrize(
    ("session", "expected"),
    [
        ({"loggedin": True, "token": valid_token()}, True),
        ({"loggedin": True, "token": make_token({"exp": time.time() - 1})}, False),
        # expires within the margin: counts as expired
        ({"loggedin": True, "token": make_token({"exp": time.time() + 5})}, False),
        ({"loggedin": True, "token": make_token({"username": "a"})}, False),
        ({"loggedin": True, "token": make_token({"exp": "soon"})}, False),
        ({"loggedin": True, "token": "not-a-token"}, False),
        ({"loggedin": True}, False),
        ({"loggedin": False, "token": valid_token()}, False),
        ({}, False),
    ],
)
def test_isloggedin(session: dict, expected: bool) -> None:
    cookiestorage = Session(None, data={"session": session}, new=False)
    assert UserAdapter().isloggedin(cookiestorage) is expected


# --- next validation --------------------------------------------------------


@pytest.mark.integration
@pytest.mark.parametrize(
    "value",
    ["/", "/control?event_id=1&action=x", "/raceplans?event_id=1", "/users"],
)
def test_safe_next_path_accepts_relative_paths(value: str) -> None:
    assert safe_next_path(value) == value


@pytest.mark.integration
@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "http://evil.example/",
        "https://evil.example/control",
        "//evil.example/",
        "///evil.example/",
        "/\\evil.example/",
        "\\\\evil.example/",
        "/\t/evil.example/",
        "/\n/evil.example/",
        "javascript:alert(1)",
        "evil.example/",
        "control",
        "/login",
        "/login?next=/control",
        "/logout",
    ],
)
def test_safe_next_path_rejects(value: str | None) -> None:
    assert safe_next_path(value) is None


@pytest.mark.integration
def test_login_location() -> None:
    location = login_location("Logg inn", "/control?event_id=1&heat=2")
    assert location.startswith("/login?")
    assert query_of(location) == {
        "informasjon": "Logg inn",
        "next": "/control?event_id=1&heat=2",
    }
    assert "next" not in query_of(login_location("Logg inn", "//evil.example/"))
    assert "next" not in query_of(login_location("Logg inn"))


# --- Login page and redirects -------------------------------------------------


@pytest.mark.integration
async def test_page_requires_login_with_next(client: _TestClient) -> None:
    resp = await client.get("/users", allow_redirects=False)
    assert resp.status == 303
    location = resp.headers["Location"]
    assert location.startswith("/login?")
    assert query_of(location)["next"] == "/users"


@pytest.mark.integration
async def test_expired_token_gives_login_before_form(client: _TestClient) -> None:
    """A form page with an expired token goes to login, not to the form."""
    resp = await login(client, make_token({"username": "t", "exp": time.time() + 5}))
    assert resp.status == 303
    resp = await client.get("/control?event_id=1&action=x", allow_redirects=False)
    assert resp.status == 303
    location = resp.headers["Location"]
    assert location.startswith("/login?")
    assert query_of(location)["next"] == "/control?event_id=1&action=x"


@pytest.mark.integration
async def test_login_page_keeps_next(client: _TestClient) -> None:
    resp = await client.get("/login", params={"next": "/control?event_id=1"})
    assert resp.status == 200
    text = await resp.text()
    assert 'name="next" value="/control?event_id=1"' in text


@pytest.mark.integration
async def test_login_page_drops_unsafe_next(client: _TestClient) -> None:
    resp = await client.get("/login", params={"next": '//evil.example/"><script>'})
    assert resp.status == 200
    text = await resp.text()
    assert 'name="next" value=""' in text
    assert "evil.example" not in text


@pytest.mark.integration
async def test_login_redirects_to_next(client: _TestClient) -> None:
    resp = await login(client, valid_token(), "/control?event_id=1")
    assert resp.status == 303
    assert resp.headers["Location"] == "/control?event_id=1"


@pytest.mark.integration
@pytest.mark.parametrize(
    "next_path", ["", "//evil.example/", "https://evil.example/", "/logout"]
)
async def test_login_ignores_unsafe_next(client: _TestClient, next_path: str) -> None:
    resp = await login(client, valid_token(), next_path)
    assert resp.status == 303
    assert resp.headers["Location"].startswith("/?informasjon=")


@pytest.mark.integration
async def test_logged_in_user_gets_page(client: _TestClient) -> None:
    """A valid token is not sent to login (the page itself may redirect)."""
    await login(client, valid_token())
    with aioresponses(passthrough=["http://127.0.0.1"]) as m:
        m.get(f"{USER_SERVICE_URL}/users", payload=[])
        resp = await client.get("/users", allow_redirects=False)
    assert resp.status == 200


# --- Session cookie -----------------------------------------------------------


@pytest.mark.integration
async def test_session_cookie_settings(client: _TestClient) -> None:
    resp = await login(client, valid_token())
    cookie = resp.headers["Set-Cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie
    assert "Max-Age=86400" in cookie
    assert "Secure" not in cookie


@pytest.mark.integration
async def test_session_cookie_secure(
    aiohttp_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "true")
    monkeypatch.setenv("JWT_MAX_SESSION_SECONDS", "3600")
    client = await aiohttp_client(await create_app())
    resp = await login(client, valid_token())
    cookie = resp.headers["Set-Cookie"]
    assert "Secure" in cookie
    assert "Max-Age=3600" in cookie


# --- FERNET_KEY -----------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.parametrize(
    "fernet_key",
    [
        None,
        "",
        "   ",
        "not-base64!",
        base64.urlsafe_b64encode(b"too short").decode(),
        base64.urlsafe_b64encode(b"x" * 33).decode(),
    ],
)
async def test_app_requires_valid_fernet_key(
    monkeypatch: pytest.MonkeyPatch, fernet_key: str | None
) -> None:
    if fernet_key is None:
        monkeypatch.delenv("FERNET_KEY", raising=False)
    else:
        monkeypatch.setenv("FERNET_KEY", fernet_key)
    with pytest.raises(RuntimeError, match="FERNET_KEY"):
        await create_app()


@pytest.mark.integration
async def test_fernet_key_not_in_error(monkeypatch: pytest.MonkeyPatch) -> None:
    key = base64.urlsafe_b64encode(b"x" * 31).decode()
    monkeypatch.setenv("FERNET_KEY", key)
    with pytest.raises(RuntimeError) as excinfo:
        await create_app()
    assert key not in str(excinfo.value)


@pytest.mark.integration
async def test_app_starts_with_valid_fernet_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FERNET_KEY", base64.urlsafe_b64encode(b"k" * 32).decode())
    assert await create_app() is not None
