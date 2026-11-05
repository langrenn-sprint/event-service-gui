"""Resource module for login view."""

import logging

import aiohttp_jinja2
from aiohttp import web
from aiohttp_session import new_session

from event_service_gui.adapters import UserAdapter

from .utils import safe_next_path


class Login(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get route function that return the index page."""
        username = ""
        try:
            informasjon = self.request.rel_url.query["informasjon"]
        except Exception:
            informasjon = ""
        try:
            event_id = self.request.rel_url.query["event_id"]
        except Exception:
            event_id = ""
        # page to return to after login, see check_login
        next_path = safe_next_path(self.request.rel_url.query.get("next")) or ""

        event = {"name": "Administrasjon", "organiser": "Ikke valgt"}

        return await aiohttp_jinja2.render_template_async(
            "login.html",
            self.request,
            {
                "lopsinfo": "Login",
                "event": event,
                "event_id": event_id,
                "informasjon": informasjon,
                "next": next_path,
                "username": username,
            },
        )

    async def post(self) -> web.Response:
        """Get route function that return the index page."""
        informasjon = ""
        result = 0
        form = await self.request.post()
        next_path = safe_next_path(str(form.get("next", "")))
        try:
            event_id = self.request.rel_url.query["event_id"]
            logging.debug(f"Event: {event_id}")
        except Exception:
            event_id = ""
        try:
            session = await new_session(self.request)
            result = await UserAdapter().login(
                str(form["username"]), str(form["password"]), session
            )
            if result == 200:
                informasjon = "Innlogget!"
            else:
                informasjon = f"Innlogging feilet - {result}"

        except Exception as e:
            logging.exception("Error")
            informasjon = f"Det har oppstått en feil - {e.args}."
            result = 400

        event = {"name": "Langrenn", "organiser": "Ikke valgt"}
        if result != 200:
            return await aiohttp_jinja2.render_template_async(
                "login.html",
                self.request,
                {
                    "lopsinfo": "Login resultat",
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "next": next_path or "",
                },
            )
        if next_path:
            return web.HTTPSeeOther(location=next_path)
        return web.HTTPSeeOther(location=f"/?informasjon={informasjon}")
