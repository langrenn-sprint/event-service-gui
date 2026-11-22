"""Resource module for main view."""

import aiohttp_jinja2
from aiohttp import web

from event_service_gui.adapters import ConfigAdapter
from event_service_gui.adapters.config_adapter import NO_ACCESS_CONFIG, with_defaults

from .utils import (
    ADMIN_ROLE,
    check_login,
    error_message,
    get_event,
    raise_error,
)


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
                # Show all settings, also those not saved for the event yet,
                # so admin can change them:
                if event_id:
                    event_config = with_defaults(event_config)
            except Exception as e:
                event_config = []
                informasjon += f" {error_message(self, e)}"
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
            raise_error(self, e)

    async def post(self) -> web.Response:
        """Post route function that updates video events."""
        informasjon = ""
        form = dict(await self.request.post())
        user = await check_login(self)
        event_id = str(form["event_id"])
        try:
            if "update_one" in form:
                if user["role"] != ADMIN_ROLE:
                    informasjon = NO_ACCESS_CONFIG
                else:
                    key = str(form["key"])
                    await ConfigAdapter().update_config(
                        user["token"], event_id, key, str(form["value"])
                    )
                    informasjon = "Innstillingene er oppdatert."
        except web.HTTPForbidden as e:
            informasjon = str(e.reason)
        except Exception as e:
            informasjon = error_message(self, e)
        raise web.HTTPSeeOther(
            location=f"/config?action=edit_mode&event_id={event_id}&informasjon={informasjon}"
        )
