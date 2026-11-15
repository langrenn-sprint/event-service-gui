"""Resource module for main view."""

import logging

import aiohttp_jinja2
from aiohttp import web

from event_service_gui.adapters import (
    EventsAdapter,
    RaceclassesAdapter,
)

from .utils import (
    check_login,
    get_event,
)


class PrintDash(web.View):
    """Dashboard view for print."""

    async def get(self) -> web.Response:
        """Get route function that return the dashboards page."""
        try:
            event_id = self.request.rel_url.query["event_id"]
        except Exception:
            event_id = ""
        try:
            informasjon = self.request.rel_url.query["informasjon"]
        except Exception:
            informasjon = ""

        user = await check_login(self)
        try:
            event = await get_event(user["token"], event_id)

            raceclasses = await RaceclassesAdapter().get_raceclasses(
                user["token"], event_id
            )

            return await aiohttp_jinja2.render_template_async(
                "print_dash.html",
                self.request,
                {
                    "lopsinfo": "Utskrifter",
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "local_time_now": EventsAdapter().get_local_time(event, "HH:MM"),
                    "raceclasses": raceclasses,
                    "username": user["name"],
                },
            )
        except Exception as e:
            logging.exception("Error. Redirect to main page.")
            raise web.HTTPSeeOther(location=f"/?informasjon={e}") from e
