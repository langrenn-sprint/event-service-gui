"""Resource module for main view."""
import logging

from aiohttp import web
import aiohttp_jinja2
from aiohttp_session import get_session

from event_service_gui.services import EventsAdapter
from event_service_gui.services import LoginAdapter


class Events(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get route function that return the events page."""
        try:
            eventid = self.request.rel_url.query["eventid"]
        except Exception:
            eventid = ""
        try:
            informasjon = self.request.rel_url.query["informasjon"]
        except Exception:
            informasjon = ""

        # check login
        username = ""
        session = await get_session(self.request)
        loggedin = LoginAdapter().isloggedin(session)
        if not loggedin:
            return web.HTTPSeeOther(location=f"/login?event={eventid}")
        username = session["username"]
        token = session["token"]

        logging.debug(f"get_event {eventid}")
        event = await EventsAdapter().get_event(token, eventid)

        return await aiohttp_jinja2.render_template_async(
            "events.html",
            self.request,
            {
                "lopsinfo": "Arrangement",
                "event": event,
                "eventid": eventid,
                "informasjon": informasjon,
                "username": username,
            },
        )

    async def post(self) -> web.Response:
        """Post route function that creates a collection of klasses."""
        # check for new events
        # check login
        session = await get_session(self.request)
        loggedin = LoginAdapter().isloggedin(session)
        if not loggedin:
            return web.HTTPSeeOther(location="/login")
        token = session["token"]

        informasjon = ""
        try:
            form = await self.request.post()
            logging.debug(f"Form {form}")
            request_body = {
                "name": form["name"],
                "date": form["date"],
                "organiser": form["organiser"],
            }

            # Create new event
            if "create" in form.keys():
                id = await EventsAdapter().create_event(token, request_body)
                informasjon = f"Opprettet nytt arrangement,  id {id}"
            elif "update" in form.keys():
                id = form["id"]
                res = await EventsAdapter().update_event(token, id, request_body)
                if res == 201:
                    informasjon = "Arrangementinformasjon er oppdatert."
                else:
                    informasjon = f"En feil oppstod {res}."
        except Exception:
            logging.error(f"Error handling post - {form}")
            informasjon = "Det har oppstått en feil."
            return web.HTTPSeeOther(location=f"/?informasjon={informasjon}")

        return web.HTTPSeeOther(
            location=f"/events?eventid={id}&informasjon={informasjon}"
        )
