"""Resource module for csv export."""
import csv
import io

from aiohttp import web

from event_service_gui.services import (
    RaceplansAdapter,
    StartAdapter,
)


class Csv(web.View):
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
        elif action == "startlist":
            startlist = await StartAdapter().get_all_starts_by_event("", event_id)
            csvdata = startlist[0]["start_entries"]
            fields = [
                "bib",
                "starting_position",
                "scheduled_start_time",
                "name",
                "club",
            ]
            # fields = csvdata[0].keys()

        # convert to csv format
        output = io.StringIO()
        writer = csv.DictWriter(
            output, fieldnames=fields, delimiter=";", extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(csvdata)
        informasjon = output.getvalue()

        return web.Response(text=informasjon)
