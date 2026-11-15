"""Module for raceclass results adapter."""

import logging

from event_service_gui.adapters import (
    ContestantsAdapter,
    EventsAdapter,
    RaceclassResultsAdapter,
    RaceplansAdapter,
)


class RaceclassResultsService:
    """Class representing raceclasses."""

    async def create_raceclass_results(
        self, token: str, event: dict, valgt_klasse: str
    ) -> int:
        """Create or recreate raceclass results function."""
        # generate new resultset first, so old results are kept if it fails
        if event["competition_format"] == "Interval Start":
            raceclass_result = await get_results_from_interval_start(
                token, event["id"], valgt_klasse
            )
        else:
            raceclass_result = await get_results_from_all_heats(
                token, event["id"], valgt_klasse
            )
        if not raceclass_result:
            informasjon = (
                f"Klassens resultat kan ikke lages - "
                f"A-finalen i {valgt_klasse} mangler resultater."
            )
            raise Exception(informasjon)

        # then delete any old results
        try:
            resultlist = await RaceclassResultsAdapter().get_raceclass_result(
                event["id"], valgt_klasse
            )
            if resultlist:
                res = await RaceclassResultsAdapter().delete_raceclass_result(
                    token, event["id"], valgt_klasse
                )
                logging.debug(
                    f"Deleted old results for raceclass {valgt_klasse} - {res}"
                )
        except Exception:
            logging.debug(f"No results found, no delete required {valgt_klasse}")

        # query contestant object to add ageclass
        contestants = await ContestantsAdapter().get_contestants_by_raceclass(
            token, event["id"], valgt_klasse
        )
        for racer in raceclass_result["ranking_sequence"]:
            for contestant in contestants:
                if contestant["bib"] == racer["bib"]:
                    racer["ageclass"] = contestant["ageclass"]
                    racer["minidrett_id"] = contestant["minidrett_id"]
                    break

        # and store to db
        return await RaceclassResultsAdapter().create_raceclass_results(
            token, event["id"], raceclass_result
        )

    def get_finish_rank_for_race(self, race: dict, indlude_dnf: bool) -> list:
        """Extract timing events from finish and append club logo."""
        finish_rank = []
        finish_bibs = []
        results = race["results"]
        if len(results) > 0:
            if "Finish" in results:
                finish_results = results["Finish"]
                if len(finish_results) > 0:
                    if "ranking_sequence" in finish_results:
                        finish_ranks = finish_results["ranking_sequence"]
                        for rank_event in finish_ranks:
                            if rank_event["status"] == "OK":
                                rank_event["club_logo"] = (
                                    EventsAdapter().get_club_logo_url(
                                        rank_event["club"]
                                    )
                                )
                                finish_rank.append(rank_event)
                                finish_bibs.append(rank_event["bib"])
        if indlude_dnf:
            for start in race["start_entries"]:
                if start["bib"] not in finish_bibs:
                    dnf_entry = {
                        "next_race_id": "",
                        "bib": start["bib"],
                        "rank": None,
                        "round": f"{race['round']}{race['index']}",
                        "name": start["name"],
                        "club": start["club"],
                        "club_logo": EventsAdapter().get_club_logo_url(start["club"]),
                        "ageclass": "",
                        "time_event": {},
                        "timing_point": "DNF",
                        "status": "DNF",
                    }
                    finish_rank.append(dnf_entry)
        return finish_rank


async def get_results_from_all_heats(
    token: str, event_id: str, valgt_klasse: str
) -> dict:
    """Get sprint results - return sorted list. With our without DNF."""
    results = {
        "event_id": event_id,
        "raceclass_name": valgt_klasse,
        "timing_point": "Finish",
        "no_of_contestants": 0,
        "ranking_sequence": [],
        "status": 1,
    }
    grouped_results = {
        "FA": [],
        "FB": [],
        "FB1": [],
        "FB2": [],
        "FB3": [],
        "SA": [],
        "FC": [],
        "FC1": [],
        "FC2": [],
        "FC3": [],
        "FC4": [],
        "SC": [],
        "DNF": [],
    }
    races = await RaceplansAdapter().get_races_by_racesclass(
        token, event_id, valgt_klasse
    )
    # first - extract all result-items
    for race in races:
        # need results for A final - exit if not
        if race["round"] == "F" and race["index"] == "A":
            if len(race["results"]) == 0:
                return {}
        # skip results from qualification
        if race["round"] != "Q":
            race_details = await RaceplansAdapter().get_race_by_id(token, race["id"])
            finish_results = RaceclassResultsService().get_finish_rank_for_race(
                race_details, indlude_dnf=True
            )
            for _tmp_result in finish_results:
                # skip results if racer has more races (race-service sends null)
                if not _tmp_result.get("next_race_id"):
                    new_result: dict = {
                        "bib": _tmp_result["bib"],
                        "round": f"{race['round']}{race['index']}",
                        "name": _tmp_result["name"],
                        "club": _tmp_result["club"],
                        "club_logo": _tmp_result["club_logo"],
                        "ageclass": "",
                        "minidrett_id": "",
                        "time_event": _tmp_result,
                    }
                    if _tmp_result["status"] == "DNF":
                        new_result["round"] = "DNF"
                        grouped_results["DNF"].append(new_result)
                    else:
                        grouped_results[f"{race['round']}{race['index']}"].append(
                            new_result
                        )

    # now - get the order and rank right.
    biblist = []
    already_ranked = 0
    racers_count = 0
    for round_res in grouped_results:
        for one_res in grouped_results[round_res]:
            if one_res["bib"] not in biblist:  # avoid duplicates, keep only best result
                if one_res["round"] != "DNF":
                    if one_res["round"].startswith("F"):
                        one_res["rank"] = already_ranked + one_res["time_event"]["rank"]
                    else:
                        one_res["rank"] = already_ranked + 1
                biblist.append(one_res["bib"])
                results["ranking_sequence"].append(one_res)
                racers_count += 1
        already_ranked = racers_count

    results["no_of_contestants"] = racers_count

    return results


async def get_results_from_interval_start(
    token: str, event_id: str, valgt_klasse: str
) -> dict:
    """Get interval start - return sorted list. With our without DNF."""
    racers_count = 0
    results = {
        "event_id": event_id,
        "raceclass_name": valgt_klasse,
        "timing_point": "Finish",
        "no_of_contestants": 0,
        "ranking_sequence": [],
        "status": 1,
    }
    races = await RaceplansAdapter().get_races_by_racesclass(
        token, event_id, valgt_klasse
    )

    # interval start - only one race
    if len(races) != 1:
        informasjon = "Error: Wrong number of races."
        raise Exception(informasjon)
    race = races[0]

    race_details = await RaceplansAdapter().get_race_by_id(token, race["id"])
    finish_results = RaceclassResultsService().get_finish_rank_for_race(
        race_details, indlude_dnf=True
    )
    for _tmp_result in finish_results:
        if _tmp_result["timing_point"] == "Finish":
            new_result: dict = {
                "bib": _tmp_result["bib"],
                "rank": f"{_tmp_result['rank']}",
                "round": f"{race['round']}",
                "name": _tmp_result["name"],
                "club": _tmp_result["club"],
                "club_logo": _tmp_result["club_logo"],
                "ageclass": "",
                "minidrett_id": "",
                "time_event": _tmp_result,
            }
            results["ranking_sequence"].append(new_result)
            racers_count += 1

    results["no_of_contestants"] = racers_count

    return results
