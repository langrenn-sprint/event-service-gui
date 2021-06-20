"""Resource module for login view."""
import logging

from aiohttp import web
import aiohttp_jinja2

from event_service_gui.services import LoginAdapter


class Login(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get route function that return the index page."""
        logging.debug(f"Login: {self}")
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
        logging.debug(f"Login: {self}")

        try:
            form = await self.request.post()
            try:
                event = self.request.rel_url.query["event"]
            except Exception:
                event = ""

            # Perform login
            result = await LoginAdapter().login(form["username"], form["password"])
            if result == 401:
                informasjon = "Innlogging feilet"

        except Exception:
            logging.error("Error handling post - login")

        return await aiohttp_jinja2.render_template_async(
            "login.html",
            self.request,
            {
                "lopsinfo": "Login resultat",
                "event": event,
                "informasjon": informasjon,
            },
        )
