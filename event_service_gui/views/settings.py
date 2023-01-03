"""Resource module for main view."""
import json
import logging

from aiohttp import web
import aiohttp_jinja2

from event_service_gui.services import CompetitionFormatAdapter
from .utils import (
    check_login,
    create_default_competition_format,
    get_event,
    get_qualification_text,
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
            competition_formats = (
                await CompetitionFormatAdapter().get_competition_formats(user["token"])
            )
            # enrich with qualification text
            for format in competition_formats:
                if format["datatype"] == "individual_sprint":
                    for race_config in format["race_config_ranked"]:
                        try:
                            from_to = race_config["from_to"]
                            next_race_q = {"round": "Q", "rule": from_to["Q"]["A"]}
                            race_config[
                                "next_race_desc"
                            ] = f"Q: {get_qualification_text(next_race_q)}"
                            next_race_sa = {"round": "SA", "rule": from_to["S"]["A"]}
                            race_config[
                                "next_race_desc"
                            ] += f" -- SA: {get_qualification_text(next_race_sa)}"
                            next_race_sc = {"round": "SC", "rule": from_to["S"]["C"]}
                            race_config[
                                "next_race_desc"
                            ] += f" -- SC: {get_qualification_text(next_race_sc)}"
                        except Exception as e:
                            logging.debug(e)

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
            if (
                "default_individual_sprint" in form.keys()
                or "default_individual_sprint_steinar" in form.keys()
                or "default_sprint_all_to_finals" in form.keys()
                or "default_individual_sprint_10" in form.keys()
            ):
                # delete all old information
                competition_formats = (
                    await CompetitionFormatAdapter().get_competition_formats(
                        user["token"]
                    )
                )
                for format in competition_formats:
                    informasjon = (
                        await CompetitionFormatAdapter().delete_competition_format(
                            user["token"], format["id"]
                        )
                    )
                # create new - for individual sprint and interval start
                for format in form.keys():
                    informasjon += await create_default_competition_format(
                        user["token"], format
                    )
                informasjon += await create_default_competition_format(
                    user["token"], "default_interval_start"
                )
            elif "update" in form.keys():

                if form["datatype"] == "individual_sprint":
                    rounds_ranked_classes = form["rounds_ranked_classes"].replace(
                        "'", '"'
                    )
                    rounds_non_ranked_classes = form[
                        "rounds_non_ranked_classes"
                    ].replace("'", '"')
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
                        "rounds_ranked_classes": json.loads(rounds_ranked_classes),
                        "rounds_non_ranked_classes": json.loads(
                            rounds_non_ranked_classes
                        ),
                        "race_config_ranked": get_config_from_form(form, "ranked"),
                        "race_config_non_ranked": get_config_from_form(
                            form, "non_ranked"
                        ),
                    }
                elif form["datatype"] == "interval_start":
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
                logging.info(request_body["race_config_ranked"])
                informasjon = (
                    await CompetitionFormatAdapter().update_competition_format(
                        user["token"], request_body
                    )
                )
        except Exception as e:
            logging.error(f"Error: {e}")
            informasjon = f"Det har oppstått en feil - {e}."
            error_reason = str(e)
            if error_reason.startswith("401"):
                return web.HTTPSeeOther(
                    location=f"/login?informasjon=Ingen tilgang, vennligst logg inn på nytt. {e}"
                )

        return web.HTTPSeeOther(location=f"/settings?informasjon={informasjon}")


def get_config_from_form(form: dict, rank_type: str) -> list:
    """Get settings for sprint race-config set-up."""
    race_settings = []
    for i in range(50):
        if f"{rank_type}_{i}_max_no_of_contestants" in form.keys():
            if form[f"{rank_type}_{i}_max_no_of_contestants"]:
                rounds = form[f"{rank_type}_{i}_rounds"].replace("'", '"')
                no_of_heats = form[f"{rank_type}_{i}_no_of_heats"].replace("'", '"')
                from_to = form[f"{rank_type}_{i}_from_to"].replace("'", '"')
                new_set = {
                    "max_no_of_contestants": int(
                        form[f"{rank_type}_{i}_max_no_of_contestants"]
                    ),
                    "rounds": json.loads(rounds),
                    "no_of_heats": json.loads(no_of_heats),
                    "from_to": json.loads(from_to),
                }
                race_settings.append(new_set)
    if form[f"{rank_type}_new_max_no_of_contestants"]:
        rounds = form[f"{rank_type}_new_rounds"].replace("'", '"')
        no_of_heats = form[f"{rank_type}_new_no_of_heats"].replace("'", '"')
        from_to = form[f"{rank_type}_new_from_to"].replace("'", '"')
        new_set = {
            "max_no_of_contestants": int(
                form[f"{rank_type}_new_max_no_of_contestants"]
            ),
            "rounds": json.loads(rounds),
            "no_of_heats": json.loads(no_of_heats),
            "from_to": json.loads(from_to),
        }
        race_settings.append(new_set)
    return race_settings
