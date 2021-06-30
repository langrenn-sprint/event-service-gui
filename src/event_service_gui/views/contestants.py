"""Resource module for main view."""
import logging

from aiohttp import web
import aiohttp_jinja2
from aiohttp_session import get_session

from event_service_gui.services import ContestantsAdapter, EventsAdapter, LoginAdapter


class Contestants(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get route function that return the index page."""
        try:
            id = self.request.rel_url.query["eventid"]

            # check login
            username = ""
            session = await get_session(self.request)
            loggedin = LoginAdapter().isloggedin(session)
            if not loggedin:
                return web.HTTPSeeOther(location=f"/login?eventid={id}")
            username = session["username"]
            token = session["token"]

            try:
                informasjon = self.request.rel_url.query["informasjon"]
            except Exception:
                informasjon = ""

            event = await EventsAdapter().get_event(token, id)

        except Exception:
            return web.HTTPSeeOther(location="/")

        # TODO - get list of contestants
        contestants = await ContestantsAdapter().get_all_contestants()
        logging.debug(f"Contestants: {contestants}")
        return await aiohttp_jinja2.render_template_async(
            "contestants.html",
            self.request,
            {
                "lopsinfo": "Deltakere",
                "contestants": contestants,
                "event": event,
                "eventid": id,
                "informasjon": informasjon,
                "username": username,
            },
        )

    async def post(self) -> web.Response:
        """Post route function that creates deltakerliste."""
        # check login
        session = await get_session(self.request)
        loggedin = LoginAdapter().isloggedin(session)
        if not loggedin:
            return web.HTTPSeeOther(location="/login")
        token = session["token"]

        informasjon = ""
        try:
            form = await self.request.post()
            logging.info(f"Form {form}")

            informasjon = "Deltakere ble registrert."

        except Exception:
            logging.error("Error handling post - deltakere")
            informasjon = "Det har oppstått en feil."
            return web.HTTPSeeOther(location=f"/?informasjon={informasjon}")

        return web.HTTPSeeOther(
            location=f"/contestants?eventid={id}&informasjon={informasjon}"
        )
