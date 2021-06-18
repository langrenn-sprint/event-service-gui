"""Resource module for main view."""
import logging

from aiohttp import web
import aiohttp_jinja2

from event_service_gui.services import EventsAdapter


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

    async def post(self) -> web.Response:
        """Post route function that creates a collection of klasses."""
        # check for new events
        informasjon = ""
        try:
            form = await self.request.post()
            logging.info(f"Form {form}")

            # Create new event
            if "Create" in form.keys():
                name = form["Name"]
                id = await EventsAdapter().create_event(name)
                if id == "201":
                    informasjon = f"Opprettet nytt arrangement - {name}"

        except Exception:
            logging.error("Error handling post - events")

        return await aiohttp_jinja2.render_template_async(
            "events.html",
            self.request,
            {
                "lopsinfo": "Arrangement",
                "event": name,
                "informasjon": informasjon,
            },
        )
