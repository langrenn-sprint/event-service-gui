"""Resource module for TD report view."""

import logging

import aiohttp_jinja2
from aiohttp import web

from event_service_gui.adapters import (
    ContestantsAdapter,
    EventsAdapter,
    RaceclassesAdapter,
    RaceclassResultsAdapter,
    RaceplansAdapter,
)

from .utils import (
    check_login,
    get_event,
)


def club_key(club_name: str) -> str:
    """Normalize club name to a 4-letter key for aggregation."""
    return club_name.strip()[:4].lower()


class TdReport(web.View):
    """TD report view - lists raceclasses with contestant, DNS and DNF counts."""

    async def get(self) -> web.Response:
        """Get route function that returns the TD report page."""
        try:
            event_id = self.request.rel_url.query["event_id"]
        except Exception:
            event_id = ""
        try:
            informasjon = self.request.rel_url.query["informasjon"]
        except Exception:
            informasjon = ""

        user = await check_login(self)
        try:
            event = await get_event(user["token"], event_id)

            raceclasses = await RaceclassesAdapter().get_raceclasses(
                user["token"], event_id
            )
            all_contestants = await ContestantsAdapter().get_all_contestants(
                user["token"], event_id
            )
            total_unique_clubs = len(
                {club_key(c["club"]) for c in all_contestants if c.get("club")}
            )

            raceclass_stats = []
            for raceclass in raceclasses:
                dns_count = None
                dnf_count = None
                races = await RaceplansAdapter().get_races_by_racesclass(
                    user["token"], event_id, raceclass["name"]
                )
                for race in races:
                    race_details = await RaceplansAdapter().get_race_by_id(
                        user["token"], race["id"]
                    )
                    results = race_details.get("results", {})
                    # DNS: registrert som egen timing_point i resultater
                    if results:
                        dns_count = (dns_count or 0) + results.get("DNS", {}).get(
                            "no_of_contestants", 0
                        )

                # DNF: hentes fra klasse-resultat (samme kilde som resultat.py)
                try:
                    resultlist = await RaceclassResultsAdapter().get_raceclass_result(
                        event_id, raceclass["name"]
                    )
                    ranking_sequence = resultlist.get("ranking_sequence", [])
                    dnf_count = sum(
                        1
                        for racer in ranking_sequence
                        if (racer.get("time_event", {}).get("timing_point") == "DNF")
                    )
                except Exception:
                    dnf_count = None

                contestants = (
                    await ContestantsAdapter().get_all_contestants_by_raceclass(
                        user["token"], event_id, raceclass["name"]
                    )
                )
                club_count = len(
                    {club_key(c["club"]) for c in contestants if c.get("club")}
                )

                raceclass_stats.append(
                    {
                        "name": raceclass["name"],
                        "no_of_contestants": raceclass["no_of_contestants"],
                        "clubs": club_count,
                        "dns": dns_count,
                        "dnf": dnf_count,
                    }
                )

            return await aiohttp_jinja2.render_template_async(
                "td_report.html",
                self.request,
                {
                    "lopsinfo": "TD Rapport",
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "local_time_now": EventsAdapter().get_local_time(event, "HH:MM"),
                    "raceclass_stats": raceclass_stats,
                    "total_unique_clubs": total_unique_clubs,
                    "username": user["name"],
                },
            )
        except Exception as e:
            logging.exception("Error. Redirect to main page.")
            raise web.HTTPSeeOther(location=f"/?informasjon={e}") from e
