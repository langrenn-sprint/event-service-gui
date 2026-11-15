"""Resource module for main view."""

import logging

import aiohttp_jinja2
from aiohttp import web

from event_service_gui.adapters import ConfigAdapter

from .utils import check_login, get_event


class Config(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get function that return the index page."""
        try:
            informasjon = self.request.rel_url.query["informasjon"]
        except Exception:
            informasjon = ""
        try:
            event_id = self.request.rel_url.query["event_id"]
        except Exception:
            event_id = ""
        try:
            action = self.request.rel_url.query["action"]
        except Exception:
            action = ""

        user = await check_login(self)
        try:
            event = await get_event(user["token"], event_id)

            try:
                event_config = await ConfigAdapter().get_all_configs(
                    user["token"], event_id
                )
            except Exception as e:
                event_config = []
                informasjon += f" Feil ved innlasting av config. {e}"
                logging.exception(informasjon)
            return await aiohttp_jinja2.render_template_async(
                "config.html",
                self.request,
                {
                    "action": action,
                    "event": event,
                    "event_id": event_id,
                    "event_config": event_config,
                    "informasjon": informasjon,
                    "username": user["name"],
                },
            )
        except Exception as e:
            logging.exception("Error. Redirect to login page.")
            raise web.HTTPSeeOther(location=f"/login?informasjon={e}") from e

    async def post(self) -> web.Response:
        """Post route function that updates video events."""
        informasjon = ""
        form = dict(await self.request.post())
        user = await check_login(self)
        event_id = str(form["event_id"])
        try:
            if "update_one" in form:
                key = str(form["key"])
                await ConfigAdapter().update_config(
                    user["token"], event_id, key, str(form["value"])
                )
                informasjon = "Suksess. Informasjon er oppdatert."
        except Exception as e:
            informasjon = f"Det har oppstått en feil: {e}"
            logging.exception("Config update")
        raise web.HTTPSeeOther(
            location=f"/config?action=edit_mode&event_id={event_id}&informasjon={informasjon}"
        )
