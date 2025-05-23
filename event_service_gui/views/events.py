"""Resource module for main view."""

import logging

import aiohttp_jinja2
from aiohttp import web

from event_service_gui.services import CompetitionFormatAdapter, EventsAdapter

from .utils import check_login, create_default_competition_format, get_event


class Events(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get route function that return the events page."""
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
            action = ""

        try:
            user = await check_login(self)

            event = await get_event(user["token"], event_id)
            local_time_now = ""
            if event:
                local_time_now = EventsAdapter().get_local_time(event, "HH:MM")

            try:
                create_new = False
                new = self.request.rel_url.query["new"]
                if new != "":
                    create_new = True
            except Exception:
                create_new = False

            competition_formats = await get_competition_formats(user["token"])

            return await aiohttp_jinja2.render_template_async(
                "events.html",
                self.request,
                {
                    "action": action,
                    "competition_formats": competition_formats,
                    "create_new": create_new,
                    "local_time_now": local_time_now,
                    "lopsinfo": "Informasjon",
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "username": user["name"],
                },
            )
        except Exception as e:
            logging.exception("Error.. Redirect to main page.")
            return web.HTTPSeeOther(location=f"/?informasjon={e}")

    async def post(self) -> web.Response:
        """Post route function that creates a collection of klasses."""
        # check login
        user = await check_login(self)

        informasjon = ""
        action = ""
        event_id = ""
        try:
            form = await self.request.post()
            logging.debug(f"Form {form}")
            # Create new event
            if "create_manual" in form:
                request_body = {
                    "name": form["name"],
                    "date_of_event": form["date_of_event"],
                    "time_of_event": form["time_of_event"],
                    "timezone": form["timezone"],
                    "competition_format": form["competition_format"],
                    "organiser": form["organiser"],
                    "webpage": form["webpage"],
                    "information": form["information"],
                }
                event_id = await EventsAdapter().create_event(
                    user["token"], request_body
                )
                informasjon = f"Opprettet nytt arrangement,  event_id {event_id}"
                action = "next_contestants"
                info = f"action={action}&informasjon={informasjon}"
                return web.HTTPSeeOther(location=f"/tasks?event_id={event_id}&{info}")
            if "update" in form:
                # Update event
                event_id = str(form["event_id"])
                request_body = {
                    "name": form["name"],
                    "date_of_event": form["date_of_event"],
                    "time_of_event": form["time_of_event"],
                    "timezone": form["timezone"],
                    "competition_format": form["competition_format"],
                    "organiser": form["organiser"],
                    "webpage": form["webpage"],
                    "information": form["information"],
                    "time_between_heats": form["time_between_heats"],
                    "time_between_rounds": form["time_between_rounds"],
                    "max_no_of_contestants_in_race": form[
                        "max_no_of_contestants_in_race"
                    ],
                    "id": event_id,
                }
                res = await EventsAdapter().update_event(
                    user["token"], event_id, request_body
                )
                informasjon = f"Arrangementinformasjon er oppdatert {res}."
            elif "delete" in form:
                event_id = str(form["event_id"])
                res = await EventsAdapter().delete_event(user["token"], event_id)
                informasjon = f"Arrangement er slettet {res}."
                return web.HTTPSeeOther(location=f"/?informasjon={informasjon}")
        except Exception as e:
            logging.exception("Error")
            informasjon = f"Det har oppstått en feil - {e.args}."
            error_reason = str(e)
            if error_reason.startswith("401"):
                return web.HTTPSeeOther(
                    location=f"/login?informasjon=Ingen tilgang, vennligst logg inn på nytt. {e}"
                )

        info = f"action={action}&informasjon={informasjon}"
        return web.HTTPSeeOther(location=f"/events?event_id={event_id}&{info}")


async def get_competition_formats(token: str) -> list:
    """Get valid competation formats. Created default if none exist."""
    competition_formats = await CompetitionFormatAdapter().get_competition_formats(
        token
    )
    if len(competition_formats) == 0:
        await create_default_competition_format(token, "default_individual_sprint")
        competition_formats = await CompetitionFormatAdapter().get_competition_formats(
            token
        )
    return competition_formats
