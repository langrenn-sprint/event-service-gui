"""Integration test cases for swapping starts and for empty ids.

swap_starts, used when round 2 is shuffled, deleted two starts and created
them again; if that failed, contestants were missing from round 2. Now it
updates the two start entries in place, and undoes the first update if the
second fails.

An empty id turned /races/{id} into /races/. The services redirect that to
/races, and the client follows: a GET got the list of all races, and a DELETE
could delete every item. Now the adapters refuse an empty id.
"""

import pytest
from aiohttp import web

from event_service_gui.adapters import RaceclassesAdapter, RaceplansAdapter
from event_service_gui.adapters.ids import require_id
from event_service_gui.adapters.start_adapter import StartAdapter, swap_starts


class FakeRaceService:
    """Races with start entries, and the requests received."""

    def __init__(self) -> None:
        self.races: dict[str, list[dict]] = {}
        self.requests: list[tuple[str, str]] = []
        self.fail_puts: set[int] = set()  # numbers of the PUTs that fail
        self.puts = 0

    def add_race(self, race_id: str, bibs: list[int]) -> None:
        self.races[race_id] = [
            {
                "id": f"{race_id}-{position}",
                "race_id": race_id,
                "startlist_id": "sl1",
                "bib": bib,
                "starting_position": position,
                "scheduled_start_time": "2026-11-06T09:00:00",
                "name": f"Navn {bib}",
                "club": "Lyn",
            }
            for position, bib in enumerate(bibs, start=1)
        ]

    def bibs(self, race_id: str) -> list[int]:
        return [entry["bib"] for entry in self.races[race_id]]

    async def handle(self, request: web.Request) -> web.Response:
        self.requests.append((request.method, request.path))
        return web.json_response([])  # a list, as for /races or /raceclasses

    async def get_race(self, request: web.Request) -> web.Response:
        race_id = request.match_info["race_id"]
        return web.json_response(
            {"id": race_id, "round": "R2", "start_entries": self.races[race_id]}
        )

    async def put_start_entry(self, request: web.Request) -> web.Response:
        self.puts += 1
        if self.puts in self.fail_puts:
            return web.json_response({"detail": "failed"}, status=500)
        body = await request.json()
        entries = self.races[request.match_info["race_id"]]
        index = next(
            i for i, e in enumerate(entries) if e["id"] == request.match_info["id"]
        )
        entries[index] = body
        return web.Response(status=204)  # as race-service answers


@pytest.fixture
async def race_service(aiohttp_server, monkeypatch: pytest.MonkeyPatch):
    fake = FakeRaceService()
    app = web.Application()
    app.router.add_get("/races/{race_id}", fake.get_race)
    app.router.add_put("/races/{race_id}/start-entries/{id}", fake.put_start_entry)
    app.router.add_route("*", "/{tail:.*}", fake.handle)
    server = await aiohttp_server(app)
    url = str(server.make_url("")).rstrip("/")
    adapters = "event_service_gui.adapters"
    monkeypatch.setattr(f"{adapters}.start_adapter.RACE_SERVICE_URL", url)
    monkeypatch.setattr(f"{adapters}.raceplans_adapter.RACE_SERVICE_URL", url)
    monkeypatch.setattr(f"{adapters}.raceclasses_adapter.EVENT_SERVICE_URL", url)
    fake.add_race("r1", [1, 2, 3, 4, 5])
    fake.add_race("r2", [6, 7, 8, 9, 10])
    return fake


# --- swap_starts -----------------------------------------------------------------------


@pytest.mark.integration
async def test_swap_starts(race_service: FakeRaceService) -> None:
    assert await swap_starts("t", "r2", "r1", [1, 3]) == 2
    assert race_service.bibs("r1") == [1, 7, 3, 9, 5]
    assert race_service.bibs("r2") == [6, 2, 8, 4, 10]
    # the start entries keep their race and position:
    assert race_service.races["r2"][1]["id"] == "r2-2"
    assert race_service.races["r2"][1]["starting_position"] == 2
    assert race_service.races["r2"][1]["name"] == "Navn 2"


@pytest.mark.integration
async def test_swap_skips_places_a_heat_does_not_have(
    race_service: FakeRaceService,
) -> None:
    race_service.add_race("r3", [11, 12])
    assert await swap_starts("t", "r3", "r1", [0, 2, 4]) == 1
    assert race_service.bibs("r3") == [1, 12]
    assert race_service.bibs("r1") == [11, 2, 3, 4, 5]


@pytest.mark.integration
async def test_failed_swap_is_undone(race_service: FakeRaceService) -> None:
    race_service.fail_puts = {2}  # the second update of the first swap
    assert await swap_starts("t", "r2", "r1", [1, 3]) == 1
    assert race_service.bibs("r2") == [6, 7, 8, 4, 10]  # first swap undone
    assert race_service.bibs("r1") == [1, 2, 3, 9, 5]


@pytest.mark.integration
async def test_failed_undo_is_reported(race_service: FakeRaceService) -> None:
    race_service.fail_puts = {2, 3}  # the second update, and the undo
    with pytest.raises(Exception, match="nr 7 mangler, og nr 2 står i to heat"):
        await swap_starts("t", "r2", "r1", [1])


# --- update_start_entry ----------------------------------------------------------------


@pytest.mark.integration
async def test_update_start_entry_accepts_no_content(
    race_service: FakeRaceService,
) -> None:
    """race-service answers 204; before, only 201 was accepted."""
    entry = {**race_service.races["r1"][0], "name": "Nytt navn"}
    await StartAdapter().update_start_entry("t", entry["id"], entry)
    assert race_service.races["r1"][0]["name"] == "Nytt navn"


# --- Empty ids -------------------------------------------------------------------------


@pytest.mark.integration
def test_require_id() -> None:
    assert require_id("abc") == "abc"
    assert require_id(12) == "12"
    for empty in ["", "  ", None]:
        with pytest.raises(Exception, match="Mangler id"):
            require_id(empty)


@pytest.mark.integration
async def test_get_race_without_id_is_not_sent(race_service: FakeRaceService) -> None:
    """Before, it got the list of all races."""
    with pytest.raises(Exception, match="Mangler id"):
        await RaceplansAdapter().get_race_by_id("t", "")
    assert race_service.requests == []


@pytest.mark.integration
async def test_delete_raceclass_without_id_is_not_sent(
    race_service: FakeRaceService,
) -> None:
    """Before, it could delete all raceclasses in the event."""
    with pytest.raises(Exception, match="Mangler id"):
        await RaceclassesAdapter().delete_raceclass("t", "e1", "")
    assert race_service.requests == []
