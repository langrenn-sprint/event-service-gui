"""Resource module for main view."""

import datetime
import logging

import aiohttp_jinja2
from aiohttp import web

from event_service_gui.services import (
    RaceclassesAdapter,
    RaceplansAdapter,
)

from .utils import (
    check_login,
    get_event,
    get_qualification_text,
)


class Raceplans(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get route function that return the index page."""
        informasjon = ""
        html_template = "raceplans.html"

        try:
            event_id = self.request.rel_url.query["event_id"]
        except Exception:
            informasjon = "Ingen event valgt."
            return web.HTTPSeeOther(location=f"/?informasjon={informasjon}")

        try:
            user = await check_login(self)
            event = await get_event(user["token"], event_id)

            try:
                informasjon = self.request.rel_url.query["informasjon"]
            except Exception:
                informasjon = ""
            try:
                action = self.request.rel_url.query["action"]
            except Exception:
                action = ""
            logging.debug(f"Action: {action}")

            try:
                valgt_klasse = self.request.rel_url.query["klasse"]
            except Exception:
                valgt_klasse = ""

            raceclasses = await RaceclassesAdapter().get_raceclasses(
                user["token"], event_id
            )
            races = []
            if action == "edit_one":
                html_template = "raceplan_edit.html"
                race = await RaceplansAdapter().get_race_by_id(
                    user["token"], self.request.rel_url.query["race_id"]
                )
                races.append(race)
                valgt_klasse = race["raceclass"]
            else:
                races = await RaceplansAdapter().get_all_races(user["token"], event_id)
            raceplan_summary = []
            if len(races) == 0:
                informasjon = f"{informasjon} Ingen kjøreplaner funnet."
            else:
                raceplan_summary = get_raceplan_summary(races, raceclasses)
            # generate text explaining qualification rule (videre til)
            for race in races:
                race["next_race"] = get_qualification_text(race)

            # get validation results
            raceplans = await RaceplansAdapter().get_all_raceplans(
                user["token"], event_id
            )
            raceplan_validation = {}
            if len(raceplans) == 1:
                raceplan_validation = await RaceplansAdapter().validate_raceplan(
                    user["token"], raceplans[0]["id"]
                )
                for race in races:
                    for x, y in raceplan_validation.items():
                        if x == str(race["order"]):
                            race["validation"] = y

            return await aiohttp_jinja2.render_template_async(
                html_template,
                self.request,
                {
                    "action": action,
                    "lopsinfo": "Kjøreplan",
                    "raceclasses": raceclasses,
                    "raceplan_summary": raceplan_summary,
                    "raceplan_validation": raceplan_validation,
                    "races": races,
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "username": user["name"],
                    "valgt_klasse": valgt_klasse,
                },
            )
        except Exception as e:
            logging.exception("Error.. Redirect to main page.")
            return web.HTTPSeeOther(location=f"/?informasjon={e}")

    async def post(self) -> web.Response:
        """Post route function that updates a collection of klasses."""
        user = await check_login(self)

        informasjon = ""
        action = "edit_mode"
        form = await self.request.post()
        event_id = str(form["event_id"])

        try:
            if "update_one" in form:
                race_id = str(form["race_id"])
                races = await RaceplansAdapter().get_all_races(user["token"], event_id)
                for race in races:
                    if race["id"] == race_id:
                        new_max_no_of_contestants = form["new_max_no_of_contestants"]
                        if new_max_no_of_contestants:
                            race["max_no_of_contestants"] = new_max_no_of_contestants
                        res = await RaceplansAdapter().update_race(
                            user["token"], race["id"], race
                        )
                        informasjon = (
                            f"Race er oppdatert({res}) - race nr {race['order']}"
                        )
                        break
            # Create classes from list of contestants
            elif "generate_raceplan" in form:
                result = await RaceplansAdapter().generate_raceplan(
                    user["token"], event_id
                )
                informasjon = f"Opprettet kjøreplan - {result}"
                return web.HTTPSeeOther(
                    location=f"/tasks?event_id={event_id}&informasjon={informasjon}"
                )
            elif "delete_all" in form:
                resultat = await RaceplansAdapter().delete_raceplans(
                    user["token"], str(form["event_id"])
                )
                informasjon = f"Kjøreplaner er slettet - {resultat}"
            elif "update_time" in form:
                logging.debug(f"update_time - form:{form}")
                informasjon = await RaceplansAdapter().update_start_time(
                    user["token"],
                    event_id,
                    int(str(form["order"])),
                    str(form["new_time"]),
                )
                action = "edit_time"
            elif "set_rest_time" in form:
                informasjon = await set_min_rest_time(
                    user["token"], event_id, int(str(form["min_rest_time"]))
                )
                action = "edit_time"
            elif "edit_heat_interval" in form:
                informasjon = await update_heat_time_interval(
                    user["token"], event_id, dict(form)
                )

        except Exception as e:
            logging.exception("Error")
            informasjon = f"Det har oppstått en feil - {e.args}."
            error_reason = str(e)
            if error_reason.startswith("401"):
                return web.HTTPSeeOther(
                    location=f"/login?informasjon=Ingen tilgang, vennligst logg inn på nytt. {e}"
                )
        else:
            informasjon = f"Suksess! {informasjon}"
        info = f"action={action}&informasjon={informasjon}"
        return web.HTTPSeeOther(location=f"/raceplans?event_id={event_id}&{info}")


async def update_heat_time_interval(token: str, event_id: str, form: dict) -> str:
    """Update raceplan - set heat time interval."""
    informasjon = ""
    races = await RaceplansAdapter().get_all_races(token, event_id)
    first_heat = int(form["first_heat"])
    last_heat = int(form["last_heat"])
    heat_interval = time_str_to_timedelta(form["heat_interval"])

    if races:
        # Initialize previous_race_time_obj with first value
        previous_race_time_obj = datetime.datetime.strptime(
            races[0]["start_time"], "%Y-%m-%dT%H:%M:%S"
        )

        for race in races:
            if first_heat == race["order"]:
                previous_race_time_obj = datetime.datetime.strptime(
                    race["start_time"], "%Y-%m-%dT%H:%M:%S"
                )
            if first_heat < race["order"] <= last_heat:
                # set new time for this
                new_time_obj = previous_race_time_obj + heat_interval
                new_time = f"{new_time_obj.strftime('%X')}"
                informasjon += await RaceplansAdapter().update_start_time(
                    token, event_id, race["order"], new_time
                )
                previous_race_time_obj = new_time_obj
    return informasjon


async def set_min_rest_time(token: str, event_id: str, min_rest_time: int) -> str:
    """Update raceplan - set minimum rest time between races."""
    informasjon = ""
    races = await RaceplansAdapter().get_all_races(token, event_id)
    raceclasses = await RaceclassesAdapter().get_raceclasses(token, event_id)
    rest_time = datetime.timedelta(minutes=min_rest_time)
    for raceclass in raceclasses:
        # check rest time before semi-finals / round 2 and adjust if nessecarry
        timing = get_raceplan_timing(races, raceclass)
        if timing["min_pauseS"] and (timing["min_pauseS"] < rest_time):
            time_adjust = rest_time - timing["min_pauseS"]
            for race in races:
                if race["raceclass"] == raceclass["name"]:
                    if f"{race['round']}{race['heat']}" in ("S1", "R21"):
                        # set new time for this race and all following
                        old_time_obj = datetime.datetime.strptime(
                            race["start_time"], "%Y-%m-%dT%H:%M:%S"
                        )
                        new_time_obj = old_time_obj + time_adjust
                        new_time = f"{new_time_obj.strftime('%X')}"
                        informasjon += await RaceplansAdapter().update_start_time(
                            token, event_id, race["order"], new_time
                        )
                        # refresh data - get latest time info
                        races = await RaceplansAdapter().get_all_races(token, event_id)
                        break
        # check rest time before finals and adjust if nessecarry
        if timing["min_pauseF"] and (timing["min_pauseF"] < rest_time):
            time_adjust = rest_time - timing["min_pauseF"]
            # find first final race
            for race in races:
                if race["raceclass"] == raceclass["name"]:
                    if f"{race['round']}" == "F":
                        # set new time for this race and all following
                        old_time_obj = datetime.datetime.strptime(
                            race["start_time"], "%Y-%m-%dT%H:%M:%S"
                        )
                        new_time_obj = old_time_obj + time_adjust
                        new_time = f"{new_time_obj.strftime('%X')}"
                        informasjon += await RaceplansAdapter().update_start_time(
                            token, event_id, race["order"], new_time
                        )
                        # refresh data - get latest time info
                        races = await RaceplansAdapter().get_all_races(token, event_id)
                        break
    if not informasjon:
        informasjon = "Ingen endringer."
    return informasjon


def get_raceplan_timing(races: list, raceclass: dict) -> dict:
    """Generate a summary with key timing for the raceplan."""
    class_summary = {}
    # loop through races - calculate shortest rest-times.
    # between last Quarter and first Semi and last semi A and final AorB.
    time_q_last = ""
    time_s_first = ""
    time_s_last = ""
    time_fab_first = ""
    for race in races:
        if race["datatype"] == "individual_sprint":
            if race["raceclass"] == raceclass["name"]:
                if race["round"] in ["Q", "R1"]:
                    time_q_last = race["start_time"]
                elif race["round"] in ["S", "R2"]:
                    if not (time_s_first):
                        time_s_first = race["start_time"]
                    time_s_last = race["start_time"]
                elif race["round"] == "F":
                    if race["index"] in ["A", "B", "B2", "B3", "B4"]:
                        if not (time_fab_first):
                            time_fab_first = race["start_time"]
    if time_q_last:
        time_q_last_obj = datetime.datetime.strptime(time_q_last, "%Y-%m-%dT%H:%M:%S")
        if (time_s_first) and (time_fab_first):
            time_s_first_obj = datetime.datetime.strptime(
                time_s_first, "%Y-%m-%dT%H:%M:%S"
            )
            time_s_last_obj = datetime.datetime.strptime(
                time_s_last, "%Y-%m-%dT%H:%M:%S"
            )
            time_fab_first_obj = datetime.datetime.strptime(
                time_fab_first, "%Y-%m-%dT%H:%M:%S"
            )
            class_summary["min_pauseS"] = time_s_first_obj - time_q_last_obj
            class_summary["warning_pauseS"] = check_short_pause(
                class_summary["min_pauseS"]
            )
            class_summary["min_pauseF"] = time_fab_first_obj - time_s_last_obj
            class_summary["warning_pauseF"] = check_short_pause(
                class_summary["min_pauseF"]
            )
        elif time_fab_first:
            time_fab_first_obj = datetime.datetime.strptime(
                time_fab_first, "%Y-%m-%dT%H:%M:%S"
            )
            class_summary["min_pauseS"] = ""
            class_summary["min_pauseF"] = time_fab_first_obj - time_q_last_obj
            class_summary["warning_pauseF"] = check_short_pause(
                class_summary["min_pauseF"]
            )
        elif time_s_first:
            time_s_first_obj = datetime.datetime.strptime(
                time_s_first, "%Y-%m-%dT%H:%M:%S"
            )
            time_s_last_obj = datetime.datetime.strptime(
                time_s_last, "%Y-%m-%dT%H:%M:%S"
            )
            class_summary["min_pauseS"] = time_s_first_obj - time_q_last_obj
            class_summary["warning_pauseS"] = check_short_pause(
                class_summary["min_pauseS"]
            )
            class_summary["min_pauseF"] = ""

    return class_summary


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
                if race["round"] in ["Q", "R1"]:
                    class_summary["timeQ"] = race["start_time"][-8:]
                    class_summary["orderQ"] = race["order"]
                elif race["round"] in ["S", "R2"]:
                    class_summary["timeS"] = race["start_time"][-8:]
                    class_summary["orderS"] = race["order"]
                elif race["round"] == "F":
                    class_summary["timeF"] = race["start_time"][-8:]
                    class_summary["orderF"] = race["order"]
        # loop through races - calculate shortest rest-times.
        # between last Quarter and first Semi and last semi A and final AorB.
        time_q_last = ""
        time_s_first = ""
        time_s_last = ""
        time_fab_first = ""
        for race in races:
            if race["datatype"] == "individual_sprint":
                if race["raceclass"] == raceclass["name"]:
                    if race["round"] in ["Q", "R1"]:
                        time_q_last = race["start_time"]
                    elif race["round"] in ["S", "R2"]:
                        if not (time_s_first):
                            time_s_first = race["start_time"]
                        time_s_last = race["start_time"]
                    elif race["round"] == "F":
                        if race["index"] in ["A", "B", "B2", "B3", "B4"]:
                            if not (time_fab_first):
                                time_fab_first = race["start_time"]
        if time_q_last:
            time_q_last_obj = datetime.datetime.strptime(
                time_q_last, "%Y-%m-%dT%H:%M:%S"
            )
            if (time_s_first) and (time_fab_first):
                time_s_first_obj = datetime.datetime.strptime(
                    time_s_first, "%Y-%m-%dT%H:%M:%S"
                )
                time_s_last_obj = datetime.datetime.strptime(
                    time_s_last, "%Y-%m-%dT%H:%M:%S"
                )
                time_fab_first_obj = datetime.datetime.strptime(
                    time_fab_first, "%Y-%m-%dT%H:%M:%S"
                )
                class_summary["min_pauseS"] = time_s_first_obj - time_q_last_obj
                class_summary["warning_pauseS"] = check_short_pause(
                    class_summary["min_pauseS"]
                )
                class_summary["min_pauseF"] = time_fab_first_obj - time_s_last_obj
                class_summary["warning_pauseF"] = check_short_pause(
                    class_summary["min_pauseF"]
                )
            elif time_fab_first:
                time_fab_first_obj = datetime.datetime.strptime(
                    time_fab_first, "%Y-%m-%dT%H:%M:%S"
                )
                class_summary["min_pauseS"] = ""
                class_summary["min_pauseF"] = time_fab_first_obj - time_q_last_obj
                class_summary["warning_pauseF"] = check_short_pause(
                    class_summary["min_pauseF"]
                )
            elif time_s_first:
                time_s_first_obj = datetime.datetime.strptime(
                    time_s_first, "%Y-%m-%dT%H:%M:%S"
                )
                time_s_last_obj = datetime.datetime.strptime(
                    time_s_last, "%Y-%m-%dT%H:%M:%S"
                )
                class_summary["min_pauseS"] = time_s_first_obj - time_q_last_obj
                class_summary["warning_pauseS"] = check_short_pause(
                    class_summary["min_pauseS"]
                )
                class_summary["min_pauseF"] = ""

        summary.append(class_summary)
    logging.debug(summary)
    return summary


def check_short_pause(pause_time) -> bool:
    """Return true if pause time is acceptable."""
    return pause_time < datetime.timedelta(minutes=12)


def time_str_to_timedelta(time_str: str) -> datetime.timedelta:
    """Convert time string in format mm:ss to a timedelta object."""
    minutes, seconds = map(int, time_str.split(":"))
    return datetime.timedelta(minutes=minutes, seconds=seconds)
