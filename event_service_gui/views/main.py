"""Resource module for main view."""

import json
import logging

import aiohttp_jinja2
from aiohttp import web

from event_service_gui.adapters import EventsAdapter

from .utils import check_login_open, error_text, get_event, is_login_error, raise_error


class Main(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get function that return the index page."""
        try:
            informasjon = self.request.rel_url.query["informasjon"]
        except Exception:
            informasjon = ""
        try:
            action = self.request.rel_url.query["action"]
        except Exception:
            action = ""

        try:
            user = await check_login_open(self)

            if action == "REST":
                events = await EventsAdapter().get_all_events(user["token"])
                body = json.dumps(events, default=str, ensure_ascii=False)
                return web.Response(
                    status=200, body=body, content_type="application/json"
                )
            event = await get_event(user["token"], "")

            events = await EventsAdapter().get_all_events(user["token"])
            logging.debug(f"Events: {events}")

            return await aiohttp_jinja2.render_template_async(
                "index.html",
                self.request,
                {
                    "lopsinfo": "Startside",
                    "event": event,
                    "event_id": "",
                    "events": events,
                    "informasjon": informasjon,
                    "username": user["name"],
                },
            )
        except Exception as e:
            if is_login_error(e):
                raise_error(self, e)
            # The other pages send errors here, so show an error page instead:
            logging.exception("Error on the main page")
            return await aiohttp_jinja2.render_template_async(
                "error.html",
                self.request,
                {"informasjon": error_text(e)},
                status=web.HTTPInternalServerError.status_code,
            )
