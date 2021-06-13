"""Resource module for main view."""
import logging

from aiohttp import web
import aiohttp_jinja2

from event_service_gui.services import ContestantsAdapter


class Contestants(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get route function that return the index page."""
        try:
            event = self.request.rel_url.query["event"]
            logging.debug(f"Event: {event}")
        except Exception:
            event = ""

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
            },
        )
