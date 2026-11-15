"""Resource module for photo finish verification."""

import logging
from dataclasses import dataclass

import aiohttp_jinja2
from aiohttp import web

from event_service_gui.adapters import (
    EventsAdapter,
    PhotosAdapter,
    RaceclassesAdapter,
    RaceplansAdapter,
)

from .utils import (
    check_login,
    get_enrichced_startlist,
    get_event,
    get_finish_timings,
    get_foto_finish_for_race,
    get_qualification_text,
    get_race_kpis,
    get_raceplan_summary,
)


@dataclass
class ValgtRunde:
    """Class representing information for selected round."""

    klasse: str = ""
    runde: str = ""
    race_order: int = -1
    informasjon: str = ""


class PhotoFinish(web.View):
    """Class representing the photo finish view."""

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
                "photo_finish.html",
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
