"""Resource module for login view."""
import logging

from aiohttp import web
import aiohttp_jinja2
from aiohttp_session import new_session

from event_service_gui.services import LoginAdapter


class Login(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get route function that return the index page."""
        try:
            event = self.request.rel_url.query["event"]
        except Exception:
            event = ""

        return await aiohttp_jinja2.render_template_async(
            "login.html",
            self.request,
            {
                "lopsinfo": "Login",
                "event": event,
            },
        )

    async def post(self) -> web.Response:
        """Get route function that return the index page."""
        informasjon = ""
        result = 0
        logging.debug(f"Login: {self}")

        try:
            form = await self.request.post()
            try:
                eventid = self.request.rel_url.query["eventid"]
                logging.debug(f"Event: {eventid}")
            except Exception:
                eventid = ""

            # Perform login
            session = await new_session(self.request)
            result = await LoginAdapter().login(
                form["username"], form["password"], session
            )
            if result != 200:
                informasjon = "Innlogging feilet"

        except Exception:
            logging.error("Error handling post - login")

        if result != 200:
            return await aiohttp_jinja2.render_template_async(
                "login.html",
                self.request,
                {
                    "lopsinfo": "Login resultat",
                    "eventid": eventid,
                    "informasjon": informasjon,
                },
            )
        elif eventid != "":
            return web.HTTPSeeOther(location=f"/events?event={eventid}")
        else:
            return web.HTTPSeeOther(location="/")
