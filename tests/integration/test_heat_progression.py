"""Integration test cases for progression from one heat to the next.

Before the race, generate_next_race_templates makes a Template time event for
each place in each quarter and semi final heat: which heat and position that
place goes on to. When a finish is registered, the template for its place
gives the next heat, and a start is created there.

The plan is Individual Sprint for 24 contestants: 4 quarter finals of 6, top 3
to semi final A (2 heats), the rest to semi final C (2 heats); top 3 in SA to
final A, the rest to final B; top 3 in SC to final C, the rest are out.
"""

from collections import Counter

import pytest

from event_service_gui.services import TimeEventsService
from event_service_gui.services.time_events_service import create_finish_time_event

from .fake_race_backend import (
    EVENT_ID,
    RACECLASS,
    FakeRaceBackend,
    patch_adapters,
)

EVENT = {"id": EVENT_ID, "name": "Test", "timezone": "Europe/Oslo"}
USER = {"token": "t", "name": "tester"}


def race_id(name: str) -> str:
    return f"{RACECLASS}-{name}"


@pytest.fixture
def backend(monkeypatch: pytest.MonkeyPatch) -> FakeRaceBackend:
    backend = FakeRaceBackend()
    patch_adapters(monkeypatch, backend)
    return backend


async def templates_by_place(backend: FakeRaceBackend) -> dict[tuple[str, int], tuple]:
    """Return {(race, place): (next race, position)} for all templates."""
    return {
        (t["race"].split("-")[1], t["rank"]): (t["next_race"], t["next_race_position"])
        for t in backend.templates()
    }


# --- Templates ------------------------------------------------------------------


@pytest.mark.integration
async def test_templates_follow_the_qualification_rules(
    backend: FakeRaceBackend,
) -> None:
    informasjon = await TimeEventsService().generate_next_race_templates("t", EVENT)
    places = await templates_by_place(backend)

    for heat in range(1, 5):
        # top 3 in each quarter final to semi final A, the rest to C
        assert [places[(f"QA{heat}", rank)][0][:2] for rank in range(1, 7)] == [
            "SA", "SA", "SA", "SC", "SC", "SC"
        ]  # fmt: skip
    for heat in (1, 2):
        # top 3 in semi final A to final A, the rest to B
        assert [places[(f"SA{heat}", rank)][0] for rank in range(1, 9)] == [
            "FA", "FA", "FA", "FB", "FB", "FB", "FB", "FB"
        ]  # fmt: skip
        # top 3 in semi final C to final C, the rest are out: no template
        assert [places.get((f"SC{heat}", rank)) for rank in range(4, 9)] == [None] * 5
        assert {places[(f"SC{heat}", rank)][0] for rank in range(1, 4)} == {"FC"}
    assert informasjon == f"Suksess! Opprettet {len(backend.templates())} templates. "


@pytest.mark.integration
async def test_templates_give_each_position_in_the_next_heat_once(
    backend: FakeRaceBackend,
) -> None:
    await TimeEventsService().generate_next_race_templates("t", EVENT)

    positions: dict[str, list[int]] = {}
    for template in backend.templates():
        assert template["next_race_id"] == race_id(template["next_race"])
        positions.setdefault(template["next_race"], []).append(
            template["next_race_position"]
        )
    assert {race: sorted(p) for race, p in positions.items()} == {
        "SA1": [1, 2, 3, 4, 5, 6],
        "SA2": [1, 2, 3, 4, 5, 6],
        "SC1": [1, 2, 3, 4, 5, 6],
        "SC2": [1, 2, 3, 4, 5, 6],
        "FA": [1, 2, 3, 4, 5, 6],
        "FB": list(range(1, 11)),
        "FC": [1, 2, 3, 4, 5, 6],
    }


@pytest.mark.integration
async def test_winners_are_spread_over_the_next_heats(
    backend: FakeRaceBackend,
) -> None:
    """Winners get the first positions, and the heats get the same number."""
    await TimeEventsService().generate_next_race_templates("t", EVENT)
    places = await templates_by_place(backend)

    assert [places[(f"QA{heat}", 1)] for heat in range(1, 5)] == [
        ("SA1", 1), ("SA2", 1), ("SA1", 2), ("SA2", 2)
    ]  # fmt: skip
    assert [places[(f"QA{heat}", 2)] for heat in range(1, 5)] == [
        ("SA1", 3), ("SA2", 3), ("SA1", 4), ("SA2", 4)
    ]  # fmt: skip
    # the best losers in semi final C get the first positions in final C
    assert [places[(f"SC{heat}", 1)] for heat in (1, 2)] == [("FC", 1), ("FC", 2)]
    # 4th in semi final A is the first in final B
    assert [places[(f"SA{heat}", 4)] for heat in (1, 2)] == [("FB", 1), ("FB", 2)]


@pytest.mark.integration
async def test_generating_again_replaces_the_templates(
    backend: FakeRaceBackend,
) -> None:
    await TimeEventsService().generate_next_race_templates("t", EVENT)
    first = len(backend.templates())
    await TimeEventsService().generate_next_race_templates("t", EVENT)
    assert len(backend.templates()) == first


@pytest.mark.integration
async def test_rotating_semi_final_templates_keeps_every_position(
    backend: FakeRaceBackend,
) -> None:
    """Roter plasser til semi-heat: the places change, the positions stay."""
    await TimeEventsService().generate_next_race_templates("t", EVENT)
    before = await templates_by_place(backend)

    await TimeEventsService().shuffle_semi_final_templates("t", EVENT_ID)
    after = await templates_by_place(backend)

    targets = Counter(
        after[(f"QA{heat}", rank)] for heat in range(1, 5) for rank in range(1, 7)
    )
    assert targets == Counter(
        before[(f"QA{heat}", rank)] for heat in range(1, 5) for rank in range(1, 7)
    )
    assert max(targets.values()) == 1
    # winners stay; 2nd place is shifted one heat to the right
    assert [after[(f"QA{heat}", 1)] for heat in range(1, 5)] == [
        before[(f"QA{heat}", 1)] for heat in range(1, 5)
    ]
    assert [after[(f"QA{heat}", 2)] for heat in range(1, 5)] == [
        before[("QA4", 2)], before[("QA1", 2)], before[("QA2", 2)], before[("QA3", 2)]
    ]  # fmt: skip
    # the semi final templates are not rotated
    assert {k: v for k, v in after.items() if k[0].startswith("S")} == {
        k: v for k, v in before.items() if k[0].startswith("S")
    }


# --- Registering finish ------------------------------------------------------------


def finish(race: str, bib: int, rank: int) -> dict:
    """Return a finish time event as resultat_edit_new sends it."""
    return {
        "id": "",
        "bib": bib,
        "event_id": EVENT_ID,
        "race": f"{RACECLASS}-{race}",
        "race_id": race_id(race),
        "timing_point": "Finish",
        "rank": rank,
        "registration_time": "2026-11-16T09:10:00",
        "next_race": "",
        "next_race_id": "",
        "next_race_position": 0,
        "status": "OK",
        "changelog": [],
    }


@pytest.fixture
async def quarter_final_1(backend: FakeRaceBackend) -> FakeRaceBackend:
    """Templates generated, and bibs 1-6 start in quarter final 1."""
    await TimeEventsService().generate_next_race_templates("t", EVENT)
    for bib in range(1, 7):
        backend.add_contestant(bib)
        backend.add_start(race_id("QA1"), bib, bib)
    return backend


@pytest.mark.integration
async def test_finish_creates_start_in_next_heat(
    quarter_final_1: FakeRaceBackend,
) -> None:
    backend = quarter_final_1
    # bib 6 wins, bib 1 is last
    results = [finish("QA1", bib, rank) for rank, bib in enumerate(range(6, 0, -1), 1)]

    informasjon = await TimeEventsService().update_finish_time_events(USER, [], results)

    assert backend.starts(race_id("SA1")) == [(1, 6), (3, 5), (5, 4)]
    assert backend.starts(race_id("SC1")) == [(1, 3), (3, 2), (5, 1)]
    finishes = {
        t["bib"]: t for t in backend.time_events if t["timing_point"] == "Finish"
    }
    assert (finishes[6]["next_race"], finishes[6]["next_race_position"]) == ("SA1", 1)
    assert finishes[6]["next_race_id"] == race_id("SA1")
    assert finishes[6]["name"] == "Løper 6"
    assert informasjon.startswith("6: 1 pl. 5: 2 pl.")


@pytest.mark.integration
async def test_finish_in_final_is_out(backend: FakeRaceBackend) -> None:
    await TimeEventsService().generate_next_race_templates("t", EVENT)
    backend.add_contestant(7)
    backend.add_start(race_id("FA"), 7, 1)

    await TimeEventsService().update_finish_time_events(USER, [], [finish("FA", 7, 1)])

    [time_event] = [t for t in backend.time_events if t["timing_point"] == "Finish"]
    assert (time_event["next_race"], time_event["next_race_id"]) == ("Ute", "")


@pytest.mark.integration
async def test_finish_for_unknown_bib_is_not_saved(
    quarter_final_1: FakeRaceBackend,
) -> None:
    informasjon = await TimeEventsService().update_finish_time_events(
        USER, [], [finish("QA1", 99, 1)]
    )
    assert "Bib 99: Fant ingen deltaker" in informasjon
    assert [
        t for t in quarter_final_1.time_events if t["timing_point"] == "Finish"
    ] == []


@pytest.mark.integration
async def test_finish_with_error_status_gives_no_next_start(
    quarter_final_1: FakeRaceBackend,
) -> None:
    """race-service gives status Error, e.g. for a bib not in the start list."""
    backend = quarter_final_1
    backend.add_contestant(50)

    informasjon = await TimeEventsService().update_finish_time_events(
        USER, [], [finish("QA1", 50, 1)]
    )

    assert "Bib 50 er ikke i startlisten." in informasjon
    assert backend.starts(race_id("SA1")) == []


@pytest.mark.integration
async def test_second_finish_for_same_bib_is_explained(
    quarter_final_1: FakeRaceBackend,
) -> None:
    backend = quarter_final_1
    await TimeEventsService().update_finish_time_events(USER, [], [finish("QA1", 1, 1)])

    informasjon = await TimeEventsService().update_finish_time_events(
        USER, [], [finish("QA1", 1, 2)]
    )

    assert informasjon == f"ERROR: Bib 1 er allerede registrert i {RACECLASS}-QA1. "
    assert backend.starts(race_id("SA1")) == [(1, 1)]


@pytest.mark.integration
async def test_blocking_error_finish_is_explained(
    quarter_final_1: FakeRaceBackend,
) -> None:
    """A finish with status Error blocks a new one until it is deleted."""
    backend = quarter_final_1
    backend.add_contestant(50)
    await TimeEventsService().update_finish_time_events(
        USER, [], [finish("QA1", 50, 1)]
    )
    backend.add_start(race_id("QA1"), 50, 7)

    informasjon = await TimeEventsService().update_finish_time_events(
        USER, [], [finish("QA1", 50, 1)]
    )

    assert informasjon.startswith(
        f"ERROR: Bib 50 har allerede en passering i {RACECLASS}-QA1 med status Error"
    )
    assert "Årsak: Bib 50 er ikke i startlisten." in informasjon
    assert "Slett den under Kontroll" in informasjon


# --- Deleting results -----------------------------------------------------------------


@pytest.mark.integration
async def test_deleting_result_deletes_start_in_next_heat(
    quarter_final_1: FakeRaceBackend,
) -> None:
    backend = quarter_final_1
    await TimeEventsService().update_finish_time_events(
        USER, [], [finish("QA1", 1, 1), finish("QA1", 2, 2)]
    )
    [first] = [t for t in backend.time_events if t["bib"] == 1]

    informasjon = await TimeEventsService().update_finish_time_events(
        USER, [first["id"]], []
    )

    assert informasjon == "Slettet passering (1). Slettet neste start (1). "
    assert backend.starts(race_id("SA1")) == [(3, 2)]
    assert first not in backend.time_events


@pytest.mark.integration
async def test_deleting_result_twice_says_so(quarter_final_1: FakeRaceBackend) -> None:
    await TimeEventsService().update_finish_time_events(USER, [], [finish("QA1", 1, 1)])
    [first] = [t for t in quarter_final_1.time_events if t["bib"] == 1]
    await TimeEventsService().update_finish_time_events(USER, [first["id"]], [])

    informasjon = await TimeEventsService().update_finish_time_events(
        USER, [first["id"]], []
    )

    assert informasjon == "Time event allerede slettet."


@pytest.mark.integration
async def test_correcting_result_moves_the_next_start(
    quarter_final_1: FakeRaceBackend,
) -> None:
    """Delete and register again, as resultat_edit_new does when a place changes."""
    backend = quarter_final_1
    await TimeEventsService().update_finish_time_events(
        USER, [], [finish("QA1", 1, 1), finish("QA1", 2, 2)]
    )
    ids = [t["id"] for t in backend.time_events if t["timing_point"] == "Finish"]

    await TimeEventsService().update_finish_time_events(
        USER, ids, [finish("QA1", 2, 1), finish("QA1", 1, 2)]
    )

    assert backend.starts(race_id("SA1")) == [(1, 2), (3, 1)]


# --- Expired login while saving ------------------------------------------------------

LOGIN_401 = Exception("create_time_event failed - 401-Unauthorized")


@pytest.mark.integration
@pytest.mark.parametrize(
    ("method", "error"),
    [
        ("create_time_event", LOGIN_401),
        ("create_start_entry", Exception("Error - 401: Unauthorized.")),
    ],
)
async def test_expired_login_when_saving_finish_is_raised(
    quarter_final_1: FakeRaceBackend,
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    error: Exception,
) -> None:
    """Not turned into "ERROR: …", so the view sends the user to log in."""

    async def fail(*_: object, **__: object) -> None:
        raise error

    monkeypatch.setattr(quarter_final_1, method, fail)
    with pytest.raises(Exception, match="401"):
        await TimeEventsService().update_finish_time_events(
            USER, [], [finish("QA1", 1, 1)]
        )


@pytest.mark.integration
async def test_expired_login_when_explaining_duplicate_is_raised(
    quarter_final_1: FakeRaceBackend, monkeypatch: pytest.MonkeyPatch
) -> None:
    backend = quarter_final_1
    await TimeEventsService().update_finish_time_events(USER, [], [finish("QA1", 1, 1)])

    async def fail(*_: object, **__: object) -> None:
        raise LOGIN_401

    monkeypatch.setattr(backend, "get_time_events_by_race_id", fail)
    with pytest.raises(Exception, match="401"):
        # update_finish_time_events reads the race's time events first
        await create_finish_time_event("t", finish("QA1", 1, 2), [], "startlist-1")


@pytest.mark.integration
@pytest.mark.parametrize("method", ["get_time_event_by_id", "delete_time_event"])
async def test_expired_login_when_deleting_result_is_raised(
    quarter_final_1: FakeRaceBackend, monkeypatch: pytest.MonkeyPatch, method: str
) -> None:
    """Not reported as "Time event allerede slettet"."""
    backend = quarter_final_1
    await TimeEventsService().update_finish_time_events(USER, [], [finish("QA1", 1, 1)])
    [first] = [t for t in backend.time_events if t["bib"] == 1]

    async def fail(*_: object, **__: object) -> None:
        raise LOGIN_401

    monkeypatch.setattr(backend, method, fail)
    with pytest.raises(Exception, match="401"):
        await TimeEventsService().update_finish_time_events(USER, [first["id"]], [])


@pytest.mark.integration
async def test_duplicate_message_is_plain_text(
    quarter_final_1: FakeRaceBackend,
) -> None:
    """The pages escape it; escaped here too, it showed "&#x27;" for "'"."""
    backend = quarter_final_1
    backend.add_contestant(50)
    await TimeEventsService().update_finish_time_events(
        USER, [], [finish("QA1", 50, 1)]
    )
    [blocking] = [t for t in backend.time_events if t["bib"] == 50]
    blocking["changelog"] = [{"comment": "Bib 50 er ikke i 'startlisten' & <A>."}]

    informasjon = await TimeEventsService().update_finish_time_events(
        USER, [], [finish("QA1", 50, 1)]
    )

    assert "Årsak: Bib 50 er ikke i 'startlisten' & <A>." in informasjon
