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
        result = 0
        logging.debug(f"Login: {self}")

        try:
            form = await self.request.post()
            try:
                event = self.request.rel_url.query["event"]
            except Exception:
                event = ""

            # Perform login
            result = await LoginAdapter().login(form["username"], form["password"])
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
                    "event": event,
                    "informasjon": informasjon,
                },
            )
        else:
            return await aiohttp_jinja2.render_template_async(
                "events.html",
                self.request,
                {
                    "lopsinfo": "Arrangement",
                    "event": event,
                },
            )
