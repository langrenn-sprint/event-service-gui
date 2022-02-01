"""Resource module for live resources."""
import logging

from aiohttp import web
import aiohttp_jinja2

from event_service_gui.services import (
    ContestantsAdapter,
    RaceclassesAdapter,
)
from .utils import (
    check_login,
    get_event,
)


class PrintContestants(web.View):
    """Class representing the printable heat lists view."""

    async def get(self) -> web.Response:
        """Get route function that return the livelister page."""
        informasjon = ""
        try:
            event_id = self.request.rel_url.query["event_id"]
        except Exception:
            event_id = ""
        try:
            action = self.request.rel_url.query["action"]
        except Exception:
            action = ""

        try:
            user = await check_login(self)
            event = await get_event(user["token"], event_id)
            try:
                valgt_klasse = self.request.rel_url.query["klasse"]
            except Exception:
                valgt_klasse = ""  # noqa: F841
            try:
                action = self.request.rel_url.query["action"]
            except Exception:
                action = ""

            raceclasses = await RaceclassesAdapter().get_raceclasses(
                user["token"], event_id
            )

            if valgt_klasse == "":
                contestants = await ContestantsAdapter().get_all_contestants(
                    user["token"], event_id
                )
            else:
                contestants = (
                    await ContestantsAdapter().get_all_contestants_by_ageclass(
                        user["token"], event_id, valgt_klasse
                    )
                )
            if len(contestants) == 0:
                informasjon = "Ingen deltakere funnet."

            # get clubs
            clubs = []
            if action == "klubb":
                for contestant in contestants:
                    if contestant["club"] not in clubs:
                        clubs.append(contestant["club"])
            """Get route function."""
            return await aiohttp_jinja2.render_template_async(
                "print_contestants.html",
                self.request,
                {
                    "action": action,
                    "clubs": clubs,
                    "contestants": contestants,
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "raceclasses": raceclasses,
                    "username": user["name"],
                },
            )
        except Exception as e:
            logging.error(f"Error: {e}. Redirect to main page.")
            return web.HTTPSeeOther(location=f"/?informasjon={e}")
