"""Integration test cases for token renewal of active users (#205)."""

import base64
import json
import time
from collections.abc import Iterator
from urllib.parse import parse_qs, urlsplit

import pytest
from aiohttp import ClientConnectionError
from aiohttp.test_utils import TestClient as _TestClient
from aiohttp_session import Session
from aioresponses import aioresponses
from yarl import URL

from event_service_gui.adapters.user_adapter import token_needs_renewal
from event_service_gui.middleware import skip_token_renewal

USER_SERVICE_URL = "http://user-service:8080"
RENEW_URL = f"{USER_SERVICE_URL}/token/renew"
USERS_URL = f"{USER_SERVICE_URL}/users"
LIFETIME = 3600


def make_token(claims: dict) -> str:
    def b64(data: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")

    return f"{b64({'alg': 'HS256', 'typ': 'JWT'})}.{b64(claims)}.signature"


class Clock:
    """Shifts time.time() by `offset` seconds."""

    offset = 0.0


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    real_time = time.time
    clock = Clock()
    monkeypatch.setattr(time, "time", lambda: real_time() + clock.offset)
    return clock


@pytest.fixture
def mocked() -> Iterator[aioresponses]:
    with aioresponses(passthrough=["http://127.0.0.1"]) as m:
        yield m


def token_at(clock_time: float, name: str) -> str:
    """Return a token issued at clock_time, with `name` to tell tokens apart."""
    return make_token(
        {
            "username": "tester",
            "role": "admin",
            "name": name,
            "exp": clock_time + LIFETIME,
        }
    )


async def login(client: _TestClient, mocked: aioresponses, token: str) -> None:
    mocked.post(f"{USER_SERVICE_URL}/login", payload={"token": token})
    resp = await client.post(
        "/login", data={"username": "tester", "password": "pw"}, allow_redirects=False
    )
    assert resp.status == 303


def calls(mocked: aioresponses, method: str, url: str) -> list:
    return mocked.requests.get((method, URL(url)), [])


def bearer(call) -> str:
    return dict(call.kwargs["headers"])["Authorization"]


async def get_users_page(client: _TestClient, mocked: aioresponses):
    mocked.get(USERS_URL, payload=[])
    return await client.get("/users", allow_redirects=False)


# --- When to renew ------------------------------------------------------------


@pytest.mark.integration
def test_token_needs_renewal() -> None:
    now = time.time()

    def session(data: dict) -> Session:
        return Session(None, data={"session": data}, new=False)

    token = make_token({"exp": now + LIFETIME})
    assert not token_needs_renewal(session({"token": token, "token_received_at": now}))
    halfway = now - LIFETIME / 2
    token = make_token({"exp": halfway + LIFETIME})
    assert token_needs_renewal(session({"token": token, "token_received_at": halfway}))
    # session from before token_received_at was stored: renew once
    assert token_needs_renewal(session({"token": token}))
    # no exp: nothing to renew
    no_exp = make_token({"username": "a"})
    assert not token_needs_renewal(session({"token": no_exp, "token_received_at": 0}))


@pytest.mark.integration
@pytest.mark.parametrize(
    ("path", "skip"),
    [
        ("/ping", True),
        ("/ready", True),
        ("/login", True),
        ("/logout", True),
        ("/static/styles.css", True),
        ("/", False),
        ("/users", False),
        ("/control", False),
        ("/loginx", False),
    ],
)
def test_skip_token_renewal(path: str, skip: bool) -> None:
    assert skip_token_renewal(path) is skip


# --- Middleware -----------------------------------------------------------------


@pytest.mark.integration
async def test_no_renewal_before_half_lifetime(
    client: _TestClient, mocked: aioresponses, clock: Clock
) -> None:
    old = token_at(time.time(), "old")
    await login(client, mocked, old)
    clock.offset = LIFETIME / 2 - 60
    resp = await get_users_page(client, mocked)
    assert resp.status == 200
    assert calls(mocked, "POST", RENEW_URL) == []
    assert bearer(calls(mocked, "GET", USERS_URL)[-1]) == f"Bearer {old}"


@pytest.mark.integration
async def test_renewal_after_half_lifetime(
    client: _TestClient, mocked: aioresponses, clock: Clock
) -> None:
    old = token_at(time.time(), "old")
    await login(client, mocked, old)
    clock.offset = LIFETIME / 2 + 60
    new = token_at(time.time(), "new")
    mocked.post(RENEW_URL, payload={"token": new})

    resp = await get_users_page(client, mocked)
    assert resp.status == 200
    renew_calls = calls(mocked, "POST", RENEW_URL)
    assert len(renew_calls) == 1
    assert bearer(renew_calls[0]) == f"Bearer {old}"
    # the page already uses the new token
    assert bearer(calls(mocked, "GET", USERS_URL)[-1]) == f"Bearer {new}"

    # the new token is kept in the session, and is not renewed again yet
    resp = await get_users_page(client, mocked)
    assert resp.status == 200
    assert len(calls(mocked, "POST", RENEW_URL)) == 1
    assert bearer(calls(mocked, "GET", USERS_URL)[-1]) == f"Bearer {new}"

    # an active user stays logged in after the first token has expired
    clock.offset = LIFETIME + 600
    resp = await get_users_page(client, mocked)
    assert resp.status == 200
    assert bearer(calls(mocked, "GET", USERS_URL)[-1]) == f"Bearer {new}"


@pytest.mark.integration
async def test_renewal_refused_logs_out(
    client: _TestClient, mocked: aioresponses, clock: Clock
) -> None:
    await login(client, mocked, token_at(time.time(), "old"))
    clock.offset = LIFETIME / 2 + 60
    mocked.post(RENEW_URL, status=401)

    resp = await client.get("/users?new=1", allow_redirects=False)
    assert resp.status == 303
    location = resp.headers["Location"]
    assert location.startswith("/login?")
    assert parse_qs(urlsplit(location).query)["next"] == ["/users?new=1"]

    # logged out: the next request goes to login without trying to renew
    resp = await client.get("/users", allow_redirects=False)
    assert resp.status == 303
    assert resp.headers["Location"].startswith("/login?")
    assert len(calls(mocked, "POST", RENEW_URL)) == 1


@pytest.mark.integration
@pytest.mark.parametrize(
    "renew_response",
    [
        {"status": 500},
        {"status": 503},
        {"exception": ClientConnectionError("down")},
        {"status": 200, "payload": {"no": "token"}},
    ],
)
async def test_renewal_error_keeps_token(
    client: _TestClient, mocked: aioresponses, clock: Clock, renew_response: dict
) -> None:
    old = token_at(time.time(), "old")
    await login(client, mocked, old)
    clock.offset = LIFETIME / 2 + 60
    mocked.post(RENEW_URL, **renew_response)

    resp = await get_users_page(client, mocked)
    assert resp.status == 200
    assert bearer(calls(mocked, "GET", USERS_URL)[-1]) == f"Bearer {old}"
    assert len(calls(mocked, "POST", RENEW_URL)) == 1


@pytest.mark.integration
async def test_expired_token_is_not_renewed(
    client: _TestClient, mocked: aioresponses, clock: Clock
) -> None:
    """A session without activity still expires with the token."""
    await login(client, mocked, token_at(time.time(), "old"))
    clock.offset = LIFETIME + 1
    resp = await client.get("/users", allow_redirects=False)
    assert resp.status == 303
    assert resp.headers["Location"].startswith("/login?")
    assert calls(mocked, "POST", RENEW_URL) == []


@pytest.mark.integration
@pytest.mark.parametrize("path", ["/ping", "/login", "/static/styles.css"])
async def test_skipped_paths_do_not_renew(
    client: _TestClient, mocked: aioresponses, clock: Clock, path: str
) -> None:
    await login(client, mocked, token_at(time.time(), "old"))
    clock.offset = LIFETIME / 2 + 60
    resp = await client.get(path, allow_redirects=False)
    assert resp.status == 200
    assert calls(mocked, "POST", RENEW_URL) == []


@pytest.mark.integration
async def test_not_logged_in_does_not_renew(
    client: _TestClient, mocked: aioresponses
) -> None:
    resp = await client.get("/", allow_redirects=False)
    assert resp.status in (200, 303)
    assert calls(mocked, "POST", RENEW_URL) == []
