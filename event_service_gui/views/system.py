"""Resource module for system view."""

import logging

import aiohttp_jinja2
from aiohttp import web

from event_service_gui.services import SystemStatusService

from .utils import check_admin


class System(web.View):
    """Class representing the system view: instance, backup and database status."""

    async def get(self) -> web.Response:
        """Get route function that returns the system page."""
        informasjon = self.request.rel_url.query.get("informasjon", "")
        user = await check_admin(self)
        try:
            system_info = SystemStatusService().get_system_info()
        except Exception as e:
            logging.exception("Error reading system status")
            system_info = {"has_status": False, "warnings": [], "error": str(e)}

        event = {"name": "Systemstatus", "organiser": "Ikke valgt"}
        return await aiohttp_jinja2.render_template_async(
            "system.html",
            self.request,
            {
                "lopsinfo": "System",
                "event": event,
                "event_id": "",
                "informasjon": informasjon,
                "username": user["name"],
                "system": system_info,
            },
        )
