"""Resource module for main view."""
import logging

from aiohttp import web
import aiohttp_jinja2

from event_service_gui.services import RaceclassesAdapter


class Raceclasses(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get route function that return the index page."""
        try:
            event = self.request.rel_url.query["event"]
            logging.debug(f"Event: {event}")
        except Exception:
            event = ""

        # TODO - get list of raceclasses
        raceclasses = await RaceclassesAdapter().get_all_raceclasses()
        logging.debug(f"Raceclasses: {raceclasses}")
        return await aiohttp_jinja2.render_template_async(
            "raceclasses.html",
            self.request,
            {
                "lopsinfo": "Løpsklasser",
                "raceclasses": raceclasses,
                "event": event,
            },
        )
