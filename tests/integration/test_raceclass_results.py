"""Integration test cases for the results of a raceclass.

For sprint, the result list is made from the heats where each contestant
ended: final A first, then final B, those out in semi final A, final C, those
out in semi final C, and last those who did not finish (DNF). For interval
start, it is the finish order of the one race.
"""

import pytest

from event_service_gui.services import RaceclassResultsService
from event_service_gui.services.raceclass_result_service import (
    get_results_from_all_heats,
)

from .fake_race_backend import (
    EVENT_ID,
    RACECLASS,
    FakeRaceBackend,
    make_races,
    patch_adapters,
)

SPRINT = {"id": EVENT_ID, "competition_format": "Individual Sprint"}
INTERVAL = {"id": EVENT_ID, "competition_format": "Interval Start"}


def race_id(name: str) -> str:
    return f"{RACECLASS}-{name}"


def ranked(bibs: list[int], next_race: str | None = None) -> list[dict]:
    """Return finish results for bibs in this order, going on to next_race."""
    return [
        {"bib": bib, "rank": rank, "next_race_id": next_race and race_id(next_race)}
        for rank, bib in enumerate(bibs, 1)
    ]


def ranking(results: dict) -> list[tuple]:
    return [(r["bib"], r.get("rank"), r["round"]) for r in results["ranking_sequence"]]


@pytest.fixture
def backend(monkeypatch: pytest.MonkeyPatch) -> FakeRaceBackend:
    backend = FakeRaceBackend()
    patch_adapters(monkeypatch, backend)
    return backend


@pytest.fixture
def finished_sprint(backend: FakeRaceBackend) -> FakeRaceBackend:
    """Semi finals and finals with results; bibs 7 and 36 did not finish.

    Semi final A: 1-7 and 11-14, all on to final A or B.
    Semi final C: 31-36; 31-33 on to final C, 34 and 35 out, 36 DNF.
    Final A: 1-6, and 7 did not finish. Final B: 11-14. Final C: 31-33.
    """
    starts = {
        "SA1": [1, 3, 5, 7, 11, 13],
        "SA2": [2, 4, 6, 12, 14],
        "SC1": [31, 33, 34],
        "SC2": [32, 35, 36],
        "FA": [1, 2, 3, 4, 5, 6, 7],
        "FB": [11, 12, 13, 14],
        "FC": [31, 32, 33],
    }
    for race, bibs in starts.items():
        for position, bib in enumerate(bibs, 1):
            backend.add_start(race_id(race), bib, position)
    for bib in {bib for bibs in starts.values() for bib in bibs}:
        backend.add_contestant(bib)
    # the quarter finals are not used for the result list
    backend.set_results(race_id("QA1"), ranked([1, 2, 3], "SA1"))
    backend.set_results(
        race_id("SA1"), ranked([1, 3, 5], "FA") + ranked([7, 11, 13], "FB")
    )
    for result in backend.races[race_id("SA1")]["results"]["Finish"][
        "ranking_sequence"
    ]:
        if result["bib"] == 7:
            result["next_race_id"] = race_id("FA")  # 7 was moved up to final A
    backend.set_results(
        race_id("SA2"), ranked([2, 4, 6], "FA") + ranked([12, 14], "FB")
    )
    backend.set_results(race_id("SC1"), ranked([31, 33], "FC") + ranked([34]))
    backend.set_results(race_id("SC2"), ranked([32], "FC") + ranked([35]))
    backend.set_results(race_id("FA"), ranked([1, 2, 3, 4, 5, 6]))
    backend.set_results(race_id("FB"), ranked([11, 12, 13, 14]))
    backend.set_results(race_id("FC"), ranked([31, 32, 33]))
    return backend


# --- Results of one race -------------------------------------------------------------


@pytest.mark.integration
def test_finish_rank_has_only_ok_results() -> None:
    race = {
        "round": "F",
        "index": "A",
        "results": {
            "Finish": {
                "ranking_sequence": [
                    {"bib": 1, "rank": 1, "status": "OK", "club": "Lyn"},
                    {"bib": 2, "rank": 2, "status": "Error", "club": "Lyn"},
                ]
            }
        },
        "start_entries": [
            {"bib": 1, "name": "A", "club": "Lyn"},
            {"bib": 2, "name": "B", "club": "Lyn"},
        ],
    }
    service = RaceclassResultsService()

    assert [
        r["bib"] for r in service.get_finish_rank_for_race(race, indlude_dnf=False)
    ] == [1]
    with_dnf = service.get_finish_rank_for_race(race, indlude_dnf=True)
    assert [(r["bib"], r["status"]) for r in with_dnf] == [(1, "OK"), (2, "DNF")]
    assert with_dnf[1]["round"] == "FA"


@pytest.mark.integration
def test_finish_rank_without_results_is_all_dnf() -> None:
    race = {
        "round": "F",
        "index": "A",
        "results": {},
        "start_entries": [{"bib": 1, "name": "A", "club": "Lyn"}],
    }
    service = RaceclassResultsService()
    assert service.get_finish_rank_for_race(race, indlude_dnf=False) == []
    assert [
        r["status"] for r in service.get_finish_rank_for_race(race, indlude_dnf=True)
    ] == ["DNF"]


# --- Sprint ------------------------------------------------------------------------


@pytest.mark.integration
async def test_sprint_ranking_follows_the_heats(
    finished_sprint: FakeRaceBackend,
) -> None:
    results = await get_results_from_all_heats("t", EVENT_ID, RACECLASS)

    assert ranking(results) == [
        # final A: the place in the final
        (1, 1, "FA"), (2, 2, "FA"), (3, 3, "FA"), (4, 4, "FA"), (5, 5, "FA"), (6, 6, "FA"),
        # final B: after final A
        (11, 7, "FB"), (12, 8, "FB"), (13, 9, "FB"), (14, 10, "FB"),
        # final C: after final B
        (31, 11, "FC"), (32, 12, "FC"), (33, 13, "FC"),
        # out in semi final C: share the next place (see #233)
        (34, 14, "SC"), (35, 14, "SC"),
        # did not finish: last, without place, in race order (see #234)
        (36, None, "DNF"), (7, None, "DNF"),
    ]  # fmt: skip
    assert results["no_of_contestants"] == 17
    assert results["raceclass_name"] == RACECLASS
    assert results["ranking_sequence"][0]["time_event"]["rank"] == 1


@pytest.mark.integration
async def test_sprint_without_final_a_results_gives_no_ranking(
    finished_sprint: FakeRaceBackend,
) -> None:
    finished_sprint.set_results(race_id("FA"), [])
    assert await get_results_from_all_heats("t", EVENT_ID, RACECLASS) == {}


@pytest.mark.integration
async def test_create_results_replaces_old_and_adds_ageclass(
    finished_sprint: FakeRaceBackend,
) -> None:
    backend = finished_sprint
    backend.raceclass_results[RACECLASS] = {"raceclass_name": RACECLASS, "old": True}

    await RaceclassResultsService().create_raceclass_results("t", SPRINT, RACECLASS)

    assert backend.deleted_raceclass_results == [RACECLASS]
    stored = backend.raceclass_results[RACECLASS]
    assert "old" not in stored
    first = stored["ranking_sequence"][0]
    assert (first["bib"], first["ageclass"], first["minidrett_id"]) == (
        1,
        "G12 år",
        "m1",
    )


@pytest.mark.integration
async def test_create_results_keeps_old_results_if_final_a_is_missing(
    finished_sprint: FakeRaceBackend,
) -> None:
    backend = finished_sprint
    old = {"raceclass_name": RACECLASS, "old": True}
    backend.raceclass_results[RACECLASS] = old
    backend.set_results(race_id("FA"), [])

    with pytest.raises(Exception, match=f"A-finalen i {RACECLASS} mangler resultater"):
        await RaceclassResultsService().create_raceclass_results("t", SPRINT, RACECLASS)

    assert backend.raceclass_results[RACECLASS] is old
    assert backend.deleted_raceclass_results == []


# --- Interval start ---------------------------------------------------------------


def interval_backend(
    monkeypatch: pytest.MonkeyPatch, no_of_races: int
) -> FakeRaceBackend:
    plan = {
        "no_of_heats": {"R1": {"A": no_of_races}},
        "from_to": {},
        "max_no_of_contestants": {"R1": 50},
    }
    backend = FakeRaceBackend(make_races(plan))
    patch_adapters(monkeypatch, backend)
    return backend


@pytest.mark.integration
async def test_interval_start_ranking_is_finish_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = interval_backend(monkeypatch, 1)
    [race] = backend.races
    for position, bib in enumerate([5, 6, 7], 1):
        backend.add_start(race, bib, position)
        backend.add_contestant(bib)
    backend.set_results(race, ranked([6, 5]))

    await RaceclassResultsService().create_raceclass_results("t", INTERVAL, RACECLASS)

    stored = backend.raceclass_results[RACECLASS]
    # 7 did not finish and is not in the list; the place is a number, as for sprint
    assert ranking(stored) == [(6, 1, "R1"), (5, 2, "R1")]
    assert stored["no_of_contestants"] == 2


@pytest.mark.integration
async def test_interval_start_needs_exactly_one_race(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    interval_backend(monkeypatch, 2)
    with pytest.raises(Exception, match="nøyaktig ett heat"):
        await RaceclassResultsService().create_raceclass_results(
            "t", INTERVAL, RACECLASS
        )
