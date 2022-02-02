"""Resource module for main view."""
import logging
import os

from aiohttp import web
import aiohttp_jinja2

from event_service_gui.services import EventsAdapter
from .utils import check_login, get_event, get_local_time


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
            other_settings = get_other_settings()
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
                    "local_time": get_local_time(
                        "HH:MM", other_settings["time_zone_offset"]
                    ),
                    "other_settings": other_settings,
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
                    "time_between_groups": "00:05:00",
                    "intervals": "00:00:30",
                    "max_no_of_contestants_in_raceclass": 9999,
                    "max_no_of_contestants_in_race": 9999,
                    "datatype": "interval_start",
                }
                informasjon = await EventsAdapter().create_competition_format(
                    user["token"], request_body
                )
                request_body = {
                    "name": "Individual Sprint",
                    "starting_order": "Heat Start",
                    "start_procedure": "Draw",
                    "time_between_groups": "00:15:00",
                    "time_between_rounds": "00:03:00",
                    "time_between_heats": "00:01:30",
                    "max_no_of_contestants_in_raceclass": 80,
                    "max_no_of_contestants_in_race": 10,
                    "datatype": "individual_sprint",
                }
                informasjon = await EventsAdapter().create_competition_format(
                    user["token"], request_body
                )
            elif "update" in form.keys():
                if form["datatype"] == "individual_sprint":
                    request_body = {
                        "id": str(form["id"]),
                        "name": str(form["name"]),
                        "starting_order": str(form["starting_order"]),
                        "start_procedure": str(form["start_procedure"]),
                        "datatype": str(form["datatype"]),
                        "time_between_groups": str(form["time_between_groups"]),
                        "time_between_rounds": str(form["time_between_rounds"]),
                        "time_between_heats": str(form["time_between_heats"]),
                        "max_no_of_contestants_in_raceclass": int(
                            form["max_no_of_contestants_in_raceclass"]  # type: ignore
                        ),
                        "max_no_of_contestants_in_race": int(
                            form["max_no_of_contestants_in_race"]  # type: ignore
                        ),
                    }
                else:
                    request_body = {
                        "id": str(form["id"]),
                        "name": str(form["name"]),
                        "starting_order": str(form["starting_order"]),
                        "start_procedure": str(form["start_procedure"]),
                        "time_between_groups": str(form["time_between_groups"]),
                        "intervals": str(form["intervals"]),
                        "max_no_of_contestants_in_raceclass": int(
                            form["max_no_of_contestants_in_raceclass"]  # type: ignore
                        ),
                        "max_no_of_contestants_in_race": int(
                            form["max_no_of_contestants_in_race"]  # type: ignore
                        ),
                        "datatype": str(form["datatype"]),
                    }

                informasjon = await EventsAdapter().update_competition_format(
                    user["token"], request_body
                )
        except Exception as e:
            logging.error(f"Error: {e}")
            informasjon = f"Det har oppstått en feil - {e.args}."
            error_reason = str(e)
            if error_reason.startswith("401"):
                return web.HTTPSeeOther(
                    location=f"/login?informasjon=Ingen tilgang, vennligst logg inn på nytt. {e}"
                )

        return web.HTTPSeeOther(location=f"/settings?informasjon={informasjon}")


def get_other_settings() -> dict:
    """Check loging and return user credentials."""
    other_settings = {}
    other_settings["time_zone_offset"] = int(os.getenv("TIME_ZONE_OFFSET", 1))
    return other_settings
