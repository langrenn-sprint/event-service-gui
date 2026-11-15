"""Integration test cases for live updates and health check of the system page (#203)."""

import asyncio
import json

import pytest
from aiohttp import ClientConnectionError
from aiohttp.test_utils import TestClient as _TestClient
from aioresponses import aioresponses

from event_service_gui.adapters import ServiceHealthAdapter
from event_service_gui.adapters.service_health_adapter import HEALTH_CHECKS, HealthCheck
from event_service_gui.services import SystemStatusService

from .test_system_status import (  # noqa: F401 (fixtures)
    NOW,
    instance,
    login,
    service_doc,
    status_doc,
    status_file,
    warning_texts,
)

CHECK = HealthCheck("event-service", "EVENTS", ("/ping", "/ready"))
URL = "http://event-service:8000"


@pytest.fixture
def events_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EVENTS_HOST_SERVER", "event-service")
    monkeypatch.setenv("EVENTS_HOST_PORT", "8000")


def health(
    name: str, status: str = "ok", response_ms: int | None = 12, detail: str = ""
) -> dict:
    return {
        "name": name,
        "status": status,
        "response_ms": response_ms,
        "detail": detail,
    }


# --- Health check adapter -----------------------------------------------------


@pytest.mark.integration
async def test_health_ok(events_host) -> None:
    with aioresponses() as m:
        m.get(f"{URL}/ping", status=200, body="OK")
        m.get(f"{URL}/ready", status=200, body="OK")
        result = await ServiceHealthAdapter(checks=(CHECK,)).check_services()
    assert len(result) == 1
    assert result[0]["name"] == "event-service"
    assert result[0]["status"] == "ok"
    assert result[0]["detail"] == ""
    assert isinstance(result[0]["response_ms"], int)


@pytest.mark.integration
async def test_health_ready_failed(events_host) -> None:
    with aioresponses() as m:
        m.get(f"{URL}/ping", status=200, body="OK")
        m.get(f"{URL}/ready", status=500)
        result = await ServiceHealthAdapter(checks=(CHECK,)).check_services()
    assert result[0]["status"] == "failed"
    assert result[0]["detail"] == "/ready svarte 500"


@pytest.mark.integration
async def test_health_connection_failed(events_host) -> None:
    with aioresponses() as m:
        m.get(f"{URL}/ping", exception=ClientConnectionError("refused"))
        result = await ServiceHealthAdapter(checks=(CHECK,)).check_services()
    assert result[0]["status"] == "failed"
    assert result[0]["detail"].startswith("Får ikke kontakt")


@pytest.mark.integration
async def test_health_timeout(events_host) -> None:
    async def slow(url, **kwargs) -> None:
        await asyncio.sleep(5)

    with aioresponses() as m:
        m.get(f"{URL}/ping", callback=slow)
        result = await ServiceHealthAdapter(
            checks=(CHECK,), timeout=0.1
        ).check_services()
    assert result[0]["status"] == "timeout"
    assert result[0]["response_ms"] is None
    assert result[0]["detail"] == "Ingen svar innen 0.1 s"


@pytest.mark.integration
async def test_health_checks_in_parallel(monkeypatch: pytest.MonkeyPatch) -> None:
    """Two slow services take one timeout, not two."""
    monkeypatch.setenv("EVENTS_HOST_SERVER", "event-service")
    monkeypatch.setenv("EVENTS_HOST_PORT", "8000")
    monkeypatch.setenv("RACE_HOST_SERVER", "race-service")
    monkeypatch.setenv("RACE_HOST_PORT", "8000")
    checks = (CHECK, HealthCheck("race-service", "RACE", ("/ping",)))

    async def slow(url, **kwargs) -> None:
        await asyncio.sleep(5)

    with aioresponses() as m:
        m.get(f"{URL}/ping", callback=slow)
        m.get("http://race-service:8000/ping", callback=slow)
        loop = asyncio.get_running_loop()
        start = loop.time()
        result = await ServiceHealthAdapter(checks=checks, timeout=0.3).check_services()
        elapsed = loop.time() - start
    assert [r["status"] for r in result] == ["timeout", "timeout"]
    assert elapsed < 0.55



@pytest.mark.integration
async def test_health_nothing_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    for check in HEALTH_CHECKS:
        monkeypatch.delenv(f"{check.env_prefix}_HOST_SERVER", raising=False)
    assert await ServiceHealthAdapter().check_services() == []


# --- Health merged into the system info -------------------------------------


@pytest.mark.integration
def test_system_info_health_merged(status_file) -> None:
    status_file(
        status_doc(
            services=[
                service_doc("event-service"),
                service_doc("race-service", state="exited"),
                service_doc("integration-service"),
            ]
        )
    )
    info = SystemStatusService().get_system_info(
        now=NOW,
        health=[
            health("event-service", "timeout", None, "Ingen svar innen 2 s"),
            health(
                "race-service", "failed", 3, "Får ikke kontakt (ClientConnectorError)"
            ),
            health("user-service", "ok", 7),
        ],
    )
    by_name = {s["name"]: s for s in info["services"]}
    assert by_name["event-service"]["health"] == {
        "status": "timeout",
        "status_text": "Tidsavbrudd",
        "ok": False,
        "response_ms": None,
        "text": "Tidsavbrudd",
        "detail": "Ingen svar innen 2 s",
    }
    assert by_name["integration-service"]["health"] is None
    # Checked, but not in the status file
    assert by_name["user-service"]["state"] == "unknown"
    assert by_name["user-service"]["running"] is None
    assert by_name["user-service"]["health"]["text"] == "OK (7 ms)"
    errors = warning_texts(info, "error")
    # Running container that does not answer: that is what the live check is for
    assert "Tjenesten event-service svarer ikke: Ingen svar innen 2 s." in errors
    # Stopped container already has a warning, no extra one
    assert not any("race-service svarer ikke" in t for t in errors)
    assert "Tjenesten race-service kjører ikke (status: exited)." in errors
    assert not any("user-service" in t for t in errors)


@pytest.mark.integration
def test_system_info_health_without_status_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SYSTEM_STATUS_FILE", raising=False)
    info = SystemStatusService().get_system_info(
        now=NOW, health=[health("event-service", "failed", 4, "/ready svarte 500")]
    )
    assert info["has_status"] is False
    assert [s["name"] for s in info["services"]] == ["event-service"]
    assert warning_texts(info) == [
        "Tjenesten event-service svarer ikke: /ready svarte 500."
    ]


# --- JSON endpoint --------------------------------------------------------------


@pytest.mark.integration
async def test_status_endpoint_requires_login(client: _TestClient) -> None:
    resp = await client.get("/system/status", allow_redirects=False)
    assert resp.status == 401
    assert resp.content_type == "application/json"
    assert resp.headers["Cache-Control"] == "no-store"
    assert await resp.json() == {"error": "unauthorized"}


@pytest.mark.integration
async def test_status_endpoint_requires_admin(client: _TestClient) -> None:
    await login(client, "event-admin")
    resp = await client.get("/system/status", allow_redirects=False)
    assert resp.status == 401
    assert await resp.json() == {"error": "unauthorized"}


@pytest.mark.integration
async def test_status_endpoint_admin(
    client: _TestClient, instance, status_file, monkeypatch: pytest.MonkeyPatch
) -> None:
    instance("Laptop reserve", "standby")
    status_file(status_doc())

    async def check_services(self) -> list[dict]:
        return [
            health("event-service", "ok", 5),
            health("user-service", "timeout", None, "Ingen svar innen 2 s"),
        ]

    monkeypatch.setattr(ServiceHealthAdapter, "check_services", check_services)
    await login(client, "admin")
    resp = await client.get("/system/status", allow_redirects=False)
    assert resp.status == 200
    assert resp.content_type == "application/json"
    assert resp.headers["Cache-Control"] == "no-store"
    data = await resp.json()

    # The format the JavaScript relies on
    assert set(data) >= {
        "instance",
        "has_status",
        "warnings",
        "checked_at",
        "generated",
        "backup",
        "restore",
        "mongodb",
        "disk",
        "memory",
        "services",
    }
    assert data["has_status"] is True
    assert data["instance"]["name"] == "Laptop reserve"
    assert len(data["checked_at"]) == 8  # hh:mm:ss
    assert set(data["generated"]) >= {"time", "age", "text", "stale"}
    assert set(data["backup"]["last_success"]) >= {"text", "stale", "file", "size"}
    assert set(data["backup"]) >= {
        "last_attempt_text",
        "failed",
        "last_error",
        "upload",
    }
    assert set(data["backup"]["upload"]) >= {"status_text", "time_text", "failed"}
    assert set(data["disk"]) >= {"free_text", "total", "low"}
    assert data["memory"] == {
        "known": True,
        "total": "32.0 GiB",
        "used_text": "16.0 GiB av 32.0 GiB (50%)",
        "used_percent": "50%",
        "used_warning": False,
        "used_error": False,
        "swap_text": "0 MiB av 8.0 GiB (0%)",
        "swap_percent": "0%",
        "swap_warning": False,
    }
    assert data["mongodb"]["databases"][0]["collections"] == [
        ["contestants", 412],
        ["events", 3],
    ]
    for warning in data["warnings"]:
        assert set(warning) == {"level", "text"}
    by_name = {s["name"]: s for s in data["services"]}
    service = by_name["event-service"]
    assert set(service) >= {
        "name",
        "state_text",
        "running",
        "image",
        "image_created",
        "started_at",
        "version",
        "health",
        "sort",
        "memory_text",
        "memory_share",
        "memory_limit_text",
        "cpu_text",
    }
    assert service["memory_text"] == "523 MiB"
    assert service["memory_share"] == "1.6%"
    assert service["memory_limit_text"] == ""
    assert service["cpu_text"] == "1.4%"
    assert set(service["version"]) == {"text", "url", "title", "is_revision"}
    assert service["health"]["text"] == "OK (5 ms)"
    assert service["health"]["ok"] is True
    assert by_name["user-service"]["health"]["status"] == "timeout"
    assert {
        "level": "error",
        "text": "Tjenesten user-service svarer ikke: Ingen svar innen 2 s.",
    } in data["warnings"]
    json.dumps(data)  # round trip


@pytest.mark.integration
async def test_status_endpoint_same_as_page(
    client: _TestClient, status_file, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The page shows the live health and loads the polling script."""
    status_file(status_doc())

    async def check_services(self) -> list[dict]:
        return [health("event-service", "failed", 3, "/ready svarte 500")]

    monkeypatch.setattr(ServiceHealthAdapter, "check_services", check_services)
    await login(client, "admin")
    resp = await client.get("/system", allow_redirects=False)
    assert resp.status == 200
    text = await resp.text()
    assert "Tjenesten event-service svarer ikke: /ready svarte 500." in text
    assert 'title="/ready svarte 500">Feil (3 ms)</td>' in text
    assert '<script src="/static/system.js?v=' in text
    assert '<noscript><meta http-equiv="refresh" content="60"></noscript>' in text
    assert 'data-status-url="/system/status"' in text
    assert 'id="live-refresh" href="/system"' in text
    # Sortable columns; Versjon is not sortable
    for key in (
        "name",
        "state",
        "health",
        "memory",
        "cpu",
        "image_created",
        "started_at",
    ):
        assert f'data-sort="{key}"' in text
    assert text.count("data-sort=") == 7
    # Explanations for inexperienced users, readable by screen readers
    assert text.count('class="info-tip') >= 15
    assert 'aria-label="Forklaring: Live sjekk hver gang siden oppdateres' in text


@pytest.mark.integration
async def test_status_endpoint_without_status_file(
    client: _TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("SYSTEM_STATUS_FILE", raising=False)
    for check in HEALTH_CHECKS:
        monkeypatch.delenv(f"{check.env_prefix}_HOST_SERVER", raising=False)
    await login(client, "admin")
    resp = await client.get("/system/status")
    assert resp.status == 200
    data = await resp.json()
    assert data["has_status"] is False
    assert data["services"] is None


@pytest.mark.integration
def test_sort_key_health(status_file) -> None:
    """Errors and timeouts first, then the slowest, not checked last."""
    status_file(
        status_doc(
            services=[
                service_doc("a-ok-fast"),
                service_doc("b-ok-slow"),
                service_doc("c-timeout"),
                service_doc("d-failed"),
                service_doc("e-not-checked"),
            ]
        )
    )
    info = SystemStatusService().get_system_info(
        now=NOW,
        health=[
            health("a-ok-fast", "ok", 3),
            health("b-ok-slow", "ok", 900),
            health("c-timeout", "timeout", None, "Ingen svar innen 2 s"),
            health("d-failed", "failed", 5, "/ready svarte 500"),
        ],
    )
    keys = {s["name"]: s["sort"]["health"] for s in info["services"]}
    assert keys == {
        "a-ok-fast": [1, -3],
        "b-ok-slow": [1, -900],
        "c-timeout": [0, 0],
        "d-failed": [0, -5],
        "e-not-checked": [2, 0],
    }
    order = [name for name, _ in sorted(keys.items(), key=lambda kv: kv[1])]
    assert order == ["d-failed", "c-timeout", "b-ok-slow", "a-ok-fast", "e-not-checked"]
