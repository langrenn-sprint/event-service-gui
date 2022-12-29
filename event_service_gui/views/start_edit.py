"""Resource module for verificatoin of timing registration."""
import logging

from aiohttp import web
import aiohttp_jinja2

from event_service_gui.services import (
    ContestantsAdapter,
    EventsAdapter,
    RaceclassesAdapter,
    RaceplansAdapter,
    StartAdapter,
    TimeEventsAdapter,
)
from .utils import (
    check_login,
    get_enrichced_startlist,
    get_event,
    get_passeringer,
    get_qualification_text,
    get_race_id_by_name,
    update_time_event,
)


class StartEdit(web.View):
    """Class representing the start edit view."""

    async def get(self) -> web.Response:
        """Get route function that return the passeringer page."""
        next_races = []
        templates = []
        valgt_klasse = ""

        try:
            informasjon = self.request.rel_url.query["informasjon"]
        except Exception:
            informasjon = ""
        try:
            valgt_runde = self.request.rel_url.query["runde"]
        except Exception:
            valgt_runde = ""  # noqa: F841

        try:
            user = await check_login(self)
            event_id = self.request.rel_url.query["event_id"]
            event = await get_event(user["token"], event_id)
            raceclasses = await RaceclassesAdapter().get_raceclasses(
                user["token"], event_id
            )
            all_races = await RaceplansAdapter().get_all_races(user["token"], event_id)

            # find raceclass
            try:
                valgt_klasse = self.request.rel_url.query["klasse"]
            except Exception:
                informasjon = "Velg klasse i menyen."

            try:
                action = self.request.rel_url.query["action"]
            except Exception:
                action = ""

            # filter for selected races and enrich
            for race in all_races:
                if valgt_klasse == race["raceclass"]:
                    race = await RaceplansAdapter().get_race_by_id(
                        user["token"], race["id"]
                    )
                    race["next_race"] = get_qualification_text(race)
                    # get start list detail
                    race["startliste"] = await get_enrichced_startlist(user, race)
                    next_races.append(race)

            if valgt_runde:
                filtered_races = []
                for race in next_races:
                    if race["round"] == valgt_runde:
                        filtered_races.append(race)
                next_races = filtered_races

            # get templates
            if action == "Template":
                # get passeringer
                templates = await get_passeringer(
                    user["token"], event_id, action, valgt_klasse
                )

            """Get route function."""
            return await aiohttp_jinja2.render_template_async(
                "start_edit.html",
                self.request,
                {
                    "action": action,
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "next_races": next_races,
                    "raceclasses": raceclasses,
                    "templates": templates,
                    "username": user["name"],
                    "valgt_klasse": valgt_klasse,
                    "valgt_runde": valgt_runde,
                },
            )
        except Exception as e:
            logging.error(f"Error: {e}. Redirect to main page.")
            return web.HTTPSeeOther(location=f"/?informasjon={e}")

    async def post(self) -> web.Response:
        """Post route function that creates deltakerliste."""
        # check login
        user = await check_login(self)
        informasjon = ""
        valgt_klasse = ""
        action = ""
        try:
            form = await self.request.post()
            logging.debug(f"Form {form}")
            event_id = str(form["event_id"])
            event = await get_event(user["token"], event_id)
            valgt_klasse = str(form["klasse"])
            valgt_runde = str(form["runde"])

            if "create_start" in form.keys():
                informasjon = await create_start(user, form)  # type: ignore
            elif "delete_start" in form.keys():
                informasjon = await delete_start(user, form)  # type: ignore
            if "update_templates" in form.keys():
                action = str(form["action"])
                informasjon = await update_template_events(user, event, form)  # type: ignore
        except Exception as e:
            logging.error(f"Error: {e}")
            informasjon = f"Det har oppstått en feil - {e.args}."
            error_reason = str(e)
            if error_reason.startswith("401"):
                return web.HTTPSeeOther(
                    location=f"/login?informasjon=Ingen tilgang, vennligst logg inn på nytt. {e}"
                )
        info = (
            f"{informasjon}&klasse={valgt_klasse}&runde={valgt_runde}&action={action}"
        )
        return web.HTTPSeeOther(
            location=f"/start_edit?event_id={event_id}&informasjon={info}"
        )


async def create_start(user: dict, form: dict) -> str:
    """Extract form data and create one start."""
    contestant = await ContestantsAdapter().get_contestant_by_bib(
        user["token"], form["event_id"], form["bib"]
    )

    new_start = {
        "startlist_id": form["startlist_id"],
        "race_id": form["race_id"],
        "bib": int(form["bib"]),
        "starting_position": int(form["starting_position"]),
        "scheduled_start_time": form["start_time"],
        "name": f"{contestant['first_name']} {contestant['last_name']}",
        "club": contestant["club"],
    }
    id = await StartAdapter().create_start_entry(user["token"], new_start)
    informasjon = f"Opprettet ny start. Resultat: {id}"
    return informasjon


async def delete_start(user: dict, form: dict) -> str:
    """Extract form data and delete one start event."""
    informasjon = "delete_start"
    id = await StartAdapter().delete_start_entry(
        user["token"], form["race_id"], form["start_id"]
    )
    informasjon = f"Slettet start. Resultat: {id}"
    return informasjon


async def update_template_events(user: dict, event: dict, form: dict) -> str:
    """Extract form data and update template event."""
    informasjon = "Control result: "
    for i in range(1, 11):
        if f"next_race_{i}" in form.keys():
            if form[f"next_race_{i}"]:
                request_body = {
                    "event_id": form["event_id"],
                    "id": form[f"id_{i}"],
                    "update_template": True,
                    "next_race": form[f"next_race_{i}"],
                    "next_race_position": form[f"next_race_position_{i}"],
                    "race": form["race"],
                }
                informasjon += await update_time_event(user, event, request_body)
    if form["rank_new"]:
        next_race_id = await get_race_id_by_name(
            user, form["event_id"], form["next_race_new"], form["klasse"]
        )
        time_stamp_now = EventsAdapter().get_local_time(event, "log")
        time_event = {
            "bib": 0,
            "event_id": form["event_id"],
            "race": form["race"],
            "race_id": form["race_id"],
            "timing_point": "Template",
            "rank": form["rank_new"],
            "registration_time": time_stamp_now,
            "next_race": form["next_race_new"],
            "next_race_id": next_race_id,
            "next_race_position": form["next_race_position_new"],
            "status": "OK",
            "changelog": [],
        }
        id = await TimeEventsAdapter().create_time_event(user["token"], time_event)
        informasjon += f" Added new {id} "
    return informasjon
