"""Utilities module for gui services."""

import datetime
import logging

from aiohttp import web
from aiohttp_session import get_session

from event_service_gui.services import (
    CompetitionFormatAdapter,
    ContestantsAdapter,
    EventsAdapter,
    RaceclassesAdapter,
    RaceplansAdapter,
    StartAdapter,
    TimeEventsAdapter,
    UserAdapter,
)


async def check_login(self) -> dict:
    """Check login and return user credentials."""
    session = await get_session(self.request)
    loggedin = UserAdapter().isloggedin(session)
    if not loggedin:
        informasjon = "Logg inn for å se denne siden"
        raise web.HTTPSeeOther(location=f"/login?informasjon={informasjon}")

    return {
        "name": session["name"],
        "loggedin": True,
        "token": session["token"],
    }


async def check_login_open(self) -> dict:
    """Check login and return credentials."""
    user = {}
    session = await get_session(self.request)
    loggedin = UserAdapter().isloggedin(session)
    if loggedin:
        user = {
            "name": session["name"],
            "loggedin": True,
            "token": session["token"],
        }
    else:
        user = {"name": "Gjest", "loggedin": False, "token": ""}

    return user


async def create_default_competition_format(token: str, format_name: str) -> str:
    """Create default competition formats."""
    request_body = CompetitionFormatAdapter().get_default_competition_format(
        format_name
    )
    return await CompetitionFormatAdapter().create_competition_format(
        token, request_body
    )


def get_display_style(start_time: str, event: dict) -> str:
    """Calculate time remaining to start and return table header style."""
    time_now = EventsAdapter().get_local_datetime_now(event)
    start_time_obj = datetime.datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S")
    # make sure timezone is correct
    start_time_obj = start_time_obj.replace(tzinfo=time_now.tzinfo)
    delta_time = start_time_obj - time_now
    delta_seconds = delta_time.total_seconds()
    display_style = ""
    if delta_seconds < 300:
        display_style = "table_header_red"
    elif delta_seconds < 600:
        display_style = "table_header_orange"
    else:
        display_style = "table_header_green"

    return display_style


async def get_enrichced_startlist(user: dict, race: dict) -> list:
    """Enrich startlist information - including info if race result is registered."""
    startlist = []
    i = 0
    # get time-events registered
    next_race_time_events = await TimeEventsAdapter().get_time_events_by_race_id(
        user["token"], race["id"]
    )
    new_start_entries = race["start_entries"]
    if len(new_start_entries) > 0:
        for start_entry in new_start_entries:
            start_entry["club_logo"] = EventsAdapter().get_club_logo_url(
                start_entry["club"]
            )
            i += 1
            for time_event in next_race_time_events:
                # get next race info
                if time_event["timing_point"] == "Template":
                    logging.debug(f"Time_event with error - {time_event}")
                elif time_event["timing_point"] == "Template":
                    if i == time_event["rank"]:
                        if time_event["next_race"].startswith("Ute"):
                            start_entry["next_race"] = "Ute"
                        else:
                            start_entry["next_race"] = time_event["next_race"]
                # check if start or DNS is registered
                elif time_event["timing_point"] == "Start":
                    if time_event["bib"] == start_entry["bib"]:
                        start_entry["start_status"] = "Started"
                        start_entry["info"] = (
                            f"Started registered at {time_event['registration_time']}"
                        )
                elif time_event["timing_point"] == "DNS":
                    if time_event["bib"] == start_entry["bib"]:
                        start_entry["start_status"] = "DNS"
                        start_entry["info"] = (
                            f"DNS registered at {time_event['registration_time']}"
                        )
            startlist.append(start_entry)

    return startlist


async def get_event(token: str, event_id: str) -> dict:
    """Get event - return new if no event found."""
    event = {
        "id": event_id,
        "name": "Langrenn-sprint",
        "timezone": "Europe/Oslo",
        "organiser": "Ikke valgt",
    }
    if event_id:
        logging.debug(f"get_event {event_id}")
        event = await EventsAdapter().get_event(token, event_id)

    return event


def get_next_race_info(next_race_time_events: list, race_id: str) -> list:
    """Enrich start list with next race info."""
    startlist = []
    # get videre til information - loop and simulate result for pos 1 to 8
    for x in range(1, 9):
        for template in next_race_time_events:
            start_entry = {}
            _rank = template["rank"]
            if template["timing_point"] == "Template":
                if _rank == x:
                    start_entry["race_id"] = race_id
                    start_entry["starting_position"] = x
                    if template["next_race"].startswith("Ute"):
                        start_entry["next_race"] = "Ute"
                    else:
                        start_entry["next_race"] = template["next_race"]
                    startlist.append(start_entry)
    return startlist


async def get_passeringer(
    token: str, event_id: str, action: str, valgt_klasse: str
) -> list:
    """Return list of passeringer for selected action."""
    passeringer = []
    tmp_passeringer = await TimeEventsAdapter().get_time_events_by_event_id(
        token, event_id
    )
    if action == "control":
        for passering in reversed(tmp_passeringer):
            if not valgt_klasse or valgt_klasse in passering["race"]:
                if (
                    passering["status"] == "Error"
                    and passering["timing_point"] != "Template"
                ):
                    passeringer.append(passering)
    elif action == "Template":
        passeringer.extend(
            passering
            for passering in tmp_passeringer
            if (valgt_klasse in passering["race"])
            and (passering["timing_point"] == "Template")
        )
    else:
        passeringer.extend(
            passering
            for passering in tmp_passeringer
            if passering["timing_point"] not in ["Template"]
        )

    # indentify last passering in race
    last_race = ""
    for i, passering in enumerate(passeringer):
        if i == 0:
            passering["first_in_heat"] = True
        elif last_race != passering["race"]:
            passeringer[i - 1]["last_in_heat"] = True
            passering["first_in_heat"] = True
        if i == len(passeringer) - 1:
            passering["last_in_heat"] = True
        last_race = passering["race"]
    return passeringer


def get_qualification_text(race: dict) -> str:
    """Generate a text with info about qualification rules."""
    text = ""
    if race["round"] == "R1":
        text = "Alle til runde 2"
    elif race["round"] in ["R2", "F"]:
        text = ""
    else:
        for key, value in race["rule"].items():
            if key == "S":
                for x, y in value.items():
                    if y == "REST":
                        text += f"Resten til semi {x}. "
                    elif y > 0:
                        text += f"{y} til semi {x}. "
            elif key == "F":
                for x, y in value.items():
                    if y == "ALL":
                        text += f"Alle til finale {x}. "
                    elif y == "REST":
                        text += f"Resten til finale {x}. "
                    elif y > 0:
                        text += f"{y} til finale {x}. "
    logging.debug(f"Regel hele: {text}")
    return text


async def get_race_id_by_name(
    user: dict, event_id: str, next_race: str, raceclass: str
) -> str:
    """Get race_id for a given race."""
    race_id = ""
    races = await RaceplansAdapter().get_all_races(user["token"], event_id)
    for race in races:
        if race["raceclass"] == raceclass:
            tmp_next_race = f"{race['round']}{race['index']}{race['heat']}"
            if next_race == tmp_next_race:
                return race["id"]
    return race_id


def get_races_for_live_view(
    event: dict, races: list, valgt_heat: int, number_of_races: int
) -> list:
    """Return races to display in live view."""
    filtered_racelist = []
    time_now = EventsAdapter().get_local_time(event, "HH:MM:SS")
    i = 0
    # find next race on start
    if valgt_heat == 0:
        for race in races:
            if time_now < race["start_time"][-8:]:
                valgt_heat = race["order"]
                break

    for race in races:
        # from heat number (order) if selected
        if (race["order"] >= valgt_heat) and (i < number_of_races):
            race["next_race"] = get_qualification_text(race)
            race["start_time"] = race["start_time"][-8:]
            filtered_racelist.append(race)
            i += 1

    return filtered_racelist


async def get_races_for_print(
    user: dict, _tmp_races: list, raceclasses: list, valgt_klasse: str, action: str
) -> list:
    """Get races with lists - formatted for print."""
    races = []
    for raceclass in raceclasses:
        first_in_class = True
        for race in _tmp_races:
            if (race["raceclass"] == raceclass["name"]) and (
                (race["raceclass"] == valgt_klasse) or (valgt_klasse == "")
            ):
                race = await RaceplansAdapter().get_race_by_id(
                    user["token"], race["id"]
                )
                race["first_in_class"] = first_in_class
                race["next_race"] = get_qualification_text(race)
                race["start_time"] = race["start_time"][-8:]
                # get start list details
                if (
                    action == "start" or len(race["results"]) == 0
                ) and action != "result":
                    race["list_type"] = "start"
                    race["startliste"] = await get_enrichced_startlist(user, race)
                else:
                    race["list_type"] = action
                if first_in_class:
                    first_in_class = False
                races.append(race)
    return races


async def create_start(user: dict, form: dict) -> str:
    """Extract form data and create one start."""
    bib = int(form["bib"])
    contestant = await ContestantsAdapter().get_contestant_by_bib(
        user["token"], form["event_id"], bib
    )
    if contestant:
        new_start = {
            "startlist_id": form["startlist_id"],
            "race_id": form["race_id"],
            "bib": bib,
            "starting_position": int(form["starting_position"]),
            "scheduled_start_time": form["start_time"],
            "name": f"{contestant['first_name']} {contestant['last_name']}",
            "club": contestant["club"],
        }
        # validation - check that bib not already is in start entry for round
        new_race = await RaceplansAdapter().get_race_by_id(
            user["token"], new_start["race_id"]
        )
        start_entries = await StartAdapter().get_start_entries_by_bib(
            user["token"], form["event_id"], bib
        )
        for start_entry in start_entries:
            race = await RaceplansAdapter().get_race_by_id(
                user["token"], start_entry["race_id"]
            )
            if new_race["round"] == race["round"]:
                raise web.HTTPBadRequest(
                    reason=f"405 Bib already exists in round - {race['round']}"
                )

        w_id = await StartAdapter().create_start_entry(user["token"], new_start)
        logging.debug(f"create_start {w_id} - {new_start}")
        informasjon = f" Start kl {form['start_time'][-8:]}"

        # update previous result with correct "videre til"
        time_events = await TimeEventsAdapter().get_time_events_by_event_id_and_bib(
            user["token"], form["event_id"], bib
        )
        latest_result: dict = {}
        for time_event in time_events:
            if (
                (time_event["timing_point"] == "Finish")
                and (time_event["bib"] == bib)
                and (
                    (not latest_result)
                    or (
                        time_event["registration_time"]
                        > latest_result["registration_time"]
                    )
                )
            ):
                latest_result = time_event
        if latest_result:
            latest_result["next_race_id"] = new_race["id"]
            if new_race["round"] == "F":
                latest_result["next_race"] = f"{new_race['round']}{new_race['index']}"
            else:
                latest_result["next_race"] = (
                    f"{new_race['round']}{new_race['index']}{new_race['heat']}"
                )
            latest_result["next_race_position"] = new_start["starting_position"]
            w_id = await TimeEventsAdapter().update_time_event(
                user["token"], latest_result["id"], latest_result
            )
            logging.debug(f"updated time event {w_id} - {latest_result}")
            informasjon += " Oppdatert videre til fra forrige runde."
    else:
        informasjon = f"Error. Fant ikke deltaker med startnr {form['bib']}."
    return informasjon


async def swap_bibs(token: str, event_id: str, bib1: int, bib2: int) -> str:
    """Swap bibs."""
    informasjon = ""
    if bib1 != bib2:
        contestant1 = await ContestantsAdapter().get_contestant_by_bib(
            token, event_id, bib1
        )
        if contestant1:
            contestant1["bib"] = None
            result = await ContestantsAdapter().update_contestant(
                token, event_id, contestant1
            )

            # give bib1 to contestant2
            contestant2 = await ContestantsAdapter().get_contestant_by_bib(
                token, event_id, bib2
            )
            if contestant2:
                contestant2["bib"] = int(bib1)
                result = await ContestantsAdapter().update_contestant(
                    token, event_id, contestant2
                )
                logging.debug(result)

                # give bib2 to contestant1
                contestant1["bib"] = int(bib2)
                result = await ContestantsAdapter().update_contestant(
                    token, event_id, contestant1
                )
                logging.debug(result)
                informasjon += f"Bibs swapped: {bib1} <> {bib2}. "
            else:
                informasjon += f"Bib {bib1} not found. "
        else:
            informasjon += f"Bib {bib1} not found. "

    return informasjon


async def add_seeding_points(token: str, event_id: str, form: dict) -> str:
    """Load seeding points from form and update changes."""
    informasjon = "Seeding poeng oppdatert: "
    for key, value in form.items():
        if key.startswith("seeding_points_"):
            new_seeding_points = value
            old_seeding_points = form.get(f"old_{key}", "")
            if new_seeding_points in ["", "None", None]:
                new_seeding_points = ""
            if old_seeding_points in ["", "None", None]:
                old_seeding_points = ""
            if new_seeding_points != old_seeding_points:
                contestant_id = key[15:]
                contestant = await ContestantsAdapter().get_contestant(
                    token, event_id, contestant_id
                )
                if new_seeding_points.isnumeric():
                    contestant["seeding_points"] = int(new_seeding_points)
                else:
                    contestant["seeding_points"] = None
                result = await ContestantsAdapter().update_contestant(
                    token, event_id, contestant
                )
                logging.debug(result)
                informasjon += f"{contestant['first_name']} {contestant['last_name']}. "
    return informasjon


async def perform_seeding(token: str, event_id: str, valgt_klasse: str) -> str:
    """Assign bibs according to seeding points, low point is best."""
    informasjon = ""
    # if raceclass is missing, do seeding for all raceclasses
    raceclass_list = []
    if not valgt_klasse:
        raceclasses = await RaceclassesAdapter().get_raceclasses(token, event_id)
        raceclass_list.extend(_raceclass["name"] for _raceclass in raceclasses)
    else:
        raceclass_list.append(valgt_klasse)

    for seeding_raceclass in raceclass_list:
        contestants = await ContestantsAdapter().get_contestants_by_raceclass(
            token, event_id, seeding_raceclass
        )
        # sort seeded contestants by seeding points, lowest seeding is best - ignore contestants with no seeding points
        seeded_contestants = [x for x in contestants if x["seeding_points"]]
        seeded_contestants.sort(key=lambda x: x["seeding_points"])

        # get count of participants in each heat and number of heats
        heat_separators = await get_heat_separators(token, event_id, seeding_raceclass)
        no_of_heats = len(heat_separators)

        # calculate who to swap and do the bib swap
        for seeding_index, seeded_contestant in enumerate(seeded_contestants):
            # heat is modulo of seeding_index and no_of_heats and position is rest of division
            heat = seeding_index % no_of_heats
            position = seeding_index // no_of_heats
            if heat == 0:
                new_bib_index = position
            else:
                new_bib_index = heat_separators[heat - 1] + position
            new_bib = contestants[new_bib_index]["bib"]
            # get latest bib from db - contestant by id
            latest_seeded_contestant = await ContestantsAdapter().get_contestant(
                token, event_id, seeded_contestant["id"]
            )
            old_bib = latest_seeded_contestant["bib"]
            informasjon += await swap_bibs(token, event_id, new_bib, old_bib)
    if len(raceclass_list) > 1:
        informasjon = " Alle klasser er seedet basert på innleste seeding poeng."
    return informasjon


async def get_heat_separators(token: str, event_id: str, raceclass: str) -> list:
    """Indicate how many racers that will be placed in same heat."""
    heat_separators = []
    races = await RaceplansAdapter().get_races_by_racesclass(token, event_id, raceclass)
    count = 0
    for race in races:
        if race["round"] == "Q":
            count += race["no_of_contestants"]
            heat_separators.append(count)
    return heat_separators
