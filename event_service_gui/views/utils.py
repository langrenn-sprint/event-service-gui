"""Utilities module for gui services."""
import datetime
import logging

from aiohttp import web
from aiohttp_session import get_session

from event_service_gui.services import (
    CompetitionFormatAdapter,
    EventsAdapter,
    RaceplansAdapter,
    TimeEventsAdapter,
    UserAdapter,
)


async def check_login(self) -> dict:
    """Check login and return user credentials."""
    session = await get_session(self.request)
    loggedin = UserAdapter().isloggedin(session)
    if not loggedin:
        informasjon = "Logg inn for å se denne siden"
        raise web.HTTPSeeOther(location=f"/login?informasjon={informasjon}")  # type: ignore

    return {
        "name": session["name"],
        "loggedin": True,
        "token": session["token"],
        "g_loggedin": session["g_loggedin"],
        "g_name": session["g_name"],
        "g_jwt": session["g_jwt"],
        "g_auth_photos": session["g_auth_photos"],
        "g_scope": session["g_scope"],
        "g_client_id": session["g_client_id"],
        "g_photos_token": session["g_photos_token"],
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
    informasjon = await CompetitionFormatAdapter().create_competition_format(
        token, request_body
    )
    return informasjon


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
                        start_entry[
                            "info"
                        ] = f"Started registered at {time_event['registration_time']}"
                elif time_event["timing_point"] == "DNS":
                    if time_event["bib"] == start_entry["bib"]:
                        start_entry["start_status"] = "DNS"
                        start_entry[
                            "info"
                        ] = f"DNS registered at {time_event['registration_time']}"
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
                    start_entry["starting_position"] = x  # type: ignore
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
    elif action in [
        "Template",
    ]:
        for passering in tmp_passeringer:
            if valgt_klasse in passering["race"]:
                if passering["timing_point"] == "Template":
                    passeringer.append(passering)
    else:
        for passering in tmp_passeringer:
            if passering["timing_point"] not in [
                "Template",
                "Error",
            ]:
                passeringer.append(passering)

    # indentify last passering in race
    i = 0
    last_race = ""
    for passering in passeringer:
        if i == 0:
            passering["first_in_heat"] = True
        elif last_race != passering["race"]:
            passeringer[i - 1]["last_in_heat"] = True
            passering["first_in_heat"] = True
        i += 1
        if i == len(passeringer):
            passering["last_in_heat"] = True
        last_race = passering["race"]

    return passeringer


def get_qualification_text(race: dict) -> str:
    """Generate a text with info about qualification rules."""
    text = ""
    if race["round"] == "R1":
        text = "Alle til runde 2"
    elif race["round"] == "R2":
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


def get_raceplan_summary(races: list, raceclasses: list) -> list:
    """Generate a summary with key timing for the raceplan."""
    summary = []
    # create a dict of all raceclasses and populate
    # loop raceclasses and find key parameters
    for raceclass in raceclasses:
        class_summary = {"name": raceclass["name"]}
        class_summary["no_of_contestants"] = raceclass["no_of_contestants"]
        class_summary["ranking"] = raceclass["ranking"]
        # loop through races - update start time pr round pr class
        for race in reversed(races):
            if race["raceclass"] == raceclass["name"]:
                if race["datatype"] == "individual_sprint":
                    if race["round"] in ["Q", "R1"]:
                        class_summary["timeQ"] = race["start_time"][-8:]
                        class_summary["orderQ"] = race["order"]
                    elif race["round"] in ["S", "R2"]:
                        class_summary["timeS"] = race["start_time"][-8:]
                        class_summary["orderS"] = race["order"]
                    elif race["round"] == "F":
                        class_summary["timeF"] = race["start_time"][-8:]
                        class_summary["orderF"] = race["order"]
        summary.append(class_summary)
    logging.debug(summary)
    return summary


def get_races_for_live_view(
    event, races, valgt_heat: int, number_of_races: int
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
            if race["raceclass"] == raceclass["name"]:
                if (race["raceclass"] == valgt_klasse) or ("" == valgt_klasse):
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


async def update_time_event(user: dict, event: dict, form: dict) -> str:
    """Register time event - return information."""
    informasjon = ""
    time_stamp_now = EventsAdapter().get_local_time(event, "log")
    request_body = await TimeEventsAdapter().get_time_event_by_id(
        user["token"], form["id"]
    )
    if "update" in form.keys():
        request_body["changelog"] = [
            {
                "timestamp": time_stamp_now,
                "user_id": user["name"],
                "comment": f"Oppdatering - tidligere informasjon: {request_body}. ",
            }
        ]
        request_body["timing_point"] = form["timing_point"]
        request_body["registration_time"] = form["registration_time"]
        request_body["rank"] = form["rank"]
    elif "update_template" in form.keys():
        request_body["changelog"] = [
            {
                "timestamp": time_stamp_now,
                "user_id": user["name"],
                "comment": f"Oppdatering - old info, next_race {request_body['next_race']}-{request_body['next_race_position']}. ",
            }
        ]
        request_body["next_race_position"] = form["next_race_position"]
        raceclass = form["race"].split("-")
        request_body["next_race_id"] = await get_race_id_by_name(
            user, form["event_id"], form["next_race"], raceclass[0]
        )
        request_body["next_race"] = form["next_race"]
    elif "delete" in form.keys():
        response = await TimeEventsAdapter().delete_time_event(
            user["token"], form["id"]
        )
    logging.debug(f"Control result: {response}")
    informasjon = f"Oppdatert - {response}  "
    return informasjon
