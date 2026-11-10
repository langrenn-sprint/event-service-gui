"""Resource module for photo resources."""

import logging

import aiohttp_jinja2
from aiohttp import web

from event_service_gui.adapters import (
    PhotosAdapter,
    RaceclassesAdapter,
)

from .utils import (
    check_login_open,
    get_event,
)


class Photos(web.View):
    """Class representing the photo view."""

    async def get(self) -> web.Response:
        """Get route function that return the photolister page."""
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

            try:
                valgt_klasse = self.request.rel_url.query["klasse"]
            except Exception:
                valgt_klasse = ""
            try:
                valgt_startnr = int(self.request.rel_url.query["startnr"])
            except Exception:
                valgt_startnr = 0

            raceclasses = await RaceclassesAdapter().get_raceclasses(
                user["token"], event_id
            )
            photos = []
            if not valgt_klasse:
                photos = await PhotosAdapter().get_all_photos(
                    user["token"], event_id, starred=True, limit=50
                )
            else:
                photos = await PhotosAdapter().get_photos_by_raceclass(
                    user["token"], event_id, valgt_klasse, starred=True
                )

            """Get route function."""
            return await aiohttp_jinja2.render_template_async(
                "photos.html",
                self.request,
                {
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "photos": photos,
                    "valgt_klasse": valgt_klasse,
                    "valgt_startnr": valgt_startnr,
                    "raceclasses": raceclasses,
                    "username": user["name"],
                },
            )
        except Exception as e:
            logging.exception("Error. Redirect to main page.")
            raise web.HTTPSeeOther(location=f"/?informasjon={e}") from e
