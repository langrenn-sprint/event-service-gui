"""Resource module for main view."""

import logging

import aiohttp_jinja2
from aiohttp import web

from event_service_gui.services import (
    ContestantsAdapter,
    RaceclassesAdapter,
    RaceplansAdapter,
    StartAdapter,
    TimeEventsAdapter,
    TimeEventsService,
)

from .utils import check_login, get_event


class Tasks(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get route function that return the tasks page."""
        try:
            event_id = self.request.rel_url.query["event_id"]
        except Exception:
            event_id = ""
        try:
            informasjon = self.request.rel_url.query["informasjon"]
        except Exception:
            informasjon = ""
        try:
            user = await check_login(self)
            event = await get_event(user["token"], event_id)

            task_status = await get_task_status(user["token"], event_id)

            return await aiohttp_jinja2.render_template_async(
                "tasks.html",
                self.request,
                {
                    "lopsinfo": "Admin: Sette rennet",
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "task_status": task_status,
                    "username": user["name"],
                },
            )
        except Exception as e:
            if "401" in str(e):
                return web.HTTPSeeOther(location=f"/login?informasjon={e}")
            logging.exception("Error.. Redirect to main page.")
            return web.HTTPSeeOther(location=f"/?informasjon={e}")

    async def post(self) -> web.Response:
        """Post route function that updates a collection of klasses."""
        user = await check_login(self)

        informasjon = ""
        action = ""
        form = await self.request.post()
        event_id = str(form["event_id"])
        event = await get_event(user["token"], event_id)

        try:
            if "generate_startlist" in form:
                informasjon = await StartAdapter().generate_startlist_for_event(
                    user["token"], event_id
                )
            elif "generate_next_race" in form:
                informasjon = await TimeEventsService().generate_next_race_templates(
                    user["token"], event
                )
            elif "delete_all_cont" in form:
                res = await ContestantsAdapter().delete_all_contestants(
                    user["token"], event_id
                )
                informasjon = f"Deltakerne er slettet - {res}"
            elif "delete_all_raceplans" in form:
                res = await RaceplansAdapter().delete_raceplans(user["token"], event_id)
                informasjon = f"Kjøreplaner er slettet - {res}"
            elif "delete_all_raceclasses" in form:
                res = await RaceclassesAdapter().delete_all_raceclasses(
                    user["token"], event_id
                )
                informasjon = f"Klasser er slettet - {res}"
            elif "delete_time_events" in form:
                informasjon = await delete_time_events(user["token"], event_id)
            elif "delete_start_lists" in form:
                informasjon = await delete_start_lists(user["token"], event_id)
        except Exception as e:
            informasjon = f"Det har oppstått en feil - {e.args}."
            error_reason = str(e)
            if error_reason.startswith("401"):
                return web.HTTPSeeOther(
                    location=f"/login?informasjon=Ingen tilgang, vennligst logg inn på nytt. {e}"
                )
            logging.exception("Error")

        info = f"action={action}&informasjon={informasjon}"
        return web.HTTPSeeOther(location=f"/tasks?event_id={event_id}&{info}")


async def delete_start_lists(token: str, event_id: str) -> str:
    """Delete all start lists on event."""
    startlists = await StartAdapter().get_all_starts_by_event(token, event_id)
    i = 0
    for startlist in startlists:
        w_id = await StartAdapter().delete_start_list(token, startlist["id"])
        logging.debug(f"Slettet startliste {startlist['id']} - resultat {w_id}")
        i += 1
    return f"Slettet {i} start lister."


async def delete_time_events(token: str, event_id: str) -> str:
    """Delete all time_events on event."""
    # delete all existing Template time events
    all_time_events = await TimeEventsAdapter().get_time_events_by_event_id(
        token,
        event_id,
    )
    i = 0
    for time_event in all_time_events:
        w_id = await TimeEventsAdapter().delete_time_event(token, time_event["id"])
        logging.debug(f"Deleted time_event id {w_id}")
        i += 1
    return f"Slettet {i} time_events."


async def get_task_status(token: str, event_id: str) -> dict:
    """Generate a status of event preparation."""
    task_status = {}
    # contestants informasjon
    contestants = await ContestantsAdapter().get_all_contestants(token, event_id)
    i_missing_bib = 0
    for contestant in contestants:
        if contestant["bib"] is None:
            i_missing_bib += 1
    task_status["no_of_contestants"] = len(contestants)
    if len(contestants) > 0:
        task_status["done_2"] = True
    else:
        task_status["done_2"] = False

    task_status["bib_missing"] = i_missing_bib
    if i_missing_bib == 0 and len(contestants) > 0:
        task_status["done_5"] = True
    else:
        task_status["done_5"] = False

    # raceclasses informasjon
    raceclasses = await RaceclassesAdapter().get_raceclasses(token, event_id)
    i_missing_startorder = 0
    for klasse in raceclasses:
        if klasse["order"] is None:
            i_missing_startorder += 1
    task_status["no_of_raceclasses"] = len(raceclasses)
    if len(raceclasses) > 0:
        task_status["done_3"] = True
    else:
        task_status["done_3"] = False
    task_status["no_of_startorder_missing"] = i_missing_startorder
    if (i_missing_startorder == 0) and (len(raceclasses) > 0):
        task_status["done_4"] = True
    else:
        task_status["done_4"] = False

    # raceplan informasjon
    races = await RaceplansAdapter().get_all_races(token, event_id)
    task_status["no_of_races"] = len(races)
    if len(races) > 0:
        task_status["done_6"] = True
        raceplans = await RaceplansAdapter().get_all_raceplans(token, event_id)
        if len(raceplans) == 1:
            task_status[
                "raceplan_validation"
            ] = await RaceplansAdapter().validate_raceplan(
                token, raceplans[0]["id"]
            )
    else:
        task_status["done_6"] = False

    # start list
    startlist = await StartAdapter().get_all_starts_by_event(token, event_id)
    if len(startlist) > 0:
        task_status["no_of_starts"] = len(startlist[0]["start_entries"])
        task_status["done_8"] = True
    else:
        task_status["done_8"] = False

    # qualification - next race
    next_race_templates = []
    passeringer = await TimeEventsAdapter().get_time_events_by_event_id(token, event_id)
    for passering in passeringer:
        if passering["timing_point"] == "Template":
            next_race_templates.append(passering)
            logging.debug(passering)

    if len(next_race_templates) > 0:
        task_status["no_of_next_race"] = len(next_race_templates)
        task_status["done_9"] = True
    else:
        task_status["done_9"] = False

    return task_status
