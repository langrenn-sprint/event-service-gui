"""Resource module for start resources."""

import logging

import aiohttp_jinja2
from aiohttp import web

from event_service_gui.adapters import (
    EventsAdapter,
    RaceclassesAdapter,
    RaceplansAdapter,
    StartAdapter,
)
from event_service_gui.services import (
    TimeEventsService,
)

from .utils import (
    check_login,
    get_enrichced_startlist,
    get_event,
    login_location,
)


class Timing(web.View):
    """Class representing the start view."""

    async def get(self) -> web.Response:
        """Get route function that return the timing registration page."""
        informasjon = ""
        try:
            event_id = self.request.rel_url.query["event_id"]
        except Exception:
            event_id = ""
        try:
            informasjon = self.request.rel_url.query["informasjon"]
        except Exception:
            informasjon = ""
        try:
            action = self.request.rel_url.query["action"]
        except Exception:
            action = "start"
            informasjon = f"Velg funksjon i menyen. {informasjon}"
        try:
            valgt_heat = int(self.request.rel_url.query["heat"])
        except Exception:
            valgt_heat = 0

        user = await check_login(self)
        try:
            event = await get_event(user["token"], event_id)
            raceclasses = await RaceclassesAdapter().get_raceclasses(
                user["token"], event_id
            )
            races = []
            if valgt_heat == 0:
                # find race starting now
                all_races = await RaceplansAdapter().get_all_races(
                    user["token"], event_id
                )
                time_now = EventsAdapter().get_local_time(event, "HH:MM:SS")
                # find next race on start
                valgt_heat = 1
                for tmp_race in all_races:
                    if time_now < tmp_race["start_time"][-8:]:
                        valgt_heat = tmp_race["order"]
                        break
            race = await RaceplansAdapter().get_race_by_order(
                user["token"], event_id, valgt_heat
            )
            races.append(race)
            if len(races) > 0:
                for race in races:
                    # get start list detail
                    race["startliste"] = await get_enrichced_startlist(user, race)
            else:
                informasjon = "Fant ingen heat. Velg på nytt."

            """Get route function."""
            return await aiohttp_jinja2.render_template_async(
                "timing.html",
                self.request,
                {
                    "action": action,
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "raceclasses": raceclasses,
                    "races": races,
                    "username": user["name"],
                    "valgt_heat": valgt_heat,
                },
            )
        except Exception as e:
            logging.exception("Error. Redirect to main page.")
            raise web.HTTPSeeOther(location=f"/?informasjon={e}") from e

    async def post(self) -> web.Response:
        """Post route function that register started or DNS."""
        # check login
        user = await check_login(self)
        form = dict(await self.request.post())
        event_id = str(form["event_id"])
        action = str(form["action"])
        valgt_heat = str(form["heat"])
        informasjon = ""
        try:
            event = await get_event(user["token"], event_id)

            if "finish" in action:
                informasjon = "Funksjon ikke støttet, bruk hovedside for tidtaker"
            elif action == "start":
                informasjon = await create_start_time_events_for_race(user, event, form)
            elif action == "dns_manual":
                informasjon = await create_dns_time_events_manual(user, event, form)
            else:
                informasjon = "Ugylding action - ingen endringer"

        except Exception as e:
            logging.exception("Error")
            informasjon = f"Det har oppstått en feil - {e.args}."
            error_reason = str(e)
            if error_reason.startswith("401"):
                raise web.HTTPSeeOther(
                    location=login_location(
                        f"Ingen tilgang, vennligst logg inn på nytt. {e}",
                        self.request.path_qs,
                    )
                ) from e

        raise web.HTTPSeeOther(
            location=f"/timing?event_id={event_id}&informasjon={informasjon}&action={action}&heat={valgt_heat}"
        )


async def create_dns_time_events_manual(user: dict, event: dict, form: dict) -> str:
    """Extract form data and create time_events for start."""
    informasjon = ""
    time_stamp_now = EventsAdapter().get_local_time(event, "log")
    request_body = {
        "id": "",
        "bib": 0,
        "event_id": form["event_id"],
        "race": "",
        "race_id": "",
        "timing_point": "",
        "rank": 0,
        "registration_time": time_stamp_now,
        "next_race": "",
        "next_race_id": "",
        "next_race_position": 0,
        "status": "OK",
        "changelog": [],
    }
    i = 0
    if "bib" in form:
        biblist = form["bib"].rsplit(" ")
        for bib in biblist:
            try:
                if bib.isnumeric():
                    request_body["timing_point"] = "DNS"
                    changelog_comment = "DNS registrert. "
                    request_body["bib"] = int(bib)
                    request_body["changelog"] = [
                        {
                            "timestamp": time_stamp_now,
                            "user_id": user["name"],
                            "comment": changelog_comment,
                        }
                    ]
                    # find race - always pick the latest start if several results
                    start_entries = await StartAdapter().get_start_entries_by_bib(
                        user["token"], event["id"], int(bib)
                    )
                    if start_entries:
                        start_entry = start_entries[len(start_entries) - 1]
                        race_id = start_entry["race_id"]
                        race = await RaceplansAdapter().get_race_by_id(
                            user["token"], race_id
                        )
                        request_body["name"] = start_entry["name"]
                        request_body["club"] = start_entry["club"]
                        request_body["race_id"] = race_id
                        request_body["race"] = (
                            f"{race['raceclass']}-{race['round']}{race['index']}{race['heat']}"
                        )

                    await TimeEventsService().create_start_time_event(
                        user["token"], request_body
                    )
                    i += 1
                    informasjon += f" {request_body['bib']}-{changelog_comment}. "
            except Exception as e:
                informasjon += f"Error: {e}"

    return f" {i} registreringer lagret. {informasjon}"


async def create_start_time_events_for_race(user: dict, event: dict, form: dict) -> str:
    """Extract form data and create time_events for start."""
    time_stamp_now = EventsAdapter().get_local_time(event, "log")
    request_body = {
        "id": "",
        "bib": 0,
        "event_id": form["event_id"],
        "race": form["race"],
        "race_id": form["race_id"],
        "timing_point": "",
        "rank": 0,
        "registration_time": time_stamp_now,
        "next_race": "",
        "next_race_id": "",
        "next_race_position": 0,
        "status": "OK",
        "changelog": [],
    }

    i = 0
    for key, value in form.items():
        if key.startswith("form_start_"):
            request_body["bib"] = int(key[11:])
            if value == "DNS":
                # register DNS
                request_body["timing_point"] = "DNS"
                changelog_comment = "DNS registrert. "
            else:
                # register normal start
                request_body["timing_point"] = "Start"
                changelog_comment = "Start registrert. "
            i += 1
            request_body["changelog"] = [
                {
                    "timestamp": time_stamp_now,
                    "user_id": user["name"],
                    "comment": changelog_comment,
                }
            ]
            await TimeEventsService().create_start_time_event(
                user["token"], request_body
            )
    return f" {i} registreringer lagret. "
