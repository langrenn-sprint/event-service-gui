"""Resource module for start resources."""

import logging
from operator import itemgetter

import aiohttp_jinja2
from aiohttp import web

from event_service_gui.adapters import (
    EventsAdapter,
    RaceclassesAdapter,
    RaceplansAdapter,
)

from .utils import (
    check_login_open,
    get_display_style,
    get_event,
    get_qualification_text,
    get_raceplan_summary,
    get_races_for_live_view,
    get_startlist_with_logos,
)


class Start(web.View):
    """Class representing the start view."""

    async def get(self) -> web.Response:
        """Get route function that return the startlister page."""
        try:
            user = await check_login_open(self)
            event_id = self.request.rel_url.query["event_id"]
            event = await get_event(user["token"], event_id)

            try:
                informasjon = self.request.rel_url.query["informasjon"]
            except Exception:
                informasjon = ""

            races = []
            raceplan_summary = []
            colseparators = []
            colclass = "w3-container"
            try:
                valgt_klasse = self.request.rel_url.query["klasse"]
            except Exception:
                valgt_klasse = ""
                informasjon += "Viser kjøreplan. Velg klasse for å se startlister."
            try:
                valgt_runde = self.request.rel_url.query["runde"]
            except Exception:
                valgt_runde = ""

            raceclasses = await RaceclassesAdapter().get_raceclasses(
                user["token"], event_id
            )
            # get relevant races
            # get startlister for klasse

            if valgt_klasse == "now":
                tmp_races = await RaceplansAdapter().get_all_races(
                    user["token"], event_id
                )
                races = await get_races_for_live_view(user, event, tmp_races, 0, 9)
                if len(races) > 6:
                    colseparators = [3, 6]
                    colclass = "w3-third"
                elif len(races) > 3:
                    colseparators = [3]
                    colclass = "w3-half"
            elif valgt_klasse:
                races = await RaceplansAdapter().get_races_by_racesclass(
                    user["token"], event_id, valgt_klasse
                )
            else:
                races = await RaceplansAdapter().get_all_races(user["token"], event_id)

            if len(races) == 0:
                informasjon = f"{informasjon} Ingen løp funnet."
            else:
                filtered_races = []
                for race in races:
                    if valgt_klasse:
                        race["next_race"] = get_qualification_text(race)
                        race["display_color"] = get_display_style(
                            race["start_time"], event
                        )
                        # get start list details
                        race["startliste"] = get_startlist_with_logos(race)

                    # filter on selected round
                    if valgt_runde:
                        if race["round"] == valgt_runde:
                            filtered_races.append(race)
                    else:
                        filtered_races.append(race)
                raceplan_summary = get_raceplan_summary(races, raceclasses)
                races = filtered_races

            # sort start list by starting position
            for race in races:
                startliste = race.get("startliste", [])
                if len(startliste) > 1:
                    race["startliste"] = sorted(
                        startliste, key=itemgetter("starting_position")
                    )

            """Get route function."""
            return await aiohttp_jinja2.render_template_async(
                "start.html",
                self.request,
                {
                    "colclass": colclass,
                    "colseparators": colseparators,
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "valgt_klasse": valgt_klasse,
                    "valgt_runde": valgt_runde,
                    "raceclasses": raceclasses,
                    "races": races,
                    "raceplan_summary": raceplan_summary,
                    "local_time_now": EventsAdapter().get_local_time(event, "HH:MM"),
                    "username": user["name"],
                },
            )
        except Exception as e:
            logging.exception("Error. Redirect to main page.")
            raise web.HTTPSeeOther(location=f"/?informasjon={e}") from e
