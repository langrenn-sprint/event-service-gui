"""Resource module for main view."""
import logging

from aiohttp import web
import aiohttp_jinja2

from event_service_gui.services import SchedulesAdapter


class Schedules(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get route function that return the index page."""
        # TODO - get list of schedules
        schedules = await SchedulesAdapter().get_all_schedules()
        logging.debug(f"Schedules: {schedules}")
        return await aiohttp_jinja2.render_template_async(
            "schedules.html",
            self.request,
            {
                "lopsinfo": "Kjøreplan",
                "schedules": schedules,
            },
        )
