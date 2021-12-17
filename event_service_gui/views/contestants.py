"""Resource module for main view."""
import logging

from aiohttp import web
import aiohttp_jinja2

from event_service_gui.services import (
    ContestantsAdapter,
    EventsAdapter,
    RaceclassesAdapter,
)
from .utils import check_login, get_event


class Contestants(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get route function that return the index page."""
        try:
            event_id = self.request.rel_url.query["event_id"]
        except Exception:
            event_id = ""
        if event_id == "":
            informasjon = "Ingen event valgt."
            return web.HTTPSeeOther(location=f"/?informasjon={informasjon}")

        try:
            user = await check_login(self)
            event = await get_event(user["token"], event_id)

            try:
                informasjon = self.request.rel_url.query["informasjon"]
            except Exception:
                informasjon = ""

            try:
                valgt_klasse = self.request.rel_url.query["klasse"]
            except Exception:
                valgt_klasse = ""  # noqa: F841

            raceclasses = await RaceclassesAdapter().get_raceclasses(
                user["token"], event_id
            )
            for klasse in raceclasses:
                klasse["ageclass_web"] = klasse["ageclass_name"].replace(" ", "%20")

            contestant = {}
            try:
                action = self.request.rel_url.query["action"]
                if action == "update_one":
                    id = self.request.rel_url.query["id"]
                    contestant = await ContestantsAdapter().get_contestant(
                        user["token"], event_id, id
                    )

            except Exception:
                action = ""

            event = await EventsAdapter().get_event(user["token"], event_id)

            contestants = await ContestantsAdapter().get_all_contestants_by_ageclass(
                user["token"], event_id, valgt_klasse
            )
            logging.debug(f"Contestants: {contestants}")
            return await aiohttp_jinja2.render_template_async(
                "contestants.html",
                self.request,
                {
                    "action": action,
                    "contestants": contestants,
                    "contestant": contestant,
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "raceclasses": raceclasses,
                    "valgt_klasse": valgt_klasse,
                    "lopsinfo": f"Deltakere {valgt_klasse}",
                    "username": user["name"],
                },
            )
        except Exception as e:
            logging.error(f"Error: {e}. Redirect to main page.")
            return web.HTTPSeeOther(location=f"/?informasjon={e}")

    async def post(self) -> web.Response:
        """Post route function that creates deltakerliste."""
        # check login
        user = await check_login(self)

        informasjon = ""
        action = ""
        try:
            form = await self.request.post()
            logging.debug(f"Form {form}")
            event_id = str(form["event_id"])

            # Create new deltakere
            if "assign_bibs" in form.keys():
                informasjon = await ContestantsAdapter().assign_bibs(
                    user["token"], event_id
                )
                return web.HTTPSeeOther(
                    location=f"/tasks?event_id={event_id}&informasjon={informasjon}"
                )

            elif "create" in form.keys():
                file = form["file"]
                text_file = file.file  # type: ignore
                logging.debug(f"File type: {file.content_type}")  # type: ignore

                # handle file - csv supported
                if file.content_type == "text/csv":  # type: ignore
                    resp = await ContestantsAdapter().create_contestants(
                        user["token"], event_id, text_file
                    )
                    logging.debug(f"Created contestants: {resp}")
                    informasjon = f"Opprettet deltakere: {resp}"
                else:
                    raise Exception(f"Ugyldig filtype {file.content_type}")  # type: ignore
                return web.HTTPSeeOther(
                    location=f"/tasks?event_id={event_id}&informasjon={informasjon}"
                )

            elif "create_one" in form.keys() or "update_one" in form.keys():
                request_body = {
                    "first_name": str(form["first_name"]),
                    "last_name": str(form["last_name"]),
                    "birth_date": str(form["birth_date"]),
                    "gender": str(form["gender"]),
                    "ageclass": str(form["ageclass"]),
                    "region": str(form["region"]),
                    "club": str(form["club"]),
                    "event_id": event_id,
                    "email": str(form["email"]),
                    "team": str(form["team"]),
                    "minidrett_id": str(form["minidrett_id"]),
                    "bib": str(form["bib"]),
                }
                if "create_one" in form.keys():
                    id = await ContestantsAdapter().create_contestant(
                        user["token"], event_id, request_body
                    )
                    informasjon = f"Deltaker er opprettet - {id}"
                else:
                    request_body["id"] = str(form["id"])
                    result = await ContestantsAdapter().update_contestant(
                        user["token"], event_id, request_body
                    )
                    informasjon = f"Informasjon er oppdatert - {result}"
            # delete
            elif "delete_one" in form.keys():
                result = await ContestantsAdapter().delete_contestant(
                    user["token"], event_id, str(form["id"])
                )
                informasjon = f"Deltaker er slettet - {result}"
            # delete_all
            elif "delete_all" in form.keys():
                result = await ContestantsAdapter().delete_all_contestants(
                    user["token"], event_id
                )
                informasjon = f"Deltakerne er slettet - {result}"
        except Exception as e:
            logging.error(f"Error: {e}")
            informasjon = f"Det har oppstått en feil - {e.args}."

        info = f"action={action}&informasjon={informasjon}"
        return web.HTTPSeeOther(location=f"/contestants?event_id={event_id}&{info}")
