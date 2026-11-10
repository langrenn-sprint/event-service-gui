"""Resource module for verificatoin of timing registration."""

import json
import logging
from dataclasses import dataclass

import aiohttp_jinja2
from aiohttp import web

from event_service_gui.adapters import (
    EventsAdapter,
    PhotosAdapter,
    RaceclassesAdapter,
    RaceplansAdapter,
    ResultAdapter,
)
from event_service_gui.services import (
    PhotoTimingService,
    RaceclassResultsService,
    TimeEventsService,
)

from .utils import (
    check_login,
    create_start,
    get_enrichced_startlist,
    get_event,
    get_finish_timings,
    get_foto_finish_for_race,
    get_qualification_text,
    get_race_kpis,
    get_raceplan_summary,
    login_location,
)


@dataclass
class ValgtRunde:
    """Class representing information for selected round."""

    klasse: str = ""
    runde: str = ""
    race_order: int = -1
    informasjon: str = ""


class ResultatEditNew(web.View):
    """Class representing the result edit view."""

    async def get(self) -> web.Response:
        """Get route function that return the passeringer page."""
        race = {}
        all_races = []
        raceplan_summary = []
        raceplan_kpis = []
        race_orders = {}

        valgt_runde = ValgtRunde()

        try:
            informasjon = self.request.rel_url.query["informasjon"]
            info_list = informasjon.split("<br>")
            informasjon = ""
        except Exception:
            informasjon = ""
            info_list = []

        user = await check_login(self)
        try:
            event_id = self.request.rel_url.query["event_id"]
            event = await get_event(user["token"], event_id)
            raceclasses = await RaceclassesAdapter().get_raceclasses(
                user["token"], event_id
            )

            # check if specific round is selected
            try:
                valgt_runde = await get_starting_now(
                    user, event, int(self.request.rel_url.query["heat"])
                )
                all_races = await RaceplansAdapter().get_races_by_racesclass(
                    user["token"], event["id"], valgt_runde.klasse
                )

            except Exception:
                # if race not is selected, use round and find first race
                try:
                    valgt_runde.klasse = self.request.rel_url.query["klasse"]
                    valgt_runde.runde = self.request.rel_url.query["runde"]
                    all_races = await RaceplansAdapter().get_races_by_racesclass(
                        user["token"], event["id"], valgt_runde.klasse
                    )

                    valgt_runde = find_order(valgt_runde, all_races)
                except Exception:
                    informasjon = f"Velg runde i menyen. {informasjon}"
                    logging.debug("Ingen runde valgt")

            if valgt_runde.race_order != -1:
                race = await RaceplansAdapter().get_race_by_order(
                    user["token"], event_id, valgt_runde.race_order
                )
            raceplan_summary = get_raceplan_summary(all_races, raceclasses)

            if not race or not race.get("id"):
                informasjon += " Ingen heat i denne runden."
            elif valgt_runde.klasse:
                foto = await PhotosAdapter().get_photos_by_race_id(
                    user["token"], race["id"]
                )
                race["next_race"] = get_qualification_text(race)
                # get start list detail
                race["startliste"] = await get_enrichced_startlist(user, race)
                race["finish_timings"] = await get_finish_timings(user, race["id"])
                race["photo_finish"] = get_foto_finish_for_race(race, foto)
                race["photo_start"] = get_foto_start_for_race(race, foto)
                race["photo_bib_rank"] = get_finish_rank_from_photos(
                    race["photo_finish"], "right"
                )

            # get kpis, the race progress status
            for raceclass in raceclasses:
                if raceclass["name"] == valgt_runde.klasse:
                    raceplan_kpis = await get_race_kpis(
                        user["token"], event, [raceclass], valgt_runde.runde
                    )
                    break
            race_orders = get_race_orders(raceplan_kpis)

            """Get route function."""
            return await aiohttp_jinja2.render_template_async(
                "resultat_edit_new.html",
                self.request,
                {
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "info_list": info_list,
                    "raceclasses": raceclasses,
                    "raceplan_summary": raceplan_summary,
                    "race": race,
                    "race_orders": race_orders,
                    "raceplan_kpis": raceplan_kpis,
                    "username": user["name"],
                    "valgt_runde": valgt_runde,
                },
            )
        except Exception as e:
            logging.exception("Error. Redirect to main page.")
            raise web.HTTPSeeOther(location=f"/?informasjon={e}") from e

    async def post(self) -> web.Response:
        """Post route function that creates deltakerliste."""
        # check login
        user = await check_login(self)
        informasjon = ""
        valgt_runde = ValgtRunde()
        form = dict(await self.request.post())

        try:
            logging.debug(f"Form {form}")
            event_id = str(form["event_id"])
            event = await get_event(user["token"], event_id)
            valgt_runde.klasse = str(form["klasse"])
            valgt_runde.runde = str(form["runde"])
            race_id = str(form["race_id"])

            if "create_start" in form:
                informasjon = await create_start(user, form)
            elif "update_result" in form:
                if "photo_finish_button" in form:
                    informasjon = (
                        "Registrering fra målfoto: "
                        + await PhotoTimingService().create_time_events_from_photos(
                            user, race_id
                        )
                    )
                else:
                    informasjon = "Registrert: " + await update_result(
                        user, event, form
                    )
                # set results to official
                if "publish" in form:
                    if form["publish"] != "false":
                        res = await ResultAdapter().update_result_status(
                            user["token"], race_id, 2
                        )
                        if res == "204":
                            informasjon += f"Resultat er publisert ({res})."
                        if "raceclass_results" in form:
                            res = await RaceclassResultsService().create_raceclass_results(
                                user["token"], event, valgt_runde.klasse
                            )
                            informasjon += f" Klassens resultat er publisert ({res}). "

            # check for update without reload - return latest race results
            if "ajax" in form:
                race = await RaceplansAdapter().get_race_by_id(user["token"], race_id)
                # get latest race status
                raceclass = await RaceclassesAdapter().get_raceclass_by_name(
                    user["token"], event_id, race["raceclass"]
                )
                raceplan_kpis = await get_race_kpis(
                    user["token"], event, [raceclass], race["round"]
                )
                response = {
                    "race_results": [],
                    "race_results_status": 0,
                    "raceplan_kpis": raceplan_kpis,
                    "informasjon": informasjon,
                }
                if race["results"]:
                    response["race_results"] = race["results"]["Finish"][
                        "ranking_sequence"
                    ]
                    response["race_results_status"] = race["results"]["Finish"][
                        "status"
                    ]
                json_response = json.dumps(response)
                return web.Response(body=json_response)

        except Exception as e:
            logging.exception("Error")
            error_reason = str(e)
            if error_reason.count("401") > 0:
                informasjon = (
                    f"Error 401 - Ingen tilgang, vennligst logg inn på nytt. {e}"
                )
            else:
                informasjon += f"{error_reason}. " + informasjon

            # check for update without reload
            if "ajax" in form:
                response = {
                    "race_results": [],
                    "race_results_status": 0,
                    "informasjon": informasjon,
                }
                json_response = json.dumps(response)
                return web.Response(text=json_response)
            raise web.HTTPSeeOther(
                location=login_location(informasjon, self.request.path_qs)
            ) from e
        info = f"{informasjon}&klasse={valgt_runde.klasse}&runde={valgt_runde.runde}"
        raise web.HTTPSeeOther(
            location=f"/resultat_edit_new?event_id={event_id}&informasjon={info}"
        )


async def get_starting_now(user: dict, event: dict, heat: int) -> ValgtRunde:
    """Analyse selected heat and determine raceclass and round."""
    valgt_runde = ValgtRunde()
    valgt_runde.race_order = heat
    time_now = EventsAdapter().get_local_time(event, "log")
    races = await RaceplansAdapter().get_all_races(user["token"], event["id"])
    if heat == 0:
        for race in races:
            if time_now < race["start_time"]:
                valgt_runde.klasse = race["raceclass"]
                valgt_runde.runde = race["round"]

                break
    else:
        for race in races:
            if heat == race["order"]:
                valgt_runde.klasse = race["raceclass"]
                valgt_runde.runde = race["round"]
                break
    return valgt_runde


def find_order(valgt_runde: ValgtRunde, races: list) -> ValgtRunde:
    """Analyse selected round and determine current race order."""
    # find first heat in round
    for race in races:
        if race["round"] == valgt_runde.runde:
            valgt_runde.race_order = race["order"]
            break
    return valgt_runde


def get_race_orders(raceplan_kpis: list) -> dict:
    """Get highest and lowest race order."""
    race_orders = {
        "highest": 0,
        "lowest": 10000,
    }
    if raceplan_kpis:
        for race in raceplan_kpis[0]["races_q"]:
            race_orders["highest"] = max(race_orders["highest"], race["order"])
            race_orders["lowest"] = min(race_orders["lowest"], race["order"])
        for race in raceplan_kpis[0]["races_s"]:
            race_orders["highest"] = max(race_orders["highest"], race["order"])
            race_orders["lowest"] = min(race_orders["lowest"], race["order"])
        for race in raceplan_kpis[0]["races_f"]:
            race_orders["highest"] = max(race_orders["highest"], race["order"])
            race_orders["lowest"] = min(race_orders["lowest"], race["order"])
    return race_orders


def get_foto_start_for_race(race: dict, photos: list) -> list:
    """Loop throgh photos and return relevant finish photo(s)."""
    fotos = []
    for photo in photos:
        if photo["race_id"] == race["id"]:
            if photo["is_start_registration"]:
                fotos.append(photo)
    return fotos


def get_finish_rank_from_photos(photos: list, camera_side: str) -> list:
    """Loop throgh photos and return bib(s) in sorted order."""
    biblist = []
    for photo in photos:
        if camera_side == "left":
            for bib in photo["biblist"]:
                if bib not in biblist:
                    biblist.append(bib)
        else:
            for bib in reversed(photo["biblist"]):
                if bib not in biblist:
                    biblist.append(bib)
    return biblist


async def update_result(user: dict, event: dict, form: dict) -> str:
    """Extract form data and update result and corresponding start event."""
    time_stamp_now = EventsAdapter().get_local_time(event, "log")
    delete_result_list = []
    add_result_list = []
    race_order = form["race_order"]
    for x in form:
        any_change = True
        if x.startswith(f"{race_order}_form_rank_"):
            new_bib = form[x]
            rank_pos = x.find("rank_") + 5
            _rank = int(x[rank_pos:])
            new_rank = int(form[f"{race_order}_pos_{_rank}"])
            old_rank = int(form[f"{race_order}_old_pos_{_rank}"])
            # check if anything is changed and delete old registration
            if form[f"{race_order}_old_form_rank_{_rank}"]:
                old_bib = form[f"{race_order}_old_form_rank_{_rank}"]
                if (old_bib == new_bib) and (old_rank == new_rank):
                    any_change = False
                else:
                    # append time event to be deleted
                    delete_id = form[f"{race_order}_time_event_id_{_rank}"]
                    delete_result_list.append(delete_id)
            if new_bib.isnumeric() and any_change:
                # append new entry
                new_entry = {
                    "id": "",
                    "bib": int(new_bib),
                    "event_id": form["event_id"],
                    "race": form["race"],
                    "race_id": form["race_id"],
                    "timing_point": form["timing_point"],
                    "rank": new_rank,
                    "registration_time": time_stamp_now,
                    "next_race": "",
                    "next_race_id": "",
                    "next_race_position": 0,
                    "status": "OK",
                    "changelog": [
                        {
                            "timestamp": time_stamp_now,
                            "user_id": user["name"],
                            "comment": f"{_rank} plass i mål. ",
                        }
                    ],
                }
                add_result_list.append(new_entry)
    if len(delete_result_list) > 0 or len(add_result_list) > 0:
        informasjon = await TimeEventsService().update_finish_time_events(
            user, delete_result_list, add_result_list
        )
    else:
        informasjon = "Ingen oppdateringer"
    return informasjon
