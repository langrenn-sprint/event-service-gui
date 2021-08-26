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
        try:
            informasjon = self.request.rel_url.query["informasjon"]
        except Exception:
            informasjon = ""
        try:
            edit_mode = False
            edit = self.request.rel_url.query["edit_mode"]
            if edit != "":
                edit_mode = True
        except Exception:
            edit_mode = False

        # check login
        username = ""
        session = await get_session(self.request)
        loggedin = UserAdapter().isloggedin(session)
        if not loggedin:
            return web.HTTPSeeOther(location=f"/login?event={eventid}")
        username = session["username"]
        token = session["token"]

        # TODO - get list of ageclasses
        event = await EventsAdapter().get_event(token, eventid)
        ageclasses = await RaceclassesAdapter().get_mongo(self.request.app["db"])
        return await aiohttp_jinja2.render_template_async(
            "raceclasses.html",
            self.request,
            {
                "lopsinfo": "Løpsklasser",
                "ageclasses": ageclasses,
                "edit_mode": edit_mode,
                "event": event,
                "eventid": eventid,
                "informasjon": informasjon,
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

        informasjon = ""
        try:
            form = await self.request.post()
            logging.debug(f"Form {form}")
            eventid = form["eventid"]

            # Create new event
            if "update" in form.keys():
                request_body = form
                result = await RaceclassesAdapter().update_mongo(
                    self.request.app["db"], request_body
                )
                informasjon = f"Informasjon er oppdatert {result}"

        except Exception as e:
            logging.error(f"Error: {e}")
            informasjon = f"Det har oppstått en feil - {e.args}."

        return web.HTTPSeeOther(
            location=f"/raceclasses?eventid={eventid}&informasjon={informasjon}&edit_mode=True"
        )
