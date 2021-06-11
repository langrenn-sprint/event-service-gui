"""Resource module for main view."""
import logging

from aiohttp import web
import aiohttp_jinja2

from event_service_gui.services import EventsAdapter


class Events(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get route function that return the index page."""
        # TODO - get list of events
        events = await EventsAdapter().get_all_events()
        logging.debug(f"Events: {events}")
        return await aiohttp_jinja2.render_template_async(
            "events.html",
            self.request,
            {
                "lopsinfo": "Arrangement",
                "events": events,
            },
        )
