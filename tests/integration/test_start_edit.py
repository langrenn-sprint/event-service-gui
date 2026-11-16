"""Integration test cases for adding and moving starts (Legg til and Flytt).

Flytt deletes the start from its heat and adds it to the new one. Everything
is checked before the delete, so a move that can not be done leaves the start
where it was, and a start is put back if adding it still fails. Legg til
picks the first free position when none is given, and works in an empty heat.

race-service is replaced by a fake that keeps the races in memory.
"""

from http import HTTPStatus

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient as _TestClient
from yarl import URL

from event_service_gui.adapters import (
    ContestantsAdapter,
    RaceplansAdapter,
    StartAdapter,
    TimeEventsAdapter,
)

from .test_config_access import EVENT_ID, fakes, login, photo_service

__all__ = ["fakes", "photo_service"]  # fixtures used by the tests below

STARTLIST_ID = "sl1"
CONTESTANTS = {
    bib: {"first_name": "Navn", "last_name": f"{bib}", "club": "Lyn"}
    for bib in range(1, 30)
}


class FakeRaceService:
    """Races with start entries, as race-service keeps them."""

    def __init__(self) -> None:
        self.races: dict[str, dict] = {}
        self.fail_create_in: str = ""  # race where creating a start fails
        self.create_error: Exception | None = None  # every create fails with it
        self.next_id = 0

    def add_race(self, race_id: str, round_: str, bibs: list[int], max_: int = 10):
        self.races[race_id] = {
            "id": race_id,
            "round": round_,
            "index": "A",
            "heat": 1,
            "start_time": "2026-11-06T09:00:00",
            "max_no_of_contestants": max_,
            "start_entries": [],
        }
        for bib in bibs:
            self.create(race_id, bib, len(self.races[race_id]["start_entries"]) + 1)

    def create(self, race_id: str, bib: int, position: int) -> None:
        self.next_id += 1
        self.races[race_id]["start_entries"].append(
            {
                "id": f"s{self.next_id}",
                "startlist_id": STARTLIST_ID,
                "race_id": race_id,
                "bib": bib,
                "starting_position": position,
                "scheduled_start_time": "2026-11-06T09:00:00",
                "name": f"Navn {bib}",
                "club": "Lyn",
            }
        )

    def bibs(self, race_id: str) -> dict[int, int]:
        """Return {bib: starting_position} for the race."""
        return {
            e["bib"]: e["starting_position"]
            for e in self.races[race_id]["start_entries"]
        }

    def start_id(self, race_id: str, bib: int) -> str:
        return next(
            e["id"] for e in self.races[race_id]["start_entries"] if e["bib"] == bib
        )


@pytest.fixture
def race_service(monkeypatch: pytest.MonkeyPatch, fakes) -> FakeRaceService:
    service = FakeRaceService()

    async def get_race_by_id(self, token: str, race_id: str) -> dict:
        assert race_id, "get_race_by_id called without race id"
        return service.races[race_id]

    async def get_start_entry_by_id(self, token, race_id, start_id) -> dict:
        return next(
            e for e in service.races[race_id]["start_entries"] if e["id"] == start_id
        )

    async def get_start_entries_by_bib(self, token, event_id, bib) -> list:
        return [
            e
            for race in service.races.values()
            for e in race["start_entries"]
            if e["bib"] == bib
        ]

    async def get_all_starts_by_event(self, token, event_id) -> list:
        return [{"id": STARTLIST_ID}]

    async def delete_start_entry(self, token, race_id, start_id) -> str:
        race = service.races[race_id]
        race["start_entries"] = [
            e for e in race["start_entries"] if e["id"] != start_id
        ]
        return start_id

    async def create_start_entry(self, token, new_start: dict) -> str:
        race_id = new_start["race_id"]
        race = service.races[race_id]
        if service.create_error:
            raise service.create_error
        if race_id == service.fail_create_in:
            service.fail_create_in = ""  # only the first time
            raise web.HTTPBadRequest(reason="create_start_entry failed")
        assert len(race["start_entries"]) < race["max_no_of_contestants"]
        assert new_start["starting_position"] not in service.bibs(race_id).values()
        assert new_start["startlist_id"] == STARTLIST_ID
        service.create(race_id, new_start["bib"], new_start["starting_position"])
        return "ok"

    async def get_contestant_by_bib(self, token, event_id, bib) -> dict:
        return CONTESTANTS.get(bib, {})

    async def get_time_events(self, token, event_id, bib) -> list:
        return []

    for cls, name, fake in [
        (RaceplansAdapter, "get_race_by_id", get_race_by_id),
        (StartAdapter, "get_start_entry_by_id", get_start_entry_by_id),
        (StartAdapter, "get_start_entries_by_bib", get_start_entries_by_bib),
        (StartAdapter, "get_all_starts_by_event", get_all_starts_by_event),
        (StartAdapter, "delete_start_entry", delete_start_entry),
        (StartAdapter, "create_start_entry", create_start_entry),
        (ContestantsAdapter, "get_contestant_by_bib", get_contestant_by_bib),
        (
            TimeEventsAdapter,
            "get_time_events_by_event_id_and_bib",
            get_time_events,
        ),
    ]:
        monkeypatch.setattr(cls, name, fake)

    service.add_race("qa1", "Q", [1, 2, 3])
    service.add_race("qa2", "Q", [4, 5])
    service.add_race("sa1", "S", [6])
    return service


async def post(client: _TestClient, **fields: str) -> str:
    """Post the start_edit form and return the message shown."""
    await login(client, "result-admin")
    form = {"event_id": EVENT_ID, "klasse": "G16", "runde": "Q", **fields}
    resp = await client.post("/start_edit", data=form, allow_redirects=False)
    assert resp.status == HTTPStatus.SEE_OTHER
    url = URL(resp.headers["Location"])
    assert url.path == "/start_edit"
    return url.query["informasjon"]


async def move(
    client: _TestClient, service: FakeRaceService, bib: int, from_: str, to: str
) -> str:
    return await post(
        client,
        race_id=from_,
        start_id=service.start_id(from_, bib),
        bib=str(bib),
        new_heat=to,
        move_start=" Flytt ",
    )


# --- Flytt -----------------------------------------------------------------------------


@pytest.mark.integration
async def test_move_start(client: _TestClient, race_service: FakeRaceService) -> None:
    message = await move(client, race_service, 2, "qa1", "qa2")
    assert message == "Flyttet nr 2."
    assert race_service.bibs("qa1") == {1: 1, 3: 3}
    assert race_service.bibs("qa2") == {4: 1, 5: 2, 2: 3}


@pytest.mark.integration
async def test_move_start_without_new_heat_keeps_the_start(
    client: _TestClient, race_service: FakeRaceService
) -> None:
    """Before, the start was deleted and then the move failed."""
    message = await move(client, race_service, 2, "qa1", "")
    assert message == "Velg nytt heat før du trykker Flytt."
    assert race_service.bibs("qa1") == {1: 1, 2: 2, 3: 3}


@pytest.mark.integration
async def test_move_start_to_full_heat_keeps_the_start(
    client: _TestClient, race_service: FakeRaceService
) -> None:
    race_service.add_race("qa3", "Q", [7, 8], max_=2)
    message = await move(client, race_service, 2, "qa1", "qa3")
    assert message == "Ikke flyttet: Heatet er fullt."
    assert race_service.bibs("qa1") == {1: 1, 2: 2, 3: 3}


@pytest.mark.integration
async def test_move_start_to_round_with_the_bib_keeps_the_start(
    client: _TestClient, race_service: FakeRaceService
) -> None:
    race_service.add_race("sa2", "S", [2])
    message = await move(client, race_service, 2, "qa1", "sa1")
    assert message == "Ikke flyttet: Nr 2 er allerede med i runde S."
    assert race_service.bibs("qa1") == {1: 1, 2: 2, 3: 3}


@pytest.mark.integration
async def test_failed_move_puts_the_start_back(
    client: _TestClient, race_service: FakeRaceService
) -> None:
    race_service.fail_create_in = "qa2"
    message = await move(client, race_service, 2, "qa1", "qa2")
    assert message == "Det har oppstått en feil: create_start_entry failed"
    assert race_service.bibs("qa1") == {1: 1, 3: 3, 2: 2}
    assert race_service.bibs("qa2") == {4: 1, 5: 2}


@pytest.mark.integration
async def test_failed_move_and_put_back_says_where_to_add_again(
    client: _TestClient, race_service: FakeRaceService
) -> None:
    race_service.create_error = web.HTTPBadRequest(reason="create_start_entry failed")
    message = await move(client, race_service, 2, "qa1", "qa2")
    assert message == (
        "Det har oppstått en feil: Flyttingen feilet, og nr 2 kunne ikke legges "
        "tilbake i heatet som starter 09:00:00, posisjon 2. Legg til nr 2 på nytt."
    )
    assert race_service.bibs("qa1") == {1: 1, 3: 3}


@pytest.mark.integration
@pytest.mark.parametrize(
    "error",
    [
        web.HTTPBadRequest(reason="Error - 401: Unauthorized."),
        Exception("401 Unathorized - create_start_entry"),
    ],
)
async def test_expired_login_during_move_goes_to_login_with_what_to_do(
    client: _TestClient, race_service: FakeRaceService, error: Exception
) -> None:
    """The start is out of both heats: the login page says how to fix it."""
    await login(client, "result-admin")
    race_service.create_error = error
    form = {
        "event_id": EVENT_ID,
        "klasse": "G16",
        "runde": "Q",
        "race_id": "qa1",
        "start_id": race_service.start_id("qa1", 2),
        "bib": "2",
        "new_heat": "qa2",
        "move_start": " Flytt ",
    }
    resp = await client.post("/start_edit", data=form, allow_redirects=False)

    assert resp.status == HTTPStatus.SEE_OTHER
    url = URL(resp.headers["Location"])
    assert url.path == "/login"
    assert url.query["informasjon"] == (
        "Innloggingen er utløpt under flyttingen. Nr 2 ble tatt ut av heatet som "
        "starter 09:00:00, posisjon 2, men ikke lagt inn igjen. Logg inn, og legg "
        "til nr 2 på nytt."
    )
    assert url.query["next"] == "/start_edit"
    assert race_service.bibs("qa1") == {1: 1, 3: 3}


# --- Legg til --------------------------------------------------------------------------


async def add(client: _TestClient, race_id: str, bib: str, position: str = "") -> str:
    return await post(
        client,
        race_id=race_id,
        bib=bib,
        starting_position=position,
        create_start=" Legg til ",
    )


@pytest.mark.integration
async def test_add_start_without_position_takes_first_free(
    client: _TestClient, race_service: FakeRaceService
) -> None:
    """Before, an empty position gave an unexpected error."""
    race_service.races["qa1"]["start_entries"].pop(0)  # position 1 is free
    assert await add(client, "qa1", "9") == "Lagt til nr 9."
    assert race_service.bibs("qa1") == {2: 2, 3: 3, 9: 1}


@pytest.mark.integration
async def test_add_start_with_position(
    client: _TestClient, race_service: FakeRaceService
) -> None:
    assert await add(client, "qa1", "9", "7") == "Lagt til nr 9."
    assert race_service.bibs("qa1")[9] == 7


@pytest.mark.integration
async def test_add_start_to_empty_heat(
    client: _TestClient, race_service: FakeRaceService
) -> None:
    race_service.add_race("qa3", "Q", [])
    assert await add(client, "qa3", "9") == "Lagt til nr 9."
    assert race_service.bibs("qa3") == {9: 1}


@pytest.mark.integration
@pytest.mark.parametrize(
    ("bib", "position", "expected"),
    [
        ("", "", "Fyll inn startnummer."),
        ("99", "", "Fant ikke deltaker med startnr 99."),
        ("9", "2", "Posisjon 2 er opptatt."),
        ("9", "x", "Posisjon må være et tall fra 1 og oppover."),
        ("4", "", "Nr 4 er allerede med i runde Q."),
    ],
)
async def test_add_start_with_invalid_input(
    client: _TestClient,
    race_service: FakeRaceService,
    bib: str,
    position: str,
    expected: str,
) -> None:
    assert await add(client, "qa1", bib, position) == expected
    assert race_service.bibs("qa1") == {1: 1, 2: 2, 3: 3}
