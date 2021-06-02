"""Resource module for main view."""
import logging

from aiohttp import web
import aiohttp_jinja2


class Main(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get route function that return the index page."""
        # TODO - get list of events
        logging.debug("Get all events")
        return await aiohttp_jinja2.render_template_async(
            "index.html",
            self.request,
            {
                "lopsinfo": "Langrenn startside",
            },
        )
