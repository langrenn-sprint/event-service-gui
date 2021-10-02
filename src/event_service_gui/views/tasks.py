"""Resource module for main view."""
import logging

from aiohttp import web
import aiohttp_jinja2

from .utils import check_login, get_event


class Tasks(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get route function that return the tasks page."""
        try:
            event_id = self.request.rel_url.query["event_id"]
        except Exception:
            event_id = ""
        try:
            informasjon = self.request.rel_url.query["informasjon"]
        except Exception:
            informasjon = ""

        try:
            user = await check_login(self)
            event = await get_event(user["token"], event_id)

            return await aiohttp_jinja2.render_template_async(
                "tasks.html",
                self.request,
                {
                    "lopsinfo": "Oppgaver",
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "username": user["name"],
                },
            )
        except Exception as e:
            logging.error(f"Error: {e}. Redirect to main page.")
            return web.HTTPSeeOther(location=f"/?informasjon={e}")
