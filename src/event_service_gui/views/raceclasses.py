"""Resource module for main view."""
import logging

from aiohttp import web
import aiohttp_jinja2

from event_service_gui.services import RaceclassesAdapter


class Raceclasses(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get route function that return the index page."""
        # TODO - get list of raceclasses
        raceclasses = await RaceclassesAdapter().get_all_raceclasses()
        logging.debug(f"Raceclasses: {raceclasses}")
        return await aiohttp_jinja2.render_template_async(
            "raceclasses.html",
            self.request,
            {
                "lopsinfo": "Løpsklasser",
                "raceclasses": raceclasses,
            },
        )
