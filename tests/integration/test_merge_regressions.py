"""Integration test cases for event-service-gui features changed by #227.

- Registering a start deletes an earlier DNS for the same bib in the same race.
- The control page rotates semi final templates again (shift_position).
"""

from http import HTTPStatus

import pytest
from aiohttp.test_utils import TestClient as _TestClient

from event_service_gui.adapters import TimeEventsAdapter
from event_service_gui.services import TimeEventsService

from .test_config_access import EVENT_ID, fakes, login, photo_service

__all__ = ["fakes", "photo_service"]  # fixtures used by the tests below


class FakeTimeEvents:
    """Time events in memory, with the TimeEventsAdapter methods used here."""

    def __init__(self, events: list) -> None:
        self.events = events
        self.deleted: list[str] = []

    async def create_time_event(self, token: str, time_event: dict) -> dict:
        new = {**time_event, "id": f"new-{len(self.events)}"}
        self.events.append(new)
        return new

    async def get_time_events_by_event_id_and_bib(
        self, token: str, event_id: str, bib: int
    ) -> list:
        return [e for e in self.events if e["bib"] == bib]

    async def delete_time_event(self, token: str, time_event_id: str) -> str:
        self.deleted.append(time_event_id)
        self.events = [e for e in self.events if e["id"] != time_event_id]
        return "204"


def start_event(bib: int, timing_point: str, race_id: str = "R1A1") -> dict:
    return {
        "id": "",
        "bib": bib,
        "event_id": EVENT_ID,
        "race_id": race_id,
        "timing_point": timing_point,
        "status": "OK",
    }


@pytest.fixture
def time_events(monkeypatch: pytest.MonkeyPatch) -> FakeTimeEvents:
    fake = FakeTimeEvents(
        [
            {"id": "dns-12", "bib": 12, "race_id": "R1A1", "timing_point": "DNS"},
            {"id": "dns-13", "bib": 13, "race_id": "R1A1", "timing_point": "DNS"},
            {"id": "dns-12-r2", "bib": 12, "race_id": "R2A1", "timing_point": "DNS"},
        ]
    )
    for name in (
        "create_time_event",
        "get_time_events_by_event_id_and_bib",
        "delete_time_event",
    ):
        monkeypatch.setattr(
            TimeEventsAdapter, name, lambda self, *a, _n=name: getattr(fake, _n)(*a)
        )
    return fake


@pytest.mark.integration
async def test_start_deletes_earlier_dns(time_events: FakeTimeEvents) -> None:
    informasjon = await TimeEventsService().create_start_time_event(
        "t", start_event(12, "Start")
    )
    assert time_events.deleted == ["dns-12"]
    assert "Slettet DNS registrering" in informasjon


@pytest.mark.integration
async def test_start_keeps_dns_in_other_races(time_events: FakeTimeEvents) -> None:
    """DNS in round 1 stays when the bib starts in round 2, and the other way."""
    await TimeEventsService().create_start_time_event(
        "t", start_event(12, "Start", race_id="R2A2")
    )
    assert time_events.deleted == []


@pytest.mark.integration
async def test_dns_does_not_delete_anything(time_events: FakeTimeEvents) -> None:
    await TimeEventsService().create_start_time_event("t", start_event(12, "DNS"))
    assert time_events.deleted == []


@pytest.mark.integration
async def test_control_rotates_semi_final_templates(
    client: _TestClient, fakes, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = []

    async def fake_shuffle(self, token: str, event_id: str) -> str:
        calls.append(event_id)
        return "Rotert."

    monkeypatch.setattr(TimeEventsService, "shuffle_semi_final_templates", fake_shuffle)
    await login(client, "admin")
    data = {
        "event_id": EVENT_ID,
        "valgt_klasse": "",
        "action": "Template",
        "shift_position": " Roter plasser til semi-heat ",
    }
    resp = await client.post("/control", data=data, allow_redirects=False)
    assert resp.status == HTTPStatus.SEE_OTHER
    assert calls == [EVENT_ID]
    assert "Rotert." in resp.headers["Location"]
