"""Resource module for main view."""

import datetime
import logging

from aiohttp import web
import aiohttp_jinja2

from event_service_gui.services import (
    RaceclassesAdapter,
    RaceplansAdapter,
)
from .utils import (
    check_login,
    get_event,
    get_qualification_text,
    get_raceplan_summary,
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
                valgt_klasse = ""  # noqa: F841

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
                )  # type: ignore
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
            logging.error(f"Error: {e}. Redirect to main page.")
            return web.HTTPSeeOther(location=f"/?informasjon={e}")

    async def post(self) -> web.Response:
        """Post route function that updates a collection of klasses."""
        user = await check_login(self)

        informasjon = ""
        action = ""
        form = await self.request.post()
        event_id = str(form["event_id"])

        try:
            if "update_one" in form.keys():
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
                        action = "edit_mode"
                        break
            # Create classes from list of contestants
            elif "generate_raceplan" in form.keys():
                result = await RaceplansAdapter().generate_raceplan(
                    user["token"], event_id
                )
                informasjon = f"Opprettet kjøreplan - {result}"
                return web.HTTPSeeOther(
                    location=f"/tasks?event_id={event_id}&informasjon={informasjon}"
                )
            elif "delete_all" in form.keys():
                resultat = await RaceplansAdapter().delete_raceplans(
                    user["token"], str(form["event_id"])
                )
                informasjon = f"Kjøreplaner er slettet - {resultat}"
            elif "update_time" in form.keys():
                logging.debug(f"update_time - form:{form}")
                order = int(form["order"])  # type: ignore
                new_time = str(form["new_time"])
                informasjon = await RaceplansAdapter().update_start_time(
                    user["token"], event_id, order, new_time
                )
                action = "edit_time"
            elif "set_rest_time" in form.keys():
                min_rest_time = int(form["min_rest_time"])  # type: ignore
                informasjon = await set_min_rest_time(
                    user["token"], event_id, min_rest_time
                )
                action = "edit_time"

        except Exception as e:
            logging.error(f"Error: {e}")
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


async def set_min_rest_time(token: str, event_id: str, min_rest_time: int) -> str:
    """Update raceplan - set minimum rest time between races."""
    informasjon = ""
    races = await RaceplansAdapter().get_all_races(token, event_id)
    raceclasses = await RaceclassesAdapter().get_raceclasses(token, event_id)
    raceplan_summary = get_raceplan_summary(races, raceclasses)
    rest_time = datetime.timedelta(minutes=min_rest_time)
    for raceclass in raceplan_summary:
        # check rest time before semi-finals / round 2 and adjust if nessecarry
        if raceclass["min_pauseS"] and (raceclass["min_pauseS"] < rest_time):
            time_adjust = rest_time - raceclass["min_pauseS"]
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
                        raceplan_summary = get_raceplan_summary(races, raceclasses)
                        break
        # check rest time before finals and adjust if nessecarry
        if raceclass["min_pauseF"] and (raceclass["min_pauseF"] < rest_time):
            time_adjust = rest_time - raceclass["min_pauseF"]
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
                        raceplan_summary = get_raceplan_summary(races, raceclasses)
                        break
    if not informasjon:
        informasjon = "Ingen endringer."
    return informasjon
