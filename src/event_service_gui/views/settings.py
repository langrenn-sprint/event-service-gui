"""Resource module for main view."""
import logging

from aiohttp import web
import aiohttp_jinja2

from event_service_gui.services import EventsAdapter
from .utils import check_login, get_event


class Settings(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get route function that return the settings page."""
        try:
            informasjon = self.request.rel_url.query["informasjon"]
        except Exception:
            informasjon = ""

        try:
            user = await check_login(self)
            event = await get_event(user["token"], "")
            event["name"] = "Globale innstillinger"

            competition_formats = await EventsAdapter().get_competition_formats(
                user["token"]
            )
            logging.debug(f"Format: {competition_formats}")

            return await aiohttp_jinja2.render_template_async(
                "settings.html",
                self.request,
                {
                    "competition_formats": competition_formats,
                    "event": event,
                    "event_id": "",
                    "informasjon": informasjon,
                    "lopsinfo": "Globale innstillinger",
                    "username": user["name"],
                },
            )
        except Exception as e:
            logging.error(f"Error: {e}. Redirect to main page.")
            return web.HTTPSeeOther(location=f"/?informasjon={e}")

    async def post(self) -> web.Response:
        """Post route function that creates a collection of klasses."""
        # check login
        user = await check_login(self)

        informasjon = ""
        try:
            form = await self.request.post()
            logging.debug(f"Form {form}")

            # Create default settings
            if "generate_default" in form.keys():

                # delete all old information
                competition_formats = await EventsAdapter().get_competition_formats(
                    user["token"]
                )
                for format in competition_formats:
                    informasjon = await EventsAdapter().delete_competition_format(
                        user["token"], format["id"]
                    )

                # then create new with default values
                request_body = {
                    "name": "Interval Start",
                    "starting_order": "Draw",
                    "start_procedure": "Interval Start",
                    "intervals": "00:00:30",
                }
                informasjon = await EventsAdapter().create_competition_format(
                    user["token"], request_body
                )
                request_body = {
                    "name": "Individual Sprint",
                    "starting_order": "Heat Start",
                    "start_procedure": "Draw",
                    "intervals": "00:02:00",
                }
                informasjon = await EventsAdapter().create_competition_format(
                    user["token"], request_body
                )
        except Exception as e:
            logging.error(f"Error: {e}")
            informasjon = f"Det har oppstått en feil - {e.args}."

        return web.HTTPSeeOther(location=f"/settings?informasjon={informasjon}")