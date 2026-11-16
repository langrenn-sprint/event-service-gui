"""Integration test cases for data shown as text, not HTML (#229), and /secret (#233).

The pages' JavaScript put data from the server into the page with innerHTML,
so a contestant name with HTML in it ran as script in the browser of the
user registering times. Now the pages use textContent. The only exception is
the status message on the timing dashboard, which is HTML built by
video_events, with the data escaped on the server.
"""

import re
from http import HTTPStatus
from pathlib import Path

import pytest
from aiohttp.test_utils import TestClient as _TestClient

from event_service_gui.adapters import StatusAdapter
from event_service_gui.views.video_events import get_integration_status

TEMPLATES = Path("event_service_gui/templates")
EVIL = '<img src=x onerror="alert(1)"> & Co'


@pytest.mark.integration
@pytest.mark.parametrize(
    "template",
    ["timing.html", "resultat_edit_new.html", "photos_edit.html", "photo_finish.html"],
)
def test_no_innerhtml(template: str) -> None:
    assert "innerHTML" not in (TEMPLATES / template).read_text()


@pytest.mark.integration
def test_timing_dashboard_uses_innerhtml_only_for_the_status_message() -> None:
    text = (TEMPLATES / "timing_dash.html").read_text()
    uses = re.findall(r".*innerHTML.*", text)
    assert uses
    assert all(use.strip().endswith(".innerHTML = info;") for use in uses)


@pytest.mark.integration
async def test_status_message_is_escaped(monkeypatch: pytest.MonkeyPatch) -> None:
    """Data from photo-service is escaped; the markup around it is kept."""

    async def status(*_: object) -> list:
        return [
            {
                "time": '2026-11-06T12:00:00" onmouseover="alert(1)',
                "type": "integration_status",
                "message": f"Error {EVIL}",
            }
        ]

    monkeypatch.setattr(StatusAdapter, "get_status", status)

    html = await get_integration_status("token", "e1")

    assert "<img src=x" not in html
    assert '" onmouseover=' not in html
    assert "&lt;img src=x onerror=&quot;alert(1)&quot;&gt; &amp; Co" in html
    assert "<span id=red>" in html  # the markup from video_events is kept
    assert "upload.png" in html


@pytest.mark.integration
async def test_secret_route_is_removed(client: _TestClient) -> None:
    """The unused example route /secret read the session (#233)."""
    resp = await client.get("/secret", allow_redirects=False)
    assert resp.status == HTTPStatus.NOT_FOUND
