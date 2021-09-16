"""Resource module for main view."""
import logging

from aiohttp import web
import aiohttp_jinja2
from aiohttp_session import get_session

# from event_service_gui.services import DashboardAdapter
from event_service_gui.services import EventsAdapter
from event_service_gui.services import UserAdapter


class Dashboard(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get route function that return the dashboards page."""
        try:
            event_id = self.request.rel_url.query["event_id"]
        except Exception:
            event_id = ""
        try:
            informasjon = self.request.rel_url.query["informasjon"]
        except Exception:
            informasjon = ""
        try:
            create_new = False
            new = self.request.rel_url.query["new"]
            if new != "":
                create_new = True
        except Exception:
            create_new = False

        # check login
        username = ""
        session = await get_session(self.request)
        loggedin = UserAdapter().isloggedin(session)
        if not loggedin:
            return web.HTTPSeeOther(location=f"/login?event={event_id}")
        username = str(session["username"])
        token = str(session["token"])

        event = {"name": "Nytt arrangement", "organiser": "Ikke valgt"}
        if event_id != "":
            logging.debug(f"get_event {event_id}")
            event = await EventsAdapter().get_event(token, event_id)

        return await aiohttp_jinja2.render_template_async(
            "dashboard.html",
            self.request,
            {
                "create_new": create_new,
                "lopsinfo": "Dashboard",
                "event": event,
                "event_id": event_id,
                "informasjon": informasjon,
                "username": username,
            },
        )

    async def post(self) -> web.Response:
        """Post route function that creates a collection of klasses."""
        # check login
        session = await get_session(self.request)
        loggedin = UserAdapter().isloggedin(session)
        if not loggedin:
            return web.HTTPSeeOther(location="/login")
        # token = str(session["token"])

        informasjon = ""
        event_id = ""
        try:
            form = await self.request.post()
            logging.debug(f"Form {form}")

            # Create new event
            if "create_manual" in form.keys():
                informasjon = f"Opprettet nytt arrangement,  event_id {event_id}"
        except Exception as e:
            logging.error(f"Error: {e}")
            informasjon = f"Det har oppstått en feil - {e.args}."

        return web.HTTPSeeOther(
            location=f"/events?event_id={event_id}&informasjon={informasjon}"
        )
