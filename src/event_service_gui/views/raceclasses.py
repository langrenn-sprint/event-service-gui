"""Resource module for main view."""
import logging

from aiohttp import web
import aiohttp_jinja2
from aiohttp_session import get_session

from event_service_gui.services import EventsAdapter
from event_service_gui.services import RaceclassesAdapter
from event_service_gui.services import UserAdapter


class Raceclasses(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get route function that return the index page."""
        informasjon = ""
        try:
            eventid = self.request.rel_url.query["eventid"]
        except Exception:
            informasjon = "Ingen event valgt."
            return web.HTTPSeeOther(location=f"/?informasjon={informasjon}")

        # check login
        username = ""
        session = await get_session(self.request)
        loggedin = UserAdapter().isloggedin(session)
        if not loggedin:
            return web.HTTPSeeOther(location=f"/login?event={eventid}")
        username = str(session["username"])
        token = str(session["token"])

        event = await EventsAdapter().get_event(token, eventid)

        try:
            informasjon = self.request.rel_url.query["informasjon"]
        except Exception:
            informasjon = ""
        klasse = {}
        try:
            action = self.request.rel_url.query["action"]
            if action == "update_one":
                id = self.request.rel_url.query["id"]
                klasse = await RaceclassesAdapter().get_ageclass(token, id)

        except Exception:
            action = ""
        logging.debug(f"Action: {action}")

        ageclasses = await RaceclassesAdapter().get_ageclasses(token, eventid)

        return await aiohttp_jinja2.render_template_async(
            "raceclasses.html",
            self.request,
            {
                "action": action,
                "ageclasses": ageclasses,
                "event": event,
                "eventid": eventid,
                "informasjon": informasjon,
                "lopsinfo": "Klasser",
                "klasse": klasse,
                "username": username,
            },
        )

    async def post(self) -> web.Response:
        """Post route function that updates a collection of klasses."""
        # check login
        session = await get_session(self.request)
        loggedin = UserAdapter().isloggedin(session)
        if not loggedin:
            return web.HTTPSeeOther(location="/login")
        token = str(session["token"])

        informasjon = ""
        try:
            form = await self.request.post()
            logging.debug(f"Form {form}")
            eventid = str(form["eventid"])

            # Update
            if "update_one" in form.keys():
                eventid = str(form["eventid"])
                request_body = {
                    "age_class": str(form["age_class"]),
                    "distance": str(form["distance"]),
                    "event_id": eventid,
                    "order": str(form["order"]),
                    "race_class": str(form["race_class"]),
                    "contestants": str(form["contestants"]),
                }

                result = await RaceclassesAdapter().update_ageclass(
                    token, eventid, request_body
                )
                informasjon = f"Informasjon er oppdatert - {result}"
            # Create classes from list of contestants
            elif "generate_ageclasses" in form.keys():
                informasjon = await RaceclassesAdapter().generate_ageclasses(
                    token, eventid
                )
            elif "refresh_contestants" in form.keys():
                informasjon = "TODO: Antall deltakere pr. klasse er oppdatert"

        except Exception as e:
            logging.error(f"Error: {e}")
            informasjon = f"Det har oppstått en feil - {e.args}."

        return web.HTTPSeeOther(
            location=f"/raceclasses?eventid={eventid}&informasjon={informasjon}"
        )
