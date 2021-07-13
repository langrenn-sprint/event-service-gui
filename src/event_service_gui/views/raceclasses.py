"""Resource module for main view."""
import logging

from aiohttp import web
import aiohttp_jinja2
from aiohttp_session import get_session

from event_service_gui.services import RaceclassesAdapter
from event_service_gui.services import UserAdapter


class Raceclasses(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get route function that return the index page."""
        try:
            eventid = self.request.rel_url.query["eventid"]
        except Exception:
            eventid = ""

        # check login
        username = ""
        session = await get_session(self.request)
        loggedin = UserAdapter().isloggedin(session)
        if not loggedin:
            return web.HTTPSeeOther(location=f"/login?event={eventid}")
        username = session["username"]

        # TODO - get list of raceclasses
        raceclasses = await RaceclassesAdapter().get_all_raceclasses()
        logging.debug(f"Raceclasses: {raceclasses}")
        return await aiohttp_jinja2.render_template_async(
            "raceclasses.html",
            self.request,
            {
                "lopsinfo": "Løpsklasser",
                "raceclasses": raceclasses,
                "eventid": eventid,
                "username": username,
            },
        )
