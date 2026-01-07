"""Module for time event service."""

import logging

from aiohttp import web

from event_service_gui.services import (
    ContestantsAdapter,
    EventsAdapter,
    RaceplansAdapter,
    StartAdapter,
    TimeEventsAdapter,
)
from event_service_gui.services.raceclasses_adapter import RaceclassesAdapter


class TimeEventsService:
    """Class representing service layer for time_events."""

    async def generate_next_race_templates(self, token: str, event: dict) -> str:
        """Calculate next race for the entire team."""
        informasjon = ""
        i = 0
        time_stamp_now = EventsAdapter().get_local_time(event, "log")
        time_event = {
            "bib": 0,
            "event_id": event["id"],
            "race": "",
            "race_id": "",
            "timing_point": "Template",
            "rank": 0,
            "registration_time": time_stamp_now,
            "next_race": "",
            "next_race_id": "",
            "next_race_position": 0,
            "status": "OK",
            "changelog": [],
        }
        # 1. delete all existing Template time events
        current_templates = (
            await TimeEventsAdapter().get_time_events_by_event_id_and_timing_point(
                token, event["id"], "Template"
            )
        )
        for template in current_templates:
            w_id = await TimeEventsAdapter().delete_time_event(token, template["id"])
            logging.debug(f"Deleted template time_event id {w_id}")

        # 2. get list of all races and loop, except finals.
        races = await RaceplansAdapter().get_all_races(token, event["id"])
        if len(races) == 0:
            informasjon = f"{informasjon} Ingen kjøreplaner funnet."
        else:
            for race in races:
                if race["round"] in ["Q", "S"]:
                    time_event["race"] = (
                        f"{race['raceclass']}-{race['round']}{race['index']}{race['heat']}"
                    )
                    time_event["race_id"] = race["id"]

                    # loop and simulate result for pos 1 to 10
                    for x in range(1, race["max_no_of_contestants"] + 1):
                        time_event["rank"] = x
                        next_start_entry = get_next_start_entry(
                            time_event, races
                        )
                        logging.debug(f"Time_event: {time_event}")
                        logging.debug(f"Start_entry: {next_start_entry}")
                        if len(next_start_entry) > 0:
                            time_event["next_race"] = next_start_entry["race_round"]
                            time_event["next_race_id"] = next_start_entry["race_id"]
                            time_event["next_race_position"] = next_start_entry[
                                "starting_position"
                            ]
                            new_t_e = await TimeEventsAdapter().create_time_event(
                                token, time_event
                            )
                            logging.debug(f"Created template: {new_t_e['status']}")
                            i += 1
        return f"Suksess! Opprettet {i} templates. "

    async def shuffle_semi_final_templates(self, token: str, event_id: str) -> str:
        """Shift right in semi finals for all contestants with given qarter_final."""
        informasjon = ""
        raceclasses = await RaceclassesAdapter().get_raceclasses(
            token, event_id
        )

        for raceclass in raceclasses:
            races = await RaceplansAdapter().get_races_by_racesclass(token, event_id, raceclass["name"])
            templates = await TimeEventsAdapter().get_time_events_by_event_id_and_timing_point(
                token, event_id, "Template"
            )
            count_of_quarter_finals = 0
            count_of_semi_finals_a = 0
            for race in races:
                if race["round"] == "S":
                    if race["index"] == "A":
                        count_of_semi_finals_a += 1
                if race["round"] == "Q":
                    count_of_quarter_finals += 1
            # if number of semi finals is half the number of quarter finals - we can shuffle
            if count_of_semi_finals_a == (count_of_quarter_finals // 2):
                informasjon += await self.shift_and_update_templates(
                    token, templates, raceclass["name"], 2
                )
                informasjon += await self.shift_and_update_templates(
                    token, templates, raceclass["name"], 3
                )
                informasjon += await self.shift_and_update_templates(
                    token, templates, raceclass["name"], 3
                )
                informasjon += await self.shift_and_update_templates(
                    token, templates, raceclass["name"], 4
                )
                informasjon += await self.shift_and_update_templates(
                    token, templates, raceclass["name"], 6
                )
                informasjon += await self.shift_and_update_templates(
                    token, templates, raceclass["name"], 8
                )
                informasjon += await self.shift_and_update_templates(
                    token, templates, raceclass["name"], 10
                )

        return informasjon

    async def shift_and_update_templates(
        self, token: str, templates: list, raceclass_name: str, race_position: int
    ) -> str:
        """Shuffle semi-final templates for given raceclass and position.

        Args:
            token: Authentication token
            templates: List of time event templates to filter and shift
            raceclass_name: Name of the raceclass (e.g., "G11")
            race_position: The rank/position to filter on (e.g., 2)

        Returns:
            Number of templates updated
        """
        updated_count = 0
        # get all template time events for semi finals A
        # filter out templates with specified position
        semi_final_templates = [
            template for template in templates
            if (f"{raceclass_name}-QA" in template["race"]) and (template["rank"] == race_position)
        ]
        # default - now shift right the fields next_race, next_race_id, next_race_position
        shifted_templates = shift_right_across_list_by(
            semi_final_templates,
            ["next_race", "next_race_id", "next_race_position"],
            shift=1
        )
        # update all shifted templates
        for shifted_template in shifted_templates:
            w_id = await TimeEventsAdapter().update_time_event(
                token, shifted_template["id"], shifted_template
            )
            updated_count += 1
            logging.debug(f"Updated template time_event id {w_id}")

        return f"{raceclass_name} {race_position} plass: {updated_count}, rotert. -- "


    async def create_start_time_event(self, token: str, time_event: dict) -> str:
        """Validate, enrich and create new start time_event."""
        # 1. First enrich data
        informasjon = ""
        if (time_event["timing_point"] == "Start") or (
            time_event["timing_point"] == "DNS"
        ):
            # just register start - nothing more to enrich
            pass
        else:
            raise web.HTTPBadRequest(
                reason=f"Error - expected start time event. {time_event}"
            )

        if len(time_event["id"]) > 0:
            # update existing time event
            w_id = await TimeEventsAdapter().update_time_event(
                token, time_event["id"], time_event
            )
            logging.debug(f"Updated time event: {time_event['bib']} - result: {w_id}")
            informasjon += f" Oppdatert startnr {time_event['bib']}. "
        else:
            new_t_e = await TimeEventsAdapter().create_time_event(token, time_event)
            informasjon += f" {new_t_e['bib']}: {new_t_e['status']}. "

        return informasjon

    async def create_finish_time_events(self, token: str, time_events: list) -> str:
        """Validate, enrich and create finish time_event."""
        # Get next race from template
        w_id = 0
        informasjon = ""
        next_start_entries = []
        start_list = []

        if len(time_events) > 0:
            next_start_entries = await TimeEventsAdapter().get_time_events_by_race_id(
                token, time_events[0]["race_id"]
            )
            start_list = await StartAdapter().get_all_starts_by_event(
                token, time_events[0]["event_id"]
            )
        for time_event in time_events:
            contestant = await ContestantsAdapter().get_contestant_by_bib(
                token, time_event["event_id"], time_event["bib"]
            )
            if not contestant:
                informasjon += (
                    f"<br> - ERROR! Bib {time_event['bib']}: Fant ingen deltaker. "
                )
            else:
                next_start_template = {}
                next_start_entry = {}
                for entry in next_start_entries:
                    if (entry["timing_point"] == "Template") and (
                        entry["rank"] == time_event["rank"]
                    ):
                        next_start_template = entry
                # Create or update time event
                if len(next_start_template) > 0:
                    time_event["next_race"] = next_start_template["next_race"]
                    time_event["next_race_id"] = next_start_template["next_race_id"]
                    time_event["next_race_position"] = next_start_template[
                        "next_race_position"
                    ]

                    next_race = await RaceplansAdapter().get_race_by_id(
                        token, time_event["next_race_id"]
                    )
                    # create next start entry
                    next_start_entry = {
                        "race_id": time_event["next_race_id"],
                        "startlist_id": start_list[0]["id"],
                        "bib": time_event["bib"],
                        "name": f"{contestant['first_name']} {contestant['last_name']}",
                        "club": contestant["club"],
                        "scheduled_start_time": next_race["start_time"],
                        "starting_position": time_event["next_race_position"],
                        "status": "OK",
                    }
                else:
                    time_event["next_race"] = "Ute"
                    time_event["next_race_id"] = ""
                # add name and club to time_event
                time_event["name"] = (
                    f"{contestant['first_name']} {contestant['last_name']}"
                )
                time_event["club"] = contestant["club"]
                result_ok = False
                if len(time_event["id"]) > 0:
                    # update existing time event
                    w_id = await TimeEventsAdapter().update_time_event(
                        token, time_event["id"], time_event
                    )
                    result_ok = True
                    informasjon += f" Updated time event {w_id}. "
                else:
                    new_t_e = await TimeEventsAdapter().create_time_event(
                        token, time_event
                    )
                    if new_t_e["status"] == "OK":
                        informasjon += f"{new_t_e['bib']}: {new_t_e['rank']} pl. "
                        result_ok = True
                    # error, return info to user
                    elif new_t_e["changelog"]:
                        informasjon += f"{new_t_e['changelog'][-1]['comment']} <br>"
                if time_event["next_race"] != "Ute" and result_ok:
                    await StartAdapter().create_start_entry(
                        token, next_start_entry
                    )

        return informasjon


def shift_right_across_list_by(data: list[dict], keys: list[str], shift: int = 1) -> list[dict]:
    """Shift values to the right by N positions across list items for specified keys.

    Args:
        data: List of dictionaries to process
        keys: List of keys whose values should be shifted across items
        shift: Number of positions to shift (default: 1)

    Returns:
        New list of dictionaries with shifted values
    """
    if len(data) == 0:
        return []

    result = [item.copy() for item in data]

    for key in keys:
        for i in range(len(data)):
            result[i][key] = data[(i - shift) % len(data)][key]

    return result


def get_next_start_entry(time_event: dict, races: list) -> dict:
    """Generate start_entry - empty result if not qualified."""
    start_entry = {}

    # find relevant race and get next race rule
    next_race = populate_next_race(time_event, races, next_race_template())

    # interpret rule part 2 - find next round and get race id
    ilimitplace = 0
    ilimitcurrent = 0
    for race_item in next_race:
        try:
            ilimitcurrent = race_item["qualified"]
            limit_rank = ilimitcurrent + ilimitplace
        except Exception:
            # if error assume all remaining racers are qualified
            limit_rank = 99
        if time_event["rank"] <= limit_rank:
            race_item["current_contestant_qualified"] = True
            # now we have next round - get race id
            time_event["rank_qualified"] = time_event["rank"] - ilimitplace
            start_entry = calculate_next_start_entry(
                race_item, time_event, races
            )
            break
        ilimitplace = limit_rank
    return start_entry


def calculate_next_start_entry(
    race_item: dict, time_event: dict, races: list
) -> dict:
    """Identify next race_id and generate start entry data."""
    start_entry = {
        "bib": time_event["bib"],
        "race_id": "",
        "race_round": "",
        "scheduled_start_time": "",
        "starting_position": time_event["rank_qualified"],
    }
    previous_race = {}
    previous_heat_count = 0
    next_race_candidates = []
    next_race_count = 0
    # 1. Get previous race and all possible next race candidates
    for race in races:
        if race.get("id") == time_event.get("race_id"):
            previous_race = race
            previous_heat_count = race.get("heat")
        elif (
            len(previous_race) > 0
            and previous_race.get("round") == race.get("round")
            and previous_race.get("index") == race.get("index")
            and previous_race.get("raceclass") == race.get("raceclass")
        ):
            previous_heat_count = race.get("heat")
        elif f"{race.get('round')}{race.get('index')}" == race_item["round"]:
            if previous_race.get("raceclass") == race.get("raceclass"):
                next_race_candidates.append(race)

    # 2. pick a next race
    next_race_count = len(next_race_candidates)
    if next_race_count > 0:
        # estimated rank from previous round is:
        previous_heat_rank = time_event["rank_qualified"]
        previous_heat_number = int(previous_race["heat"])
        previous_round_rank = (
            previous_heat_count * (previous_heat_rank - 1) + previous_heat_number
        )

        # distribute contestants evenly in next round, winners in pos 1 osv.
        next_race_tuple = divmod(
            previous_round_rank + (next_race_count - 1), next_race_count
        )
        # quotient gives the position
        next_race_position = next_race_tuple[0]
        # remainder gives the heat, need to add one as heat number starts on 1
        next_race_heat = next_race_tuple[1] + 1

        for race in next_race_candidates:
            if race.get("heat") == next_race_heat:
                logging.debug(f"Found next race: {race}")
                start_entry["race_id"] = race.get("id")
                start_entry["scheduled_start_time"] = race.get("start_time")
                if race.get("round") == "F":
                    start_entry["race_round"] = (
                        f"{race.get('round')}{race.get('index')}"
                    )
                else:
                    start_entry["race_round"] = (
                        f"{race.get('round')}{race.get('index')}{race.get('heat')}"
                    )
        start_entry["starting_position"] = next_race_position

        logging.debug(
            f"Next round:{next_race_count} current rank:{previous_round_rank}"
        )
        logging.debug(
            f"Next:{next_race_heat} pos:{next_race_position}, id: {start_entry['race_id']}"
        )
    return start_entry


def populate_next_race(time_event: dict, races: list, next_race: list) -> list:
    """Return rules matrix for next race."""
    for race in races:
        if race["id"] == time_event["race_id"]:
            for key, value in race["rule"].items():
                if key == "S":
                    for x, y in value.items():
                        if x == "A":
                            next_race[0]["qualified"] = y
                        elif x == "C":
                            next_race[1]["qualified"] = y
                elif key == "F":
                    for x, y in value.items():
                        if x == "A":
                            next_race[2]["qualified"] = y
                        elif x == "B":
                            next_race[3]["qualified"] = y
                        elif x == "B1":
                            next_race[4]["qualified"] = y
                        elif x == "B2":
                            next_race[5]["qualified"] = y
                        elif x == "B3":
                            next_race[6]["qualified"] = y
                        elif x == "C":
                            next_race[7]["qualified"] = y
                        elif x == "C1":
                            next_race[8]["qualified"] = y
                        elif x == "C2":
                            next_race[9]["qualified"] = y
                        elif x == "C3":
                            next_race[10]["qualified"] = y
                        elif x == "C4":
                            next_race[11]["qualified"] = y
    return next_race


def next_race_template() -> list:
    """Return template settings for next race."""
    return [
        {
            "round": "SA",
            "qualified": 0,
            "current_contestant_qualified": False,
        },
        {
            "round": "SC",
            "qualified": 0,
            "current_contestant_qualified": False,
        },
        {
            "round": "FA",
            "qualified": 0,
            "current_contestant_qualified": False,
        },
        {
            "round": "FB",
            "qualified": 0,
            "current_contestant_qualified": False,
        },
        {
            "round": "FB1",
            "qualified": 0,
            "current_contestant_qualified": False,
        },
        {
            "round": "FB2",
            "qualified": 0,
            "current_contestant_qualified": False,
        },
        {
            "round": "FB3",
            "qualified": 0,
            "current_contestant_qualified": False,
        },
        {
            "round": "FC",
            "qualified": 0,
            "current_contestant_qualified": False,
        },
        {
            "round": "FC1",
            "qualified": 0,
            "current_contestant_qualified": False,
        },
        {
            "round": "FC2",
            "qualified": 0,
            "current_contestant_qualified": False,
        },
        {
            "round": "FC3",
            "qualified": 0,
            "current_contestant_qualified": False,
        },
        {
            "round": "FC4",
            "qualified": 0,
            "current_contestant_qualified": False,
        },
    ]
