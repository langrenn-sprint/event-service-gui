"""Integration test cases for instance banner and system page (#198)."""

import base64
import datetime
import json
import time
from pathlib import Path

import pytest
from aiohttp.test_utils import TestClient as _TestClient
from aioresponses import aioresponses

from event_service_gui.adapters import ServiceHealthAdapter, SystemStatusAdapter
from event_service_gui.adapters.user_adapter import get_role_from_token
from event_service_gui.services import SystemStatusService
from event_service_gui.services.system_status_service import format_mib, format_percent

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
        "memory": memory_doc(),
        "services": [
            service_doc("user-service"),
            service_doc("event-service"),
        ],
    }
    doc.update(overrides)
    return doc


GB = 1024**3


def memory_doc(used_ratio: float = 0.5, swap_used_ratio: float = 0.0, **overrides):
    """Return a `memory` section: 32 GB memory and 8 GB swap, used as given."""
    doc = {
        "total_bytes": 32 * GB,
        "available_bytes": round(32 * GB * (1 - used_ratio)),
        "swap_total_bytes": 8 * GB,
        "swap_free_bytes": round(8 * GB * (1 - swap_used_ratio)),
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
        "memory_bytes": 523 * 1024**2,
        "memory_limit_bytes": 32 * GB,  # no own limit: the machine's memory
        "memory_percent": 1.6,
        "cpu_percent": 1.39,
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


@pytest.fixture(autouse=True)
def no_health_checks(monkeypatch: pytest.MonkeyPatch) -> None:
    """No live health checks in the page tests, unless a test mocks them."""

    async def check_services(self) -> list[dict]:
        return []

    monkeypatch.setattr(ServiceHealthAdapter, "check_services", check_services)


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
    assert info["memory"]["known"] is True
    assert info["memory"]["used_text"] == "16.0 GiB av 32.0 GiB (50%)"
    assert info["memory"]["used_percent"] == "50%"
    assert info["memory"]["swap_text"] == "0 MiB av 8.0 GiB (0%)"
    assert info["memory"]["total"] == "32.0 GiB"
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
    assert service["memory_text"] == "523 MiB"
    assert service["memory_share"] == "1.6%"
    assert service["memory_limit_text"] == ""
    assert service["cpu_text"] == "1.4%"


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
            payload={
                "token": make_token(
                    {"username": "tester", "role": role, "exp": time.time() + 3600}
                )
            },
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


# --- Memory (deploy#13) -----------------------------------------------------


@pytest.mark.integration
@pytest.mark.parametrize(
    ("used_percent", "level"),
    [
        (85, None),  # limits are "above"
        (86, "warning"),
        (95, "warning"),
        (96, "error"),
    ],
)
def test_memory_used_thresholds(status_file, used_percent: int, level) -> None:
    # Whole percentages of 100 MB, so 85 % is exactly 85 %.
    mb = 1024**2
    status_file(
        status_doc(
            memory=memory_doc(
                total_bytes=100 * mb, available_bytes=(100 - used_percent) * mb
            )
        )
    )
    info = SystemStatusService().get_system_info(now=NOW)
    memory = info["memory"]
    memory_warnings = [w for w in info["warnings"] if "minne" in w["text"]]
    if level is None:
        assert memory_warnings == []
    else:
        assert [w["level"] for w in memory_warnings] == [level]
        assert memory_warnings[0]["text"].startswith(
            f"Lite ledig minne: {used_percent}% brukt"
        )
    assert memory["used_warning"] is (level == "warning")
    assert memory["used_error"] is (level == "error")


@pytest.mark.integration
@pytest.mark.parametrize(("swap_used_ratio", "warn"), [(0.5, False), (0.51, True)])
def test_memory_swap_threshold(status_file, swap_used_ratio: float, warn: bool) -> None:
    status_file(status_doc(memory=memory_doc(swap_used_ratio=swap_used_ratio)))
    info = SystemStatusService().get_system_info(now=NOW)
    swap_warnings = [w for w in info["warnings"] if "swap" in w["text"]]
    assert info["memory"]["swap_warning"] is warn
    if warn:
        assert swap_warnings == [
            {
                "level": "warning",
                "text": "Mye swap i bruk: 51% - maskinen har for lite minne og kan bli treg.",
            }
        ]
        assert info["memory"]["swap_text"] == "4.1 GiB av 8.0 GiB (51%)"
    else:
        assert swap_warnings == []


@pytest.mark.integration
def test_memory_no_swap(status_file) -> None:
    status_file(status_doc(memory=memory_doc(swap_total_bytes=0, swap_free_bytes=0)))
    info = SystemStatusService().get_system_info(now=NOW)
    assert info["memory"]["swap_text"] == "Ingen swap"
    assert info["memory"]["swap_warning"] is False
    assert not any("swap" in t for t in warning_texts(info))


@pytest.mark.integration
@pytest.mark.parametrize("memory", ["null", "missing", "wrong types", "negative"])
def test_memory_unknown(status_file, memory: str) -> None:
    """memory is null if deploy could not read it: "ukjent", no warning."""
    doc = status_doc()
    if memory == "null":
        doc["memory"] = None
    elif memory == "missing":
        del doc["memory"]  # status files from before memory was added
    elif memory == "wrong types":
        doc["memory"] = {
            "total_bytes": "32",
            "available_bytes": True,
            "swap_total_bytes": None,
            "swap_free_bytes": [],
        }
    else:
        doc["memory"] = memory_doc(total_bytes=-1, swap_total_bytes=-1)
    status_file(doc)
    info = SystemStatusService().get_system_info(now=NOW)
    assert info["memory"] == {
        "known": False,
        "total": "ukjent",
        "used_text": "ukjent",
        "used_percent": "",
        "used_warning": False,
        "used_error": False,
        "swap_text": "ukjent",
        "swap_percent": "",
        "swap_warning": False,
    }
    assert info["warnings"] == []


@pytest.mark.integration
def test_memory_available_above_total(status_file) -> None:
    """Inconsistent numbers give 0 % used, not a negative amount."""
    status_file(status_doc(memory=memory_doc(available_bytes=40 * GB)))
    info = SystemStatusService().get_system_info(now=NOW)
    assert info["memory"]["used_text"] == "0 MiB av 32.0 GiB (0%)"


@pytest.mark.integration
async def test_system_page_memory(client: _TestClient, status_file) -> None:
    status_file(status_doc(memory=memory_doc(0.96, swap_used_ratio=0.6)))
    await login(client, "admin")
    resp = await client.get("/system", allow_redirects=False)
    assert resp.status == 200
    text = await resp.text()
    assert 'id="memory"' in text
    assert 'class="danger">30.7 GiB av 32.0 GiB (96%)</td>' in text
    assert 'class="warning">4.8 GiB av 8.0 GiB (60%)</td>' in text
    assert "Lite ledig minne: 96% brukt (1.3 GiB tilgjengelig)." in text


@pytest.mark.integration
async def test_system_page_memory_unknown(client: _TestClient, status_file) -> None:
    status_file(status_doc(memory=None))
    await login(client, "admin")
    resp = await client.get("/system", allow_redirects=False)
    assert resp.status == 200
    text = await resp.text()
    assert (
        '<td data-field="memory.used_text" data-class="memory.used_warning:warning memory.used_error:danger" >ukjent</td>'
        in text
    )


# --- Memory and CPU per service (deploy#13) ----------------------------------

MIB = 1024**2


@pytest.mark.integration
@pytest.mark.parametrize(
    ("value", "text"),
    [
        (None, ""),
        (0, "0 MiB"),
        (0.3 * MIB, "0.3 MiB"),
        (5 * MIB, "5.0 MiB"),
        (523 * MIB, "523 MiB"),
        (1023 * MIB, "1023 MiB"),
        (GB, "1.0 GiB"),
        (1.5 * GB, "1.5 GiB"),
        (32 * GB, "32.0 GiB"),
        (-1, ""),
        (True, ""),
        ("523", ""),
    ],
)
def test_format_mib(value, text: str) -> None:
    assert format_mib(value) == text


@pytest.mark.integration
@pytest.mark.parametrize(
    ("value", "text"),
    [(0, "0.0%"), (0.18, "0.2%"), (9.94, "9.9%"), (12.4, "12%"), (250, "250%")],
)
def test_format_percent(value: float, text: str) -> None:
    assert format_percent(value) == text


def service_by_name(info: dict, name: str) -> dict:
    return next(s for s in info["services"] if s["name"] == name)


@pytest.mark.integration
def test_service_usage_not_running(status_file) -> None:
    """docker stats are null for a service that is not running."""
    status_file(
        status_doc(
            services=[
                service_doc(
                    "integration-service",
                    state="exited",
                    memory_bytes=None,
                    memory_limit_bytes=None,
                    memory_percent=None,
                    cpu_percent=None,
                )
            ]
        )
    )
    service = service_by_name(
        SystemStatusService().get_system_info(now=NOW), "integration-service"
    )
    assert service["memory_text"] == "–"
    assert service["memory_share"] == ""
    assert service["memory_limit_text"] == ""
    assert service["cpu_text"] == "–"


@pytest.mark.integration
def test_service_usage_missing_and_wrong_types(status_file) -> None:
    """Status files from before the stats, and invalid values: "–"."""
    old = service_doc("old")
    for key in ("memory_bytes", "memory_limit_bytes", "memory_percent", "cpu_percent"):
        del old[key]
    wrong = service_doc("wrong", memory_bytes="523", cpu_percent=True)
    status_file(status_doc(services=[old, wrong]))
    info = SystemStatusService().get_system_info(now=NOW)
    for name in ("old", "wrong"):
        service = service_by_name(info, name)
        assert (
            service["memory_text"],
            service["memory_share"],
            service["memory_limit_text"],
            service["cpu_text"],
        ) == ("–", "", "", "–")


@pytest.mark.integration
def test_service_usage_own_limit(status_file) -> None:
    """A container with its own limit also gets the share of that limit."""
    status_file(
        status_doc(
            services=[
                service_doc(
                    "mongodb",
                    memory_bytes=300 * MIB,
                    memory_limit_bytes=512 * MIB,
                    cpu_percent=250.0,
                )
            ]
        )
    )
    service = service_by_name(SystemStatusService().get_system_info(now=NOW), "mongodb")
    assert service["memory_text"] == "300 MiB"
    assert service["memory_share"] == "0.9%"
    assert service["memory_limit_text"] == "59% av grensen (512 MiB)"
    assert service["cpu_text"] == "250%"


@pytest.mark.integration
def test_service_usage_limit_rounded_by_docker(status_file) -> None:
    """docker rounds the limit; within 2 % it is the machine's memory, not a limit."""
    status_file(
        status_doc(
            services=[service_doc("event-service", memory_limit_bytes=round(32.4 * GB))]
        )
    )
    service = service_by_name(
        SystemStatusService().get_system_info(now=NOW), "event-service"
    )
    assert service["memory_limit_text"] == ""


@pytest.mark.integration
def test_service_usage_machine_memory_unknown(status_file) -> None:
    """Without the machine's memory, only the share of docker's limit is known.

    That limit is the machine's memory unless the container has its own, so
    the text must not claim it is a container limit.
    """
    status_file(status_doc(memory=None))
    service = service_by_name(
        SystemStatusService().get_system_info(now=NOW), "user-service"
    )
    assert service["memory_text"] == "523 MiB"
    assert service["memory_share"] == ""
    assert service["memory_limit_text"] == (
        "1.6% av minnet containeren kan bruke (32.0 GiB)"
    )


@pytest.mark.integration
def test_service_usage_health_only_row(status_file) -> None:
    """A service only known from the health check has no stats."""
    status_file(status_doc(services=[]))
    info = SystemStatusService().get_system_info(
        now=NOW,
        health=[
            {"name": "race-service", "status": "ok", "response_ms": 3, "detail": ""}
        ],
    )
    service = service_by_name(info, "race-service")
    assert (
        service["memory_text"],
        service["memory_share"],
        service["memory_limit_text"],
        service["cpu_text"],
    ) == ("–", "", "", "–")


@pytest.mark.integration
async def test_system_page_service_usage(client: _TestClient, status_file) -> None:
    status_file(
        status_doc(
            services=[
                service_doc("user-service"),
                service_doc(
                    "integration-service",
                    state="exited",
                    memory_bytes=None,
                    memory_limit_bytes=None,
                    memory_percent=None,
                    cpu_percent=None,
                ),
            ]
        )
    )
    await login(client, "admin")
    resp = await client.get("/system", allow_redirects=False)
    assert resp.status == 200
    text = await resp.text()
    assert '<span class="sort-label">Minne</span>' in text
    assert '<span class="sort-label">CPU</span>' in text
    # The share of the machine's memory is shown, not hidden in a tooltip
    assert '<td>523 MiB <span class="text-muted">(1.6%)</span></td>' in text
    assert "info-tip-value" not in text
    assert "<td>1.4%</td>" in text
    assert "<td>–</td>" in text  # memory and CPU of the stopped service
    assert 'colspan="8"' not in text


@pytest.mark.integration
async def test_system_page_service_own_limit(client: _TestClient, status_file) -> None:
    status_file(
        status_doc(
            services=[
                service_doc(
                    "mongodb", memory_bytes=300 * MIB, memory_limit_bytes=512 * MIB
                )
            ]
        )
    )
    await login(client, "admin")
    resp = await client.get("/system", allow_redirects=False)
    assert resp.status == 200
    assert (
        '<td>300 MiB <span class="text-muted">(0.9%)</span>'
        '<br><small class="text-muted">59% av grensen (512 MiB)</small></td>'
    ) in await resp.text()


# --- Sort keys for the services table ------------------------------------------


def ordered(info: dict, key: str) -> list[str]:
    """Service names sorted as system.js does: ascending by key, None last."""
    services = info["services"]
    with_key = [s for s in services if s["sort"][key] is not None]
    without = [s for s in services if s["sort"][key] is None]
    return [s["name"] for s in sorted(with_key, key=lambda s: s["sort"][key])] + [
        s["name"] for s in without
    ]


@pytest.mark.integration
def test_sort_keys(status_file) -> None:
    status_file(
        status_doc(
            services=[
                service_doc("User-Service", memory_bytes=100 * MIB, cpu_percent=5.0),
                service_doc(
                    "integration-service",
                    state="exited",
                    started_at="2026-11-05T10:00:00+01:00",
                    memory_bytes=None,
                    cpu_percent=None,
                ),
                service_doc(
                    "mongodb",
                    memory_bytes=900 * MIB,
                    cpu_percent=0.5,
                    image_created="2026-10-27T00:26:05+01:00",
                    started_at="2026-11-05T11:00:00+01:00",
                ),
                {"name": "race-service", "state": "missing"},
            ]
        )
    )
    info = SystemStatusService().get_system_info(now=NOW)
    mongodb = service_by_name(info, "mongodb")
    assert mongodb["sort"] == {
        "name": "mongodb",
        "state": 2,
        "health": [2, 0],
        "memory": -900 * MIB,
        "cpu": -0.5,
        "image_created": -datetime.datetime.fromisoformat(
            "2026-10-27T00:26:05+01:00"
        ).timestamp(),
        "started_at": -datetime.datetime.fromisoformat(
            "2026-11-05T11:00:00+01:00"
        ).timestamp(),
    }
    assert service_by_name(info, "User-Service")["sort"]["name"] == "user-service"
    # Most interesting first, no value last
    assert ordered(info, "state")[:2] == ["integration-service", "race-service"]
    assert ordered(info, "memory") == [
        "mongodb",
        "User-Service",
        "integration-service",
        "race-service",
    ]
    assert ordered(info, "cpu")[:2] == ["User-Service", "mongodb"]
    assert ordered(info, "started_at")[:2] == ["mongodb", "integration-service"]
    assert ordered(info, "image_created")[-1] == "race-service"
    json.dumps(info)  # the keys go to the browser as JSON
