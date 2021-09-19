"""Resource module for main view."""
import logging

from aiohttp import web
import aiohttp_jinja2
from aiohttp_session import get_session

from event_service_gui.services import EventsAdapter
from event_service_gui.services import SchedulesAdapter
from event_service_gui.services import UserAdapter


class Schedules(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get route function that return the index page."""
        informasjon = ""
        try:
            event_id = self.request.rel_url.query["event_id"]
        except Exception:
            event_id = ""

        # check login
        username = ""
        session = await get_session(self.request)
        try:
            loggedin = UserAdapter().isloggedin(session)
            if not loggedin:
                return web.HTTPSeeOther(location=f"/login?event={event_id}")
            username = str(session["username"])
            token = str(session["token"])

            # TODO - get list of schedules
            schedules = await SchedulesAdapter().get_all_schedules()
            event = await EventsAdapter().get_event(token, event_id)
            logging.debug(f"Schedules: {schedules}")
            return await aiohttp_jinja2.render_template_async(
                "schedules.html",
                self.request,
                {
                    "lopsinfo": "Kjøreplan",
                    "schedules": schedules,
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "username": username,
                },
            )
        except Exception as e:
            logging.error(f"Error: {e}. Starting new session.")
            session.invalidate()
            return web.HTTPSeeOther(location="/login")
