"""Resource module for system view."""

import logging

import aiohttp_jinja2
from aiohttp import web

from event_service_gui.services import SystemStatusService

from .utils import check_admin, check_admin_api


async def get_system_info() -> dict:
    """Get system info with live health check, or an error dict on failure."""
    try:
        return await SystemStatusService().get_live_system_info()
    except Exception as e:
        logging.exception("Error reading system status")
        return {"has_status": False, "warnings": [], "services": None, "error": str(e)}


class System(web.View):
    """Class representing the system view: instance, backup and database status."""

    async def get(self) -> web.Response:
        """Get route function that returns the system page."""
        informasjon = self.request.rel_url.query.get("informasjon", "")
        user = await check_admin(self)
        system_info = await get_system_info()

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


class SystemStatus(web.View):
    """Class representing the system status as JSON, polled by the system page."""

    async def get(self) -> web.Response:
        """Get route function that returns the same system info as the page."""
        await check_admin_api(self)
        system_info = await get_system_info()
        return web.json_response(system_info, headers={"Cache-Control": "no-store"})
