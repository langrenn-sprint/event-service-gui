"""Resource module for main view."""
import logging

from aiohttp import web
import aiohttp_jinja2
from aiohttp_session import get_session

from event_service_gui.services import EventsAdapter
from event_service_gui.services import LoginAdapter


class Main(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get function that return the index page."""
        try:
            informasjon = self.request.rel_url.query["informasjon"]
        except Exception:
            informasjon = ""

        # check login
        username = ""
        session = await get_session(self.request)
        loggedin = LoginAdapter().isloggedin(session)
        if not loggedin:
            return web.HTTPSeeOther(location="/login")
        username = session["username"]
        token = session["token"]

        events = await EventsAdapter().get_all_events(token)
        logging.debug(f"Events: {events}")
        return await aiohttp_jinja2.render_template_async(
            "index.html",
            self.request,
            {
                "lopsinfo": "Langrenn startside",
                "event": [],
                "eventid": "",
                "events": events,
                "informasjon": informasjon,
                "username": username,
            },
        )
