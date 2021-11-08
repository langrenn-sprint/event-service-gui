"""Resource module for main view."""
import logging
import os

from aiohttp import web
import aiohttp_jinja2

from event_service_gui.services import (
    ContestantsAdapter,
    RaceclassesAdapter,
    RaceplansAdapter,
    StartAdapter,
    TimeEventsAdapter,
)
from .utils import check_login, get_event


RESULT_GUI_HOST_SERVER = os.getenv("RESULT_GUI_HOST_SERVER", "localhost")
RESULT_GUI_HOST_PORT = os.getenv("RESULT_GUI_HOST_PORT", "8090")
RESULT_GUI_URL = f"http://{RESULT_GUI_HOST_SERVER}:{RESULT_GUI_HOST_PORT}"


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
                    "lopsinfo": "Oppgaver - oversikt",
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "result_gui_url": RESULT_GUI_URL,
                    "task_status": task_status,
                    "username": user["name"],
                },
            )
        except Exception as e:
            logging.error(f"Error: {e}. Redirect to main page.")
            return web.HTTPSeeOther(location=f"/?informasjon={e}")


async def get_task_status(token: str, event_id: str) -> dict:
    """Generate a status of event preparation."""
    task_status = {}
    # contestants informasjon
    contestants = await ContestantsAdapter().get_all_contestants(token, event_id, "")
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
        if passering["point"] == "Template":
            next_race_templates.append(passering)
            logging.debug(passering)

    if len(next_race_templates) > 0:
        task_status["no_of_next_race"] = len(next_race_templates)
        task_status["done_9"] = True
    else:
        task_status["done_9"] = False

    return task_status
