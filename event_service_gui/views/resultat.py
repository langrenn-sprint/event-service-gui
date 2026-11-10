"""Resource module for resultat view."""

import logging

import aiohttp_jinja2
from aiohttp import web

from event_service_gui.adapters import (
    PhotosAdapter,
    RaceclassesAdapter,
    RaceclassResultsAdapter,
)

from .utils import (
    check_login_open,
    get_event,
)


class Resultat(web.View):
    """Class representing the resultat view. Both sluttresultat and heatresultat."""

    async def get(self) -> web.Response:
        """Get route function."""
        try:
            event_id = self.request.rel_url.query["event_id"]
        except Exception:
            event_id = ""
        try:
            informasjon = self.request.rel_url.query["informasjon"]
        except Exception:
            informasjon = ""

        try:
            user = await check_login_open(self)
            event = await get_event(user["token"], event_id)

            foto = []
            informasjon = ""
            resultlist = {}
            valgt_bildevisning = ""

            try:
                valgt_klasse = self.request.rel_url.query["klasse"]
            except Exception:
                valgt_klasse = ""

            raceclasses = await RaceclassesAdapter().get_raceclasses(
                user["token"], event_id
            )

            if not valgt_klasse:
                informasjon = "Velg klasse for å vise resultater"
                foto = await PhotosAdapter().get_all_photos(
                    user["token"], event_id, starred=True, limit=5
                )
            else:
                try:
                    resultlist = await RaceclassResultsAdapter().get_raceclass_result(
                        event_id, valgt_klasse
                    )
                except Exception as e:
                    informasjon = f"{e} Velg 'Live' i menyen for heat resultater"

                foto = await PhotosAdapter().get_photos_by_raceclass(
                    user["token"], event_id, valgt_klasse, starred=True, limit=5
                )
                valgt_bildevisning = "klasse=" + valgt_klasse

            """Get route function."""
            return await aiohttp_jinja2.render_template_async(
                "resultat.html",
                self.request,
                {
                    "event": event,
                    "event_id": event_id,
                    "foto": foto,
                    "informasjon": informasjon,
                    "valgt_bildevisning": valgt_bildevisning,
                    "valgt_klasse": valgt_klasse,
                    "klasser": raceclasses,
                    "resultlist": resultlist,
                    "username": user["name"],
                },
            )
        except Exception as e:
            logging.exception("Error. Redirect to main page.")
            raise web.HTTPSeeOther(location=f"/?informasjon={e}") from e
