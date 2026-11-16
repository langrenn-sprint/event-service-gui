"""Integration test cases for access to settings and video events (#237).

Only admin may save settings in photo-service. Other users see the settings
read-only, cannot start or stop the integration, and get a clear message
instead of "update_config failed - 403 - Operation forbidden".

user-service is replaced by a fake login, and photo-service by the fake from
test_config_adapter.py.
"""

import base64
import json
import time

import pytest
from aiohttp import ClientResponse, web
from aiohttp.test_utils import TestClient as _TestClient
from aiohttp_session import Session
from yarl import URL

from event_service_gui.adapters import ConfigAdapter, UserAdapter
from event_service_gui.adapters.config_adapter import (
    NO_ACCESS_CONFIG,
    default_settings,
)
from event_service_gui.adapters.user_adapter import get_role_from_token, store_token

from .test_config_adapter import EVENT_ID, FakePhotoService, photo_service

__all__ = ["photo_service"]  # the fixture is used by the tests below

EVENT = {
    "id": EVENT_ID,
    "name": "Test",
    "competition_format": "Individual Sprint",
    "date_of_event": "2026-11-06",
    "time_of_event": "12:00:00",
    "timezone": "Europe/Oslo",
    "organiser": "Lyn Ski",
    "webpage": "https://example.com",
    "information": "",
}
OTHER_ROLES = ["event-admin", "result-admin", "contestant-admin", ""]


def make_token(claims: dict) -> str:
    def b64(data: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")

    return f"{b64({'alg': 'HS256', 'typ': 'JWT'})}.{b64(claims)}.signature"


@pytest.fixture
def fakes(monkeypatch: pytest.MonkeyPatch, photo_service: FakePhotoService):
    """Fake login, event and integration status; returns the fake photo-service."""

    async def fake_login(self, username: str, password: str, cookiestorage) -> int:
        claims = {"username": username, "exp": time.time() + 3600}
        if password:
            claims["role"] = password  # the tests log in with the role as password
        store_token(cookiestorage, make_token(claims))
        cookiestorage["name"] = username
        cookiestorage["loggedin"] = True
        return 200

    async def fake_get_event(user: dict, event_id: str) -> dict:
        return EVENT

    async def fake_status(token: str, event_id: str) -> str:
        return "integration status"

    monkeypatch.setattr(UserAdapter, "login", fake_login)
    monkeypatch.setattr("event_service_gui.views.config.get_event", fake_get_event)
    monkeypatch.setattr(
        "event_service_gui.views.video_events.get_integration_status", fake_status
    )
    photo_service.settings[(EVENT_ID, "VIDEO_STORAGE_MODE")] = "old value"
    return photo_service


async def login(client: _TestClient, role: str) -> None:
    resp = await client.post(
        "/login", data={"username": "tester", "password": role}, allow_redirects=False
    )
    assert resp.status == 303


def informasjon(resp) -> str:
    return URL(resp.headers["Location"]).query.get("informasjon", "")


async def save_setting(client: _TestClient) -> ClientResponse:
    data = {
        "event_id": EVENT_ID,
        "update_one": "Oppdater",
        "key": "VIDEO_STORAGE_MODE",
        "value": "new value",
    }
    return await client.post("/config", data=data, allow_redirects=False)


async def toggle_integration(client: _TestClient, command: str) -> dict:
    data = {"event_id": EVENT_ID, "action": "toggle", command: "true"}
    resp = await client.post("/video_events", data=data)
    assert resp.status == 200
    return json.loads(await resp.text())


# --- Role in the session ----------------------------------------------------------


@pytest.mark.integration
def test_store_token_stores_the_role() -> None:
    session = Session(None, data={"session": {}}, new=True)
    store_token(session, make_token({"username": "a", "role": "result-admin"}))
    assert session["role"] == "result-admin"
    store_token(session, make_token({"username": "a"}))
    assert session["role"] == ""
    assert get_role_from_token("not-a-token") == ""
    assert get_role_from_token(make_token({"role": 42})) == ""


# --- The settings page --------------------------------------------------------------


@pytest.mark.integration
async def test_settings_page_editable_for_admin(client: _TestClient, fakes) -> None:
    await login(client, "admin")
    resp = await client.get(f"/config?event_id={EVENT_ID}&action=edit")
    text = await resp.text()
    assert "action=edit class=dropbtn>Rediger</a>" in text
    assert "name=update_one" in text


@pytest.mark.integration
@pytest.mark.parametrize("role", OTHER_ROLES)
async def test_settings_page_read_only_for_other_roles(
    client: _TestClient, fakes, role: str
) -> None:
    await login(client, role)
    resp = await client.get(f"/config?event_id={EVENT_ID}&action=edit")
    text = await resp.text()
    assert "old value" in text
    assert "Rediger</a>" not in text
    assert "name=update_one" not in text


@pytest.mark.integration
async def test_admin_saves_a_setting(client: _TestClient, fakes) -> None:
    await login(client, "admin")
    resp = await save_setting(client)
    assert resp.status == 303
    assert informasjon(resp) == "Suksess. Informasjon er oppdatert."
    assert fakes.settings[(EVENT_ID, "VIDEO_STORAGE_MODE")] == "new value"


@pytest.mark.integration
@pytest.mark.parametrize("role", OTHER_ROLES)
async def test_other_roles_cannot_save_a_setting(
    client: _TestClient, fakes, role: str
) -> None:
    """The save is refused with a clear message, and nothing is sent."""
    await login(client, role)
    resp = await save_setting(client)
    assert resp.status == 303
    assert informasjon(resp) == NO_ACCESS_CONFIG
    assert fakes.writes == []
    assert fakes.settings[(EVENT_ID, "VIDEO_STORAGE_MODE")] == "old value"


@pytest.mark.integration
async def test_forbidden_from_photo_service_gives_clear_message(
    client: _TestClient, fakes
) -> None:
    """E.g. the user's role was changed after login."""
    await login(client, "admin")
    fakes.forbidden = True
    resp = await save_setting(client)
    assert informasjon(resp) == NO_ACCESS_CONFIG


# --- Video events ---------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.parametrize("command", ["integration_start", "integration_stop"])
async def test_admin_starts_and_stops_the_integration(
    client: _TestClient, fakes, command: str
) -> None:
    await login(client, "admin")
    response = await toggle_integration(client, command)
    assert response["informasjon"] == "integration status"
    keys = {body["key"] for _, body in fakes.writes}
    assert "INTEGRATION_SERVICE_START" in keys


@pytest.mark.integration
@pytest.mark.parametrize("role", OTHER_ROLES)
@pytest.mark.parametrize("command", ["integration_start", "integration_stop"])
async def test_other_roles_cannot_start_or_stop_the_integration(
    client: _TestClient, fakes, role: str, command: str
) -> None:
    """Refused with a clear message, nothing is sent, the status is still read."""
    await login(client, role)
    response = await toggle_integration(client, command)
    assert response["informasjon"] == NO_ACCESS_CONFIG
    assert "photo_queue_latest" in response
    assert fakes.writes == []


@pytest.mark.integration
async def test_video_events_status_is_open_to_all(client: _TestClient, fakes) -> None:
    await login(client, "result-admin")
    data = {"event_id": EVENT_ID, "action": "status"}
    response = json.loads(await (await client.post("/video_events", data=data)).text())
    assert response["informasjon"] == "integration status"


@pytest.mark.integration
async def test_video_events_forbidden_from_photo_service(
    client: _TestClient, fakes
) -> None:
    await login(client, "admin")
    fakes.forbidden = True
    response = await toggle_integration(client, "integration_start")
    assert response["informasjon"] == NO_ACCESS_CONFIG


# --- ConfigAdapter ----------------------------------------------------------------------


@pytest.mark.integration
async def test_adapter_update_forbidden(fakes) -> None:
    fakes.forbidden = True
    with pytest.raises(web.HTTPForbidden) as e:
        await ConfigAdapter().update_config("t", EVENT_ID, "VIDEO_STORAGE_MODE", "x")
    assert e.value.reason == NO_ACCESS_CONFIG


@pytest.mark.integration
async def test_adapter_create_forbidden(fakes) -> None:
    """A setting that is not saved yet is created, which is also forbidden."""
    fakes.forbidden = True
    fakes.settings.clear()
    with pytest.raises(web.HTTPForbidden) as e:
        await ConfigAdapter().update_config("t", EVENT_ID, "VIDEO_STORAGE_MODE", "x")
    assert e.value.reason == NO_ACCESS_CONFIG


# --- All settings on the settings page (follow-up to #236) --------------------------


@pytest.mark.integration
async def test_settings_page_shows_all_settings(client: _TestClient, fakes) -> None:
    """A new event shows every setting, with the default, so admin can edit it."""
    fakes.settings.clear()
    fakes.settings[(EVENT_ID, "VIDEO_STORAGE_MODE")] = "saved value"
    fakes.settings[(EVENT_ID, "NOT_IN_DEFAULTS")] = "extra"
    await login(client, "admin")
    resp = await client.get(f"/config?event_id={EVENT_ID}&action=edit")
    text = await resp.text()
    defaults = default_settings()
    for key in defaults:
        assert f'name="key" value="{key}"' in text
    assert 'name="key" value="NOT_IN_DEFAULTS"' in text
    assert text.count("name=update_one") == len(defaults) + 1
    # Defaults are marked, saved values are not:
    assert text.count(">(standard)</i>") == len(defaults) - 1
    assert 'value="saved value"' in text


@pytest.mark.integration
async def test_admin_saves_a_setting_that_is_not_saved_yet(
    client: _TestClient, fakes
) -> None:
    fakes.settings.clear()
    await login(client, "admin")
    resp = await save_setting(client)
    assert informasjon(resp) == "Suksess. Informasjon er oppdatert."
    assert fakes.settings == {(EVENT_ID, "VIDEO_STORAGE_MODE"): "new value"}
    text = await (await client.get(f"/config?event_id={EVENT_ID}")).text()
    assert text.count(">(standard)</i>") == len(default_settings()) - 1
