"""In-memory race-service and event-service for testing the services.

FakeRaceBackend holds races, start entries, time events, contestants and
raceclass results, and replaces the adapter methods that TimeEventsService
and RaceclassResultsService use (see patch_adapters). It does only what the
tests need, as race-service does it: e.g. a finish for a bib that is not in
the race's start list gets status Error, and a second finish for the same
bib in a race is refused with "already exists".
"""

import itertools

import pytest

from event_service_gui.adapters import (
    ContestantsAdapter,
    EventsAdapter,
    RaceclassesAdapter,
    RaceclassResultsAdapter,
    RaceplansAdapter,
    StartAdapter,
    TimeEventsAdapter,
)

EVENT_ID = "event-1"
STARTLIST_ID = "startlist-1"
RACECLASS = "G12"

# Individual Sprint for 24 contestants, from competition_format_individual_sprint.json
SPRINT_24 = {
    "no_of_heats": {
        "Q": {"A": 4},
        "S": {"A": 2, "C": 2},
        "F": {"A": 1, "B": 1, "C": 1},
    },
    "from_to": {
        "Q": {"A": {"S": {"A": 3, "C": "REST"}}},
        "S": {"A": {"F": {"A": 3, "B": "REST"}}, "C": {"F": {"C": 3}}},
    },
    "max_no_of_contestants": {"Q": 6, "S": 8, "F": 8},
}


def race_name(race: dict) -> str:
    """Return the name of a race, as in time events: FA, SA1, QA3."""
    if race["round"] == "F":
        return f"{race['round']}{race['index']}"
    return f"{race['round']}{race['index']}{race['heat']}"


def make_races(plan: dict = SPRINT_24, raceclass: str = RACECLASS) -> list[dict]:
    """Return the races of a plan, in start order, as race-service has them."""
    races = []
    order = itertools.count(1)
    for round_name, indexes in plan["no_of_heats"].items():
        for index, heats in indexes.items():
            for heat in range(1, heats + 1):
                number = next(order)
                race = {"round": round_name, "index": index, "heat": heat}
                races.append(
                    {
                        "id": f"{raceclass}-{race_name(race)}",
                        "event_id": EVENT_ID,
                        "raceclass": raceclass,
                        "round": round_name,
                        "index": index,
                        "heat": heat,
                        "order": number,
                        "start_time": f"2026-11-16T{9 + number // 60:02}:{number % 60:02}:00",
                        "max_no_of_contestants": plan["max_no_of_contestants"][
                            round_name
                        ],
                        "rule": plan["from_to"].get(round_name, {}).get(index, {}),
                        "no_of_contestants": 0,
                        "start_entries": [],
                        "results": {},
                    }
                )
    return races


class FakeRaceBackend:
    """Races, start entries, time events, contestants and raceclass results."""

    def __init__(self, races: list[dict] | None = None) -> None:
        self.races = {race["id"]: race for race in races or make_races()}
        self.time_events: list[dict] = []
        self.contestants: dict[int, dict] = {}
        self.raceclass_results: dict[str, dict] = {}
        self.deleted_raceclass_results: list[str] = []
        self.ids = itertools.count(1)

    # --- setup helpers ---------------------------------------------------------

    def add_contestant(self, bib: int, raceclass: str = RACECLASS) -> dict:
        contestant = {
            "id": f"c{bib}",
            "bib": bib,
            "first_name": "Løper",
            "last_name": str(bib),
            "club": "Lyn Ski",
            "ageclass": f"{raceclass} år",
            "raceclass": raceclass,
            "minidrett_id": f"m{bib}",
        }
        self.contestants[bib] = contestant
        return contestant

    def add_start(self, race_id: str, bib: int, position: int) -> dict:
        race = self.races[race_id]
        entry = {
            "id": f"s{next(self.ids)}",
            "race_id": race_id,
            "startlist_id": STARTLIST_ID,
            "bib": bib,
            "starting_position": position,
            "scheduled_start_time": race["start_time"],
            "name": f"Løper {bib}",
            "club": "Lyn Ski",
            "status": "OK",
        }
        race["start_entries"].append(entry)
        race["no_of_contestants"] = len(race["start_entries"])
        return entry

    def set_results(self, race_id: str, ranking: list[dict]) -> None:
        """Set the Finish results of a race: dicts with bib, rank and more."""
        results = []
        for item in ranking:
            result = {
                "id": f"t{next(self.ids)}",
                "timing_point": "Finish",
                "status": "OK",
                "name": f"Løper {item['bib']}",
                "club": "Lyn Ski",
                "next_race_id": None,
                **item,
            }
            results.append(result)
        self.races[race_id]["results"] = (
            {"Finish": {"ranking_sequence": results}} if results else {}
        )

    def starts(self, race_id: str) -> list[tuple[int, int]]:
        """Return (position, bib) of the starts in a race, sorted."""
        return sorted(
            (e["starting_position"], e["bib"])
            for e in self.races[race_id]["start_entries"]
        )

    def templates(self) -> list[dict]:
        return [t for t in self.time_events if t["timing_point"] == "Template"]

    # --- RaceplansAdapter ------------------------------------------------------

    async def get_all_races(self, token: str, event_id: str) -> list:
        return sorted(self.races.values(), key=lambda race: race["order"])

    async def get_races_by_racesclass(
        self, token: str, event_id: str, valgt_klasse: str
    ) -> list:
        return [
            r
            for r in await self.get_all_races(token, event_id)
            if r["raceclass"] == valgt_klasse
        ]

    async def get_race_by_id(self, token: str, race_id: str) -> dict:
        return self.races[race_id]

    # --- RaceclassesAdapter ---------------------------------------------------

    async def get_raceclasses(self, token: str, event_id: str) -> list:
        names = sorted({race["raceclass"] for race in self.races.values()})
        return [{"name": name} for name in names]

    # --- StartAdapter ----------------------------------------------------------

    async def create_start_entry(self, token: str, new_start: dict) -> str:
        entry = self.add_start(
            new_start["race_id"], new_start["bib"], new_start["starting_position"]
        )
        return entry["id"]

    async def get_start_entries_by_race_id(self, token: str, race_id: str) -> list:
        return list(self.races[race_id]["start_entries"])

    async def delete_start_entry(self, token: str, race_id: str, start_id: str) -> str:
        race = self.races[race_id]
        race["start_entries"] = [
            e for e in race["start_entries"] if e["id"] != start_id
        ]
        race["no_of_contestants"] = len(race["start_entries"])
        return "204"

    async def get_all_starts_by_event(self, token: str, event_id: str) -> list:
        return [{"id": STARTLIST_ID, "event_id": event_id}]

    # --- TimeEventsAdapter -----------------------------------------------------

    async def create_time_event(self, token: str, time_event: dict) -> dict:
        new = {**time_event, "id": f"t{next(self.ids)}", "changelog": []}
        if new["timing_point"] == "Finish":
            race = self.races[new["race_id"]]
            if any(
                t["bib"] == new["bib"]
                and t["race_id"] == new["race_id"]
                and t["timing_point"] == "Finish"
                for t in self.time_events
            ):
                msg = f"400 Time event for bib {new['bib']} already exists."
                raise Exception(msg)  # noqa: TRY002 - as the adapter raises
            if new["bib"] not in [e["bib"] for e in race["start_entries"]]:
                new["status"] = "Error"
                new["changelog"] = [
                    {"comment": f"Bib {new['bib']} er ikke i startlisten."}
                ]
        self.time_events.append(new)
        return new

    async def update_time_event(self, token: str, t_id: str, time_event: dict) -> str:
        self.time_events = [
            time_event if t["id"] == t_id else t for t in self.time_events
        ]
        return "204"

    async def delete_time_event(self, token: str, t_id: str) -> str:
        if not any(t["id"] == t_id for t in self.time_events):
            msg = f"404 Time event {t_id} not found."
            raise Exception(msg)  # noqa: TRY002
        self.time_events = [t for t in self.time_events if t["id"] != t_id]
        return "204"

    async def get_time_event_by_id(self, token: str, t_id: str) -> dict:
        for t in self.time_events:
            if t["id"] == t_id:
                return t
        msg = f"404 Time event {t_id} not found."
        raise Exception(msg)  # noqa: TRY002

    async def get_time_events_by_race_id(self, token: str, race_id: str) -> list:
        return [t for t in self.time_events if t["race_id"] == race_id]

    async def get_time_events_by_event_id_and_timing_point(
        self, token: str, event_id: str, timing_point: str
    ) -> list:
        return [t for t in self.time_events if t["timing_point"] == timing_point]

    # --- ContestantsAdapter ----------------------------------------------------

    async def get_contestant_by_bib(self, token: str, event_id: str, bib: int) -> dict:
        return self.contestants.get(bib, {})

    async def get_contestants_by_raceclass(
        self, token: str, event_id: str, raceclass: str
    ) -> list:
        return [c for c in self.contestants.values() if c["raceclass"] == raceclass]

    # --- RaceclassResultsAdapter ------------------------------------------------

    async def get_raceclass_result(self, event_id: str, raceclass: str) -> dict:
        return self.raceclass_results.get(raceclass, {})

    async def delete_raceclass_result(
        self, token: str, event_id: str, raceclass: str
    ) -> str:
        self.deleted_raceclass_results.append(raceclass)
        del self.raceclass_results[raceclass]
        return "204"

    async def create_raceclass_results(
        self, token: str, event_id: str, request_body: dict
    ) -> int:
        self.raceclass_results[request_body["raceclass_name"]] = request_body
        return 201


ADAPTER_METHODS = {
    RaceplansAdapter: ["get_all_races", "get_races_by_racesclass", "get_race_by_id"],
    RaceclassesAdapter: ["get_raceclasses"],
    StartAdapter: [
        "create_start_entry",
        "get_start_entries_by_race_id",
        "delete_start_entry",
        "get_all_starts_by_event",
    ],
    TimeEventsAdapter: [
        "create_time_event",
        "update_time_event",
        "delete_time_event",
        "get_time_event_by_id",
        "get_time_events_by_race_id",
        "get_time_events_by_event_id_and_timing_point",
    ],
    ContestantsAdapter: ["get_contestant_by_bib", "get_contestants_by_raceclass"],
    RaceclassResultsAdapter: [
        "get_raceclass_result",
        "delete_raceclass_result",
        "create_raceclass_results",
    ],
}


def patch_adapters(monkeypatch: pytest.MonkeyPatch, backend: FakeRaceBackend) -> None:
    """Let the adapters use the fake backend instead of the services."""
    for adapter, names in ADAPTER_METHODS.items():
        for name in names:
            fake = getattr(backend, name)

            async def method(self, *args, _fake=fake, **kwargs):  # noqa: ANN001, ANN002, ANN003, ANN202
                return await _fake(*args, **kwargs)

            monkeypatch.setattr(adapter, name, method)
    monkeypatch.setattr(EventsAdapter, "get_club_logo_url", lambda self, club: "")
    monkeypatch.setattr(
        EventsAdapter, "get_local_time", lambda self, event, fmt: "2026-11-16T09:00:00"
    )
