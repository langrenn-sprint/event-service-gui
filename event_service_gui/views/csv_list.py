"""Resource module for csv export."""

import csv
import io

from aiohttp import web

from event_service_gui.services import (
    ContestantsAdapter,
    RaceclassResultsAdapter,
    RaceplansAdapter,
    StartAdapter,
)


class CsvList(web.View):
    """Class representing csv file export resource."""

    async def get(self) -> web.Response:
        """Ready route function."""
        informasjon = ""
        fields = []
        csvdata = []

        try:
            event_id = self.request.rel_url.query["event_id"]
            action = self.request.rel_url.query["action"]
        except Exception:
            informasjon = "Ingen event eller action valgt. Kan ikke vise informasjon"
            return web.HTTPSeeOther(location=f"/?informasjon={informasjon}")

        if action == "raceplan":
            csvdata = await RaceplansAdapter().get_all_races("", event_id)
            fields = get_fields_raceplan()
        elif action == "startlist":
            try:
                race_round = self.request.rel_url.query["round"]
            except Exception:
                race_round = ""
            csvdata = await get_startlist_data(event_id, race_round)
            fields = get_fields_startlist()
        elif action == "contestants":
            csvdata = await ContestantsAdapter().get_all_contestants("", event_id)
            fields = get_fields_contestants()
        elif action == "results":
            try:
                valgt_klasse = self.request.rel_url.query["klasse"]
            except Exception:
                informasjon = "Ingen løpsklasse valgt. Kan ikke vise informasjon"
                return web.HTTPSeeOther(location=f"/?informasjon={informasjon}")
            results = await RaceclassResultsAdapter().get_raceclass_result(
                event_id, valgt_klasse
            )
            if results:
                csvdata = results["ranking_sequence"]
            fields = get_fields_results()

        # convert to csv format
        output = io.StringIO()
        writer = csv.DictWriter(
            output, fieldnames=fields, delimiter=";", extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(csvdata)
        informasjon = output.getvalue()

        return web.Response(text=informasjon)


async def get_startlist_data(
    event_id: str, race_round: str
) -> list:
    """Return list of start-entries, filtered on round."""
    filtered_startlist = []
    startlist = await StartAdapter().get_all_starts_by_event("", event_id)
    if race_round:
        races = await RaceplansAdapter().get_all_races("", event_id)
        for race in races:
            if race["round"] == race_round:
                filtered_startlist.extend(
                    start for start in startlist[0]["start_entries"] if start["race_id"] == race["id"]
                )
    else:
        filtered_startlist = startlist[0]["start_entries"]
    return filtered_startlist

def get_fields_raceplan() -> list:
    """Return field for display."""
    return [
        "raceclass",
        "order",
        "start_time",
        "no_of_contestants",
        "round",
        "index",
        "heat",
        "rule",
    ]


def get_fields_startlist() -> list:
    """Return field for display."""
    return [
        "bib",
        "starting_position",
        "scheduled_start_time",
        "name",
        "club",
    ]


def get_fields_contestants() -> list:
    """Return field for display."""
    return [
        "bib",
        "first_name",
        "last_name",
        "birth_date",
        "gender",
        "ageclass",
        "club",
        "team",
        "region",
        "email",
        "minidrett_id",
        "id",
        "seeding_points",
        "registration_date_time",
    ]


def get_fields_results() -> list:
    """Return field for result display."""
    return [
        "rank",
        "bib",
        "name",
        "club",
        "ageclass",
        "round",
        # "minidrett_id",
    ]
