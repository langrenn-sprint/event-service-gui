"""Resource module for main view."""
import logging

from aiohttp import web
import aiohttp_jinja2


class Events(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get route function that return the events page."""
        try:
            event = self.request.rel_url.query["event"]
            logging.debug(f"Event: {event}")
        except Exception:
            event = ""

        return await aiohttp_jinja2.render_template_async(
            "events.html",
            self.request,
            {
                "lopsinfo": "Arrangement",
                "event": event,
            },
        )
