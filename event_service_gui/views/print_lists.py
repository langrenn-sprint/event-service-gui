"""Resource module for live resources."""

import logging

import aiohttp_jinja2
from aiohttp import web

from event_service_gui.adapters import (
    RaceclassesAdapter,
    RaceclassResultsAdapter,
    RaceplansAdapter,
)

from .utils import (
    check_login_open,
    get_event,
    get_qualification_text,
    get_raceplan_summary,
    get_races_for_print,
    get_races_for_round_result,
)


class PrintLists(web.View):
    """Class representing the printable heat lists view."""

    async def get(self) -> web.Response:
        """Get route function that return the livelister page."""
        informasjon = ""
        try:
            action = self.request.rel_url.query["action"]
        except Exception:
            action = ""

        show_graphics = True
        try:
            _show = self.request.rel_url.query["show_graphics"]
            if _show in ["False", "false"]:
                show_graphics = False
        except Exception:
            logging.debug("Missing param ignored")

        try:
            user = await check_login_open(self)
            event_id = self.request.rel_url.query["event_id"]
            event = await get_event(user["token"], event_id)

            races = []
            raceplan_summary = []
            resultlists = []
            html_template = "print_lists.html"
            try:
                valgt_klasse = self.request.rel_url.query["klasse"]
            except Exception:
                valgt_klasse = ""
            try:
                valgt_runde = self.request.rel_url.query["runde"]
            except Exception:
                valgt_runde = ""

            raceclasses = await RaceclassesAdapter().get_raceclasses(
                user["token"], event_id
            )
            if valgt_klasse:
                _tmp_races = await RaceplansAdapter().get_races_by_racesclass(
                    user["token"], event_id, valgt_klasse
                )
            else:
                _tmp_races = await RaceplansAdapter().get_all_races(
                    user["token"], event_id
                )
            races = await get_races(
                user,
                action,
                valgt_klasse,
                valgt_runde,
                _tmp_races,
                raceclasses,
            )
            if len(races) == 0:
                informasjon = "Ingen kjøreplaner funnet."

            if action == "raceplan":
                html_template = "print_raceplan.html"
                raceplan_summary = get_raceplan_summary(_tmp_races, raceclasses)
            elif action in ["result", "result_shuffled"]:
                html_template = "print_results.html"
                i_keep_first = 0
                try:
                    i_keep_first = int(self.request.rel_url.query["keep_first"])
                except Exception:
                    logging.debug("Missing param ignored")
                try:
                    resultlists = await get_resultlists(
                        event_id,
                        action,
                        valgt_klasse,
                        i_keep_first,
                    )
                except Exception:
                    informasjon = "Ingen resultatlister funnet."
                    logging.exception(informasjon)

            """Get route function."""
            return await aiohttp_jinja2.render_template_async(
                html_template,
                self.request,
                {
                    "action": action,
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "valgt_klasse": valgt_klasse,
                    "valgt_runde": valgt_runde,
                    "raceclasses": raceclasses,
                    "raceplan_summary": raceplan_summary,
                    "races": races,
                    "resultlists": resultlists,
                    "show_graphics": show_graphics,
                    "username": user["name"],
                },
            )
        except Exception as e:
            logging.exception("Error. Redirect to main page.")
            raise web.HTTPSeeOther(location=f"/?informasjon={e}") from e


async def get_resultlists(
    event_id: str,
    action: str,
    valgt_klasse: str,
    i_keep_first: int,
) -> list:
    """Get resultlists to display."""
    resultlists = []
    if valgt_klasse:
        if action == "result_shuffled":
            resultlist = await RaceclassResultsAdapter().get_raceclass_result_shuffeled(
                event_id, valgt_klasse, i_keep_first
            )
        else:
            resultlist = await RaceclassResultsAdapter().get_raceclass_result(
                event_id, valgt_klasse
            )
        resultlists.append(resultlist)
    else:
        resultlists = await RaceclassResultsAdapter().get_all_raceclass_results(
            event_id
        )
    return resultlists


async def get_races(
    user: dict,
    action: str,
    valgt_klasse: str,
    valgt_runde: str,
    _tmp_races: list,
    raceclasses: list,
) -> list:
    """Get races to display - return sorted list."""
    races = []
    if action == "raceplan":
        for race in _tmp_races:
            if (race["raceclass"] == valgt_klasse) or (valgt_klasse == ""):
                race["next_race"] = get_qualification_text(race)
                race["start_time"] = race["start_time"][-8:]
                race["first_in_group"] = check_group_order(race, raceclasses)
                races.append(race)
    elif action.startswith("round_"):
        races = await get_races_for_round_result(
            user, _tmp_races, valgt_runde, valgt_klasse, action
        )
    else:
        if valgt_runde != "":
            races = [
                race for race in _tmp_races if valgt_runde in ["", race["round"]]
            ]
        else:
            races = _tmp_races
        races = await get_races_for_print(
            user, races, raceclasses, valgt_klasse, action
        )
    return races


def check_group_order(race: dict, raceclasses: list) -> bool:
    """Return true if race is first in group."""
    if race["round"] in ["Q", "R1"] and race["heat"] == 1:
        group_index = 0
        for raceclass in raceclasses:
            if race["raceclass"] == raceclass["name"]:
                return raceclass["group"] > group_index
            group_index = raceclass["group"]
    return False
