"""Resource module for photo edit view."""

import logging

import aiohttp_jinja2
from aiohttp import web

from event_service_gui.adapters import (
    EventsAdapter,
    PhotosAdapter,
    RaceclassesAdapter,
    RaceplansAdapter,
)
from event_service_gui.services import (
    FotoService,
)

from .utils import (
    check_login,
    get_event,
    login_location,
)


class PhotosEdit(web.View):
    """Class representing the photos edit view."""

    async def get(self) -> web.Response:
        """Get route function that return the dashboards page."""
        try:
            action = self.request.rel_url.query["action"]
        except Exception:
            action = ""
        try:
            my_filter = self.request.rel_url.query["filter"]
        except Exception:
            my_filter = ""
        try:
            photo_type = self.request.rel_url.query["photo_type"]
        except Exception:
            photo_type = ""
        try:
            valgt_klasse = self.request.rel_url.query["raceclass"]
        except Exception:
            valgt_klasse = ""
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
            if valgt_klasse:
                photos = await PhotosAdapter().get_photos_by_raceclass(
                    user["token"], event_id, valgt_klasse, starred=False
                )
            else:
                photos = await PhotosAdapter().get_all_photos(
                    user["token"], event_id, starred=False
                )
            if my_filter == "low_confidence":
                photos = [photo for photo in photos if photo["confidence"] < 51]
            photos.reverse()

            races = await RaceplansAdapter().get_all_races(user["token"], event_id)
            raceclasses = await RaceclassesAdapter().get_raceclasses(
                user["token"], event_id
            )

            return await aiohttp_jinja2.render_template_async(
                "photos_edit.html",
                self.request,
                {
                    "lopsinfo": "Foto redigering",
                    "action": action,
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "local_time_now": EventsAdapter().get_local_time(event, "HH:MM"),
                    "photos": photos,
                    "photo_type": photo_type,
                    "raceclasses": raceclasses,
                    "races": races,
                    "valgt_klasse": valgt_klasse,
                    "username": user["name"],
                },
            )
        except Exception as e:
            logging.exception("Error. Redirect to main page.")
            raise web.HTTPSeeOther(location=f"/?informasjon={e}") from e

    async def post(self) -> web.Response:
        """Post route function that updates a collection of photos."""
        informasjon = ""
        form = dict(await self.request.post())
        event_id = str(form["event_id"])
        user = await check_login(self)

        try:
            if "update_race_info" in form:
                event = await get_event(user["token"], event_id)
                informasjon = await FotoService().update_race_info(
                    user["token"], event, form
                )
            elif "delete_all_local" in form:
                informasjon = await FotoService().delete_all_local_photos(
                    user["token"], event_id
                )
            elif "delete_all_low_confidence" in form:
                informasjon = await FotoService().delete_all_low_confidence_photos(
                    user["token"], event_id, 51
                )
            elif "delete_select" in form:
                informasjon = "Sletting utført: "
                for key, value in form.items():
                    if key.startswith("update_"):
                        photo_id = str(value)
                        result = await PhotosAdapter().delete_photo(
                            user["token"], photo_id
                        )
                        logging.debug(f"Deleted photo - {result}")
                        informasjon += f"{key} "
        except Exception as e:
            logging.exception("Error")
            informasjon = f"Det har oppstått en feil - {e.args}."
            error_reason = str(e)
            if error_reason.startswith("401"):
                raise web.HTTPSeeOther(
                    location=login_location(
                        f"Ingen tilgang, vennligst logg inn på nytt. {e}",
                        self.request.path_qs,
                    )
                ) from e

        raise web.HTTPSeeOther(
            location=f"/photos_edit?event_id={event_id}&informasjon={informasjon}"
        )
