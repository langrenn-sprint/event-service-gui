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
            startlist = await StartAdapter().get_all_starts_by_event("", event_id)
            csvdata = startlist[0]["start_entries"]
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


def get_fields_raceplan() -> list:
    """Return field for display."""
    fields = [
        "raceclass",
        "order",
        "start_time",
        "no_of_contestants",
        "round",
        "index",
        "heat",
        "rule",
    ]
    return fields


def get_fields_startlist() -> list:
    """Return field for display."""
    fields = [
        "bib",
        "starting_position",
        "scheduled_start_time",
        "name",
        "club",
    ]
    return fields


def get_fields_contestants() -> list:
    """Return field for display."""
    fields = [
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
        "registration_time",
    ]
    return fields


def get_fields_results() -> list:
    """Return field for result display."""
    fields = [
        "rank",
        "bib",
        "name",
        "club",
        "ageclass",
        "round",
        # "minidrett_id",
    ]
    return fields
