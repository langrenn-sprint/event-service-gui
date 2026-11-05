"""Integration test cases for instance banner and system page (#198)."""

import base64
import datetime
import json
from pathlib import Path

import pytest
from aiohttp.test_utils import TestClient as _TestClient
from aioresponses import aioresponses

from event_service_gui.adapters import SystemStatusAdapter
from event_service_gui.adapters.user_adapter import get_role_from_token
from event_service_gui.services import SystemStatusService

NOW = datetime.datetime(2026, 11, 5, 11, 5, 0, tzinfo=datetime.UTC)
USER_SERVICE_URL = "http://user-service:8080"


def status_doc(**overrides) -> dict:
    """Return a valid status document as in langrenn-sprint/deploy#13."""
    doc = {
        "schema_version": 1,
        "generated_at": "2026-11-05T12:00:01+01:00",
        "instance": {"name": "Laptop reserve", "role": "standby"},
        "backup": {
            "last_attempt": "2026-11-05T12:00:01+01:00",
            "last_result": "ok",
            "last_error": None,
            "last_success": {
                "time": "2026-11-05T12:00:01+01:00",
                "file": "mongo_20261105_120001.archive.gz",
                "size_bytes": 425984,
                "duration_seconds": 0,
            },
            "upload": {"status": "ok", "time": "2026-11-05T12:00:03+01:00"},
        },
        "restore": {
            "archive": "mongo_20261104_181500.archive.gz",
            "archive_sha256": "abc",
            "archive_time": "2026-11-04T18:15:00+01:00",
            "restored_at": "2026-11-05T09:12:44+01:00",
            "restored_on": "Laptop reserve",
        },
        "mongodb": {
            "available": True,
            "version": "7.0.14",
            "databases": [
                {
                    "name": "events",
                    "size_bytes": 1234567,
                    "collections": {"events": 3, "contestants": 412},
                }
            ],
        },
        "disk": {"total_bytes": 26843545600, "free_bytes": 12884901888},
        "services": [
            service_doc("user-service"),
            service_doc("event-service"),
        ],
    }
    doc.update(overrides)
    return doc


def service_doc(name: str, **overrides) -> dict:
    """Return a running service as in the `services` section of system.json."""
    doc = {
        "name": name,
        "state": "running",
        "started_at": "2026-11-05T09:12:50+01:00",
        "image": f"ghcr.io/langrenn-sprint/{name}:latest",
        "image_id": "sha256:1111",
        "image_digest": "sha256:2222",
        "image_created": "2026-11-04T21:03:11+01:00",
        "revision": "4e183fd0c2b1a9e8d7f6a5b4c3d2e1f0a9b8c7d6",
        "source": f"https://github.com/langrenn-sprint/{name}",
    }
    doc.update(overrides)
    return doc


@pytest.fixture
def status_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Point SYSTEM_STATUS_FILE to a temp file; returns a writer function."""
    path = tmp_path / "system.json"
    monkeypatch.setenv("SYSTEM_STATUS_FILE", str(path))

    def write(content) -> Path:
        path.write_text(content if isinstance(content, str) else json.dumps(content))
        return path

    return write


@pytest.fixture
def instance(monkeypatch: pytest.MonkeyPatch):
    """Set INSTANCE_NAME / INSTANCE_ROLE; None removes the variable."""

    def set_instance(name: str | None, role: str | None) -> None:
        for key, value in (("INSTANCE_NAME", name), ("INSTANCE_ROLE", role)):
            if value is None:
                monkeypatch.delenv(key, raising=False)
            else:
                monkeypatch.setenv(key, value)

    return set_instance


def warning_texts(info: dict, level: str | None = None) -> list[str]:
    return [w["text"] for w in info["warnings"] if level is None or w["level"] == level]


# --- Parsing of the status file -------------------------------------------


@pytest.mark.integration
def test_status_file_valid(status_file) -> None:
    status_file(status_doc())
    status = SystemStatusAdapter().get_status()
    assert status is not None
    assert status["schema_version"] == 1


@pytest.mark.integration
def test_status_file_env_not_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SYSTEM_STATUS_FILE", raising=False)
    assert SystemStatusAdapter().get_status() is None


@pytest.mark.integration
def test_status_file_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SYSTEM_STATUS_FILE", str(tmp_path / "nope.json"))
    assert SystemStatusAdapter().get_status() is None


@pytest.mark.integration
@pytest.mark.parametrize("content", ["", "{not json", "[1, 2]", '"text"'])
def test_status_file_invalid(status_file, content: str) -> None:
    status_file(content)
    assert SystemStatusAdapter().get_status() is None


@pytest.mark.integration
def test_system_info_no_status(monkeypatch: pytest.MonkeyPatch, instance) -> None:
    monkeypatch.delenv("SYSTEM_STATUS_FILE", raising=False)
    instance("Laptop reserve", "standby")
    info = SystemStatusService().get_system_info(now=NOW)
    assert info["has_status"] is False
    assert info["instance"]["name"] == "Laptop reserve"
    assert info["instance"]["role"] == "standby"


@pytest.mark.integration
def test_system_info_all_ok(status_file, instance) -> None:
    instance("Laptop reserve", "standby")
    status_file(status_doc())
    info = SystemStatusService().get_system_info(now=NOW)
    assert info["has_status"] is True
    assert info["warnings"] == []
    assert info["generated"]["time"] == "05.11.2026 12:00:01"
    assert info["generated"]["age"] == "4 min"
    assert info["backup"]["last_success"]["size"] == "416.0 kB"
    assert info["backup"]["upload"]["status"] == "ok"
    assert info["restore"]["archive"] == "mongo_20261104_181500.archive.gz"
    assert info["restore"]["archive_time"] == "04.11.2026 18:15:00"
    assert info["mongodb"]["available"] is True
    assert info["mongodb"]["databases"][0]["collections"] == [
        ("contestants", 412),
        ("events", 3),
    ]
    assert info["disk"]["free_percent"] == "48%"
    assert info["disk"]["low"] is False
    assert [s["name"] for s in info["services"]] == ["event-service", "user-service"]
    service = info["services"][1]
    assert service["running"] is True
    assert service["state_text"] == "Kjører"
    assert service["revision"] == "4e183fd"
    assert service["revision_url"] == (
        "https://github.com/langrenn-sprint/user-service/commit/"
        "4e183fd0c2b1a9e8d7f6a5b4c3d2e1f0a9b8c7d6"
    )
    assert service["image_created"] == "04.11.2026 21:03:11"
    assert service["started_at"] == "05.11.2026 09:12:50"


@pytest.mark.integration
def test_system_info_never_restored(status_file) -> None:
    status_file(status_doc(restore=None))
    info = SystemStatusService().get_system_info(now=NOW)
    assert info["restore"] is None


@pytest.mark.integration
def test_system_info_stale_backup_and_status(status_file) -> None:
    status_file(status_doc())
    later = NOW + datetime.timedelta(minutes=20)
    info = SystemStatusService().get_system_info(now=later)
    errors = warning_texts(info, "error")
    assert any("Statusfila er ikke oppdatert" in t for t in errors)
    assert any("Siste vellykkede backup er 24 min gammel" in t for t in errors)
    assert info["generated"]["stale"] is True
    assert info["backup"]["last_success"]["stale"] is True


@pytest.mark.integration
def test_system_info_failed_backup_upload_mongodb_disk(status_file) -> None:
    doc = status_doc(
        mongodb={"available": False},
        disk={"total_bytes": 100, "free_bytes": 8},
    )
    doc["backup"]["last_result"] = "failed"
    doc["backup"]["last_error"] = "mongodump exited with 1"
    doc["backup"]["upload"]["status"] = "failed"
    status_file(doc)
    info = SystemStatusService().get_system_info(now=NOW)
    errors = warning_texts(info, "error")
    warnings = warning_texts(info, "warning")
    assert "Siste backup feilet: mongodump exited with 1" in errors
    assert "Databasen (MongoDB) svarer ikke." in errors
    assert "Siste opplasting av backup til sky feilet." in warnings
    assert any("Lite ledig diskplass: 8%" in t for t in warnings)
    assert info["mongodb"]["databases"] == []
    assert info["disk"]["low"] is True


@pytest.mark.integration
def test_system_info_very_low_disk_is_error(status_file) -> None:
    status_file(status_doc(disk={"total_bytes": 100, "free_bytes": 2}))
    info = SystemStatusService().get_system_info(now=NOW)
    assert any("Lite ledig diskplass" in t for t in warning_texts(info, "error"))


@pytest.mark.integration
def test_system_info_partial_document(status_file) -> None:
    """Missing or wrongly typed fields must not raise."""
    status_file({"schema_version": 2, "backup": "x", "mongodb": None, "disk": []})
    info = SystemStatusService().get_system_info(now=NOW)
    assert info["has_status"] is True
    texts = warning_texts(info)
    assert any("Ukjent versjon av statusfila" in t for t in texts)
    assert "Statusfila mangler tidspunkt." in texts
    assert "Ingen vellykket backup er registrert." in texts
    assert info["restore"] is None
    assert info["services"] is None


@pytest.mark.integration
def test_system_info_services_not_running(status_file) -> None:
    status_file(
        status_doc(
            services=[
                service_doc("user-service"),
                service_doc("integration-service", state="exited"),
                service_doc("photo-service", state="restarting"),
                {"name": "race-service", "state": "missing"},
            ]
        )
    )
    info = SystemStatusService().get_system_info(now=NOW)
    errors = warning_texts(info, "error")
    assert "Tjenesten integration-service kjører ikke (status: exited)." in errors
    assert "Tjenesten photo-service kjører ikke (status: restarting)." in errors
    assert "Tjenesten race-service mangler (ingen container)." in errors
    assert not any("user-service" in t for t in errors)
    by_name = {s["name"]: s for s in info["services"]}
    assert by_name["integration-service"]["state_text"] == "Stoppet"
    assert by_name["integration-service"]["running"] is False
    missing = by_name["race-service"]
    assert missing["state_text"] == "Mangler"
    assert missing["revision"] == ""
    assert missing["started_at"] == ""


@pytest.mark.integration
def test_system_info_services_revision_link_only_for_github(status_file) -> None:
    status_file(
        status_doc(
            services=[
                service_doc("no-labels", revision=None, source=None),
                service_doc("other-host", source="https://example.com/a/b"),
                service_doc("bad-revision", revision="main"),
                service_doc("injection", source='https://github.com/a/b"><script>'),
            ]
        )
    )
    info = SystemStatusService().get_system_info(now=NOW)
    by_name = {s["name"]: s for s in info["services"]}
    assert all(s["revision_url"] == "" for s in info["services"])
    assert by_name["no-labels"]["revision"] == ""
    assert by_name["other-host"]["revision"] == "4e183fd"
    assert by_name["bad-revision"]["revision"] == "main"


@pytest.mark.integration
@pytest.mark.parametrize(
    ("image", "tag"),
    [
        ("mongo:7-jammy", "7-jammy"),
        ("ghcr.io/langrenn-sprint/user-service:latest", "latest"),
        ("registry:5000/mongo", ""),
        ("mongo", ""),
        (None, ""),
    ],
)
def test_system_info_services_image_tag(status_file, image, tag: str) -> None:
    """Images without OCI labels (e.g. mongo) show the image tag instead."""
    status_file(
        status_doc(
            services=[service_doc("db", image=image, revision=None, source=None)]
        )
    )
    info = SystemStatusService().get_system_info(now=NOW)
    assert info["services"][0]["image_tag"] == tag


@pytest.mark.integration
def test_system_info_services_wrong_types(status_file) -> None:
    """Wrongly typed entries are skipped, not raised on."""
    status_file(status_doc(services=["x", None, {"state": "running", "revision": 1}]))
    info = SystemStatusService().get_system_info(now=NOW)
    assert len(info["services"]) == 1
    assert info["services"][0]["name"] == "(uten navn)"
    assert info["services"][0]["revision"] == ""


# --- Banner logic -----------------------------------------------------------


@pytest.mark.integration
def test_banner_not_in_production(instance, status_file) -> None:
    instance("UpCloud prod", "production")
    status_file(status_doc())
    assert SystemStatusService().get_banner() is None


@pytest.mark.integration
def test_banner_production_case_insensitive(instance) -> None:
    instance("UpCloud prod", " Production ")
    assert SystemStatusService().get_banner() is None


@pytest.mark.integration
def test_banner_standby_with_restore_info(instance, status_file) -> None:
    instance("Laptop reserve", "standby")
    status_file(status_doc())
    banner = SystemStatusService().get_banner()
    assert banner is not None
    assert (
        banner["text"] == "RESERVEINSTANS: Laptop reserve - data fra backup 04.11 18:15"
    )


@pytest.mark.integration
def test_banner_without_status_file(instance, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SYSTEM_STATUS_FILE", raising=False)
    instance("Test-VM", "test")
    banner = SystemStatusService().get_banner()
    assert banner == {"role": "test", "text": "TESTINSTANS: Test-VM"}


@pytest.mark.integration
@pytest.mark.parametrize("role", [None, "", "unknown"])
def test_banner_unknown_role(instance, monkeypatch: pytest.MonkeyPatch, role) -> None:
    monkeypatch.delenv("SYSTEM_STATUS_FILE", raising=False)
    instance(None, role)
    banner = SystemStatusService().get_banner()
    assert banner is not None
    assert banner["role"] == "unknown"
    assert banner["text"].startswith("UKJENT INSTANS")


@pytest.mark.integration
def test_banner_other_role(instance, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SYSTEM_STATUS_FILE", raising=False)
    instance("X", "staging")
    banner = SystemStatusService().get_banner()
    assert banner is not None
    assert banner["text"] == "INSTANS MED ROLLE «staging»: X"


# --- Role from token ----------------------------------------------------------


def make_token(claims: dict) -> str:
    def b64(data: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")

    return f"{b64({'alg': 'HS256', 'typ': 'JWT'})}.{b64(claims)}.signature"


@pytest.mark.integration
def test_get_role_from_token() -> None:
    assert (
        get_role_from_token(make_token({"username": "a", "role": "admin"})) == "admin"
    )
    assert get_role_from_token(make_token({"username": "a"})) == ""
    assert get_role_from_token("not-a-token") == ""
    assert get_role_from_token("a.!!!.c") == ""


# --- Pages --------------------------------------------------------------------


async def login(client: _TestClient, role: str) -> None:
    with aioresponses(passthrough=["http://127.0.0.1"]) as m:
        m.post(
            f"{USER_SERVICE_URL}/login",
            payload={"token": make_token({"username": "tester", "role": role})},
        )
        resp = await client.post(
            "/login",
            data={"username": "tester", "password": "pw"},
            allow_redirects=False,
        )
    assert resp.status == 303


@pytest.mark.integration
async def test_banner_shown_on_page(client: _TestClient, instance, status_file) -> None:
    instance("Laptop reserve", "standby")
    status_file(status_doc())
    resp = await client.get("/login")
    assert resp.status == 200
    text = await resp.text()
    assert 'id="instance-banner"' in text
    assert "RESERVEINSTANS: Laptop reserve" in text


@pytest.mark.integration
async def test_banner_not_shown_in_production(client: _TestClient, instance) -> None:
    instance("UpCloud prod", "production")
    resp = await client.get("/login")
    assert resp.status == 200
    assert 'id="instance-banner"' not in await resp.text()


@pytest.mark.integration
async def test_system_page_requires_login(client: _TestClient) -> None:
    resp = await client.get("/system", allow_redirects=False)
    assert resp.status == 303
    assert resp.headers["Location"].startswith("/login")


@pytest.mark.integration
async def test_system_page_requires_admin(client: _TestClient) -> None:
    await login(client, "event-admin")
    resp = await client.get("/system", allow_redirects=False)
    assert resp.status == 303
    assert resp.headers["Location"].startswith("/login")


@pytest.mark.integration
async def test_system_page_admin(client: _TestClient, instance, status_file) -> None:
    instance("Laptop reserve", "standby")
    status_file(status_doc())
    await login(client, "admin")
    resp = await client.get("/system", allow_redirects=False)
    assert resp.status == 200
    text = await resp.text()
    assert "Laptop reserve" in text
    assert "mongo_20261104_181500.archive.gz" in text
    assert "contestants" in text
    assert 'id="mySystem"' in text  # menu link for admin
    assert 'id="mySystemHome"' in text  # link back to main page
    assert 'id="services"' in text
    assert (
        'href="https://github.com/langrenn-sprint/user-service/commit/'
        '4e183fd0c2b1a9e8d7f6a5b4c3d2e1f0a9b8c7d6"'
    ) in text


@pytest.mark.integration
async def test_system_page_services_not_running(
    client: _TestClient, status_file
) -> None:
    status_file(
        status_doc(
            services=[
                service_doc("integration-service", state="exited"),
                service_doc("<b>evil</b>", revision=None, source=None),
            ]
        )
    )
    await login(client, "admin")
    resp = await client.get("/system", allow_redirects=False)
    assert resp.status == 200
    text = await resp.text()
    assert "Tjenesten integration-service kjører ikke (status: exited)." in text
    assert "Stoppet" in text
    assert "<b>evil</b>" not in text  # values from the file are escaped
    assert "&lt;b&gt;evil&lt;/b&gt;" in text


@pytest.mark.integration
async def test_system_page_without_services(client: _TestClient, status_file) -> None:
    doc = status_doc()
    del doc["services"]
    status_file(doc)
    await login(client, "admin")
    resp = await client.get("/system", allow_redirects=False)
    assert resp.status == 200
    assert "Statusfila har ingen informasjon om tjenestene." in await resp.text()


@pytest.mark.integration
async def test_system_page_admin_no_status(
    client: _TestClient, instance, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("SYSTEM_STATUS_FILE", raising=False)
    instance("Lokal", "test")
    await login(client, "admin")
    resp = await client.get("/system", allow_redirects=False)
    assert resp.status == 200
    assert "Ingen statusinformasjon" in await resp.text()


@pytest.mark.integration
async def test_system_page_admin_invalid_status(
    client: _TestClient, status_file
) -> None:
    status_file("{broken")
    await login(client, "admin")
    resp = await client.get("/system", allow_redirects=False)
    assert resp.status == 200
    assert "Ingen statusinformasjon" in await resp.text()
