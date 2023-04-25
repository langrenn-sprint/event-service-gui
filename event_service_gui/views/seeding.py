"""Resource module for seeding view."""
import logging

from aiohttp import web
import aiohttp_jinja2

from event_service_gui.services import (
    ContestantsAdapter,
    EventsAdapter,
    RaceclassesAdapter,
)
from .utils import (
    add_seeding_points,
    check_login,
    check_login_open,
    get_event,
    get_heat_separators,
    perform_seeding,
)


class Seeding(web.View):
    """Class representing the seeding view."""

    async def get(self) -> web.Response:
        """Get route function that return the index page."""
        action = ""
        heat_separators = []
        try:
            event_id = self.request.rel_url.query["event_id"]
        except Exception:
            event_id = ""
        if event_id == "":
            informasjon = "Ingen event valgt."
            return web.HTTPSeeOther(location=f"/?informasjon={informasjon}")

        try:
            user = await check_login_open(self)
            event = await get_event(user["token"], event_id)

            try:
                informasjon = self.request.rel_url.query["informasjon"]
                info_list = informasjon.split("<br>")
                informasjon = ""
            except Exception:
                informasjon = ""
                info_list = []

            try:
                valgt_klasse = self.request.rel_url.query["klasse"]
            except Exception:
                valgt_klasse = ""  # noqa: F841

            raceclasses = await RaceclassesAdapter().get_raceclasses(
                user["token"], event_id
            )

            contestants = list()
            try:
                action = self.request.rel_url.query["action"]
            except Exception:
                action = ""

            if valgt_klasse == "":
                if action in ["seeding_manual", "seeding_points"]:
                    informasjon = "Velg klasse for å utføre seeding."
                else:
                    contestants = await ContestantsAdapter().get_all_contestants(
                        user["token"], event_id
                    )
            else:
                contestants = (
                    await ContestantsAdapter().get_all_contestants_by_raceclass(
                        user["token"], event_id, valgt_klasse
                    )
                )
                heat_separators = await get_heat_separators(
                    user["token"], event_id, valgt_klasse
                )
            for tmp_contestant in contestants:
                tmp_contestant["club_logo"] = EventsAdapter().get_club_logo_url(
                    tmp_contestant["club"]
                )
            return await aiohttp_jinja2.render_template_async(
                "seeding.html",
                self.request,
                {
                    "action": action,
                    "contestants": contestants,
                    "event": event,
                    "event_id": event_id,
                    "heat_separators": heat_separators,
                    "info_list": info_list,
                    "informasjon": informasjon,
                    "raceclasses": raceclasses,
                    "valgt_klasse": valgt_klasse,
                    "lopsinfo": f"Seeding {valgt_klasse}",
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
        valgt_klasse = ""
        try:
            form = await self.request.post()
            logging.debug(f"Form {form}")
            event_id = str(form["event_id"])
            valgt_klasse = str(form["klasse"])
            try:
                action = str(form["action"])
            except Exception:
                action = ""  # noqa: F841

            # Do the stuff
            if action == "seeding_manual":
                informasjon = await add_seeding_from_form(user["token"], event_id, form)  # type: ignore
            elif action == "seeding_points":
                informasjon = await add_seeding_points(user["token"], event_id, form)  # type: ignore
                informasjon += "<br>"
                informasjon += await perform_seeding(
                    user["token"],
                    event_id,
                    valgt_klasse,
                )
        except Exception as e:
            logging.error(f"Error: {e}")
            informasjon = f"Det har oppstått en feil - {e.args}."
            error_reason = str(e)
            if error_reason.startswith("401"):
                return web.HTTPSeeOther(
                    location=f"/login?informasjon=Ingen tilgang, vennligst logg inn på nytt. {e}"
                )

        info = f"action={action}&informasjon={informasjon}&klasse={valgt_klasse}"
        return web.HTTPSeeOther(location=f"/seeding?event_id={event_id}&{info}")


async def add_seeding_from_form(token: str, event_id: str, form: dict) -> str:
    """Load seeding info from form and swap BIB."""
    informasjon = "Flyttet på løpere: "
    for key in form.keys():
        if key.startswith("bib_"):
            new_bib = form[key]
            if new_bib.isnumeric():
                # check if bib is already in use and free it
                old_contestant = await ContestantsAdapter().get_contestant_by_bib(
                    token, event_id, new_bib
                )
                if old_contestant:
                    old_contestant["bib"] = None
                    result = await ContestantsAdapter().update_contestant(
                        token, event_id, old_contestant
                    )

                # give bib to new contestant
                contestant_id = key[4:]
                contestant = await ContestantsAdapter().get_contestant(
                    token, event_id, contestant_id
                )
                contestant["bib"] = int(new_bib)
                result = await ContestantsAdapter().update_contestant(
                    token, event_id, contestant
                )
                logging.debug(result)
                informasjon += f"{contestant['bib']} {contestant['last_name']}. "
    return informasjon
