"""Resource module for main view."""
import logging
import os

from aiohttp import web
import aiohttp_jinja2

from event_service_gui.services import EventsAdapter
from .utils import (
    check_login,
    create_default_competition_format,
    get_event,
    get_local_time,
)


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
                    "sprint_race_matrix": default_sprint_matrix(),
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
                informasjon = await create_default_competition_format(user["token"])
            elif "update_sprint_config" in form.keys():
                new_config = get_sprint_matrix_from_form(form)  # type: ignore
                informasjon = f"TODO - tjenesten er ikke implementert ennå {new_config}"
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


def default_sprint_matrix() -> list:
    """Get settings for sprint competition set-up."""
    race_settings = [
        {
            "max_no_of_contestants": 8,
            "no_of_heat": {"Q": 1, "FA": 1},
            "rule": {"Q": {"FA": float("inf")}},
        },
        {
            "max_no_of_contestants": 16,
            "no_of_heat": {"Q": 2, "FA": 1, "FB": 1},
            "rule": {"Q": {"FA": 4, "FB": float("inf")}},
        },
        {
            "max_no_of_contestants": 24,
            "no_of_heat": {"Q": 3, "SA": 2, "FA": 1, "FB": 1, "FC": 1},
            "rule": {"Q": {"SA": 5, "FC": float("inf")}, "SA": {"FA": 4, "FB": 4}},
        },
        {
            "max_no_of_contestants": 32,
            "no_of_heat": {"Q": 4, "SA": 2, "SC": 2, "FA": 1, "FB": 1, "FC": 1},
            "rule": {
                "Q": {"SA": 4, "SC": float("inf")},
                "SA": {"FA": 4, "FB": 4},
                "SC": {"FC": 4},
            },
        },
        {
            "max_no_of_contestants": 40,
            "no_of_heat": {"Q": 6, "SA": 4, "SC": 2, "FA": 1, "FB": 1, "FC": 1},
            "rule": {
                "Q": {"SA": 4, "SC": float("inf")},
                "SA": {"FA": 2, "FB": 2},
                "SC": {"FC": 4},
            },
        },
        {
            "max_no_of_contestants": 48,
            "no_of_heat": {"Q": 6, "SA": 4, "SC": 4, "FA": 1, "FB": 1, "FC": 1},
            "rule": {
                "Q": {"SA": 4, "SC": float("inf")},
                "SA": {"FA": 2, "FB": 2},
                "SC": {"FC": 2},
            },
        },
        {
            "max_no_of_contestants": 56,
            "no_of_heat": {"Q": 7, "SA": 4, "SC": 4, "FA": 1, "FB": 1, "FC": 1},
            "rule": {
                "Q": {"SA": 4, "SC": float("inf")},
                "SA": {"FA": 2, "FB": 2},
                "SC": {"FC": 2},
            },
        },
        {
            "max_no_of_contestants": 80,
            "no_of_heat": {"Q": 8, "SA": 4, "SC": 4, "FA": 1, "FB": 1, "FC": 1},
            "rule": {
                "Q": {"SA": 4, "SC": float("inf")},
                "SA": {"FA": 2, "FB": 2},
                "SC": {"FC": 2},
            },
        },
    ]
    return race_settings


def get_sprint_matrix_from_form(form: dict) -> list:
    """Get settings for sprint competition set-up."""
    race_settings = []
    for i in range(50):
        if f"max_no_of_contestants_{i}" in form.keys():
            new_no_of_heat = {}
            new_rule = {}
            new_set = {
                "max_no_of_contestants": int(form[f"max_no_of_contestants_{i}"]),
            }
            new_no_of_heat["Q"] = int(form[f"no_of_heat_Q_{i}"])
            if len(form[f"no_of_heat_SC_{i}"]) > 0:
                new_no_of_heat["SC"] = int(form[f"no_of_heat_SC_{i}"])
            if len(form[f"no_of_heat_SA_{i}"]) > 0:
                new_no_of_heat["SA"] = int(form[f"no_of_heat_SA_{i}"])
            if len(form[f"no_of_heat_FC_{i}"]) > 0:
                new_no_of_heat["FC"] = int(form[f"no_of_heat_FC_{i}"])
            if len(form[f"no_of_heat_FB_{i}"]) > 0:
                new_no_of_heat["FB"] = int(form[f"no_of_heat_FB_{i}"])
            new_no_of_heat["FA"] = int(form[f"no_of_heat_FA_{i}"])

            new_rule["Q"] = str(form[f"rule_Q_{i}"])
            if len(form[f"rule_SC_{i}"]) > 0:
                new_rule["SC"] = str(form[f"rule_SC_{i}"])  # type: ignore
            if len(form[f"rule_SA_{i}"]) > 0:
                new_rule["SA"] = str(form[f"rule_SA_{i}"])  # type: ignore

            new_set["no_of_heat"] = new_no_of_heat  # type: ignore
            new_set["rule"] = new_rule  # type: ignore

            race_settings.append(new_set)
    return race_settings


def get_other_settings() -> dict:
    """Get other global settings."""
    other_settings = {}
    other_settings["time_zone_offset"] = int(os.getenv("TIME_ZONE_OFFSET", 1))
    return other_settings
