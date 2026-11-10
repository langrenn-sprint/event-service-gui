"""Resource module for verificatoin of timing registration."""

import logging

import aiohttp_jinja2
from aiohttp import web

from event_service_gui.adapters import (
    RaceclassesAdapter,
    RaceplansAdapter,
)

from .utils import (
    check_login,
    create_start,
    delete_start,
    get_enrichced_startlist,
    get_event,
    get_qualification_text,
    login_location,
)


class StartEdit(web.View):
    """Class representing the start edit view."""

    async def get(self) -> web.Response:
        """Get route function that return the passeringer page."""
        next_races = []
        valgt_klasse = ""

        try:
            informasjon = self.request.rel_url.query["informasjon"]
        except Exception:
            informasjon = ""
        try:
            valgt_runde = self.request.rel_url.query["runde"]
        except Exception:
            valgt_runde = ""

        user = await check_login(self)
        try:
            event_id = self.request.rel_url.query["event_id"]
            event = await get_event(user["token"], event_id)
            raceclasses = await RaceclassesAdapter().get_raceclasses(
                user["token"], event_id
            )

            # find raceclass and get races
            try:
                valgt_klasse = self.request.rel_url.query["klasse"]
            except Exception:
                informasjon = "Velg klasse i menyen."

            all_races = []
            if valgt_klasse:
                all_races = await RaceplansAdapter().get_races_by_racesclass(
                    user["token"], event_id, valgt_klasse
                )

            try:
                action = self.request.rel_url.query["action"]
            except Exception:
                action = ""

            # enrich data
            for race in all_races:
                race["next_race"] = get_qualification_text(race)
                # get start list detail
                race["startliste"] = await get_enrichced_startlist(user, race)
                next_races.append(race)

            if valgt_runde:
                next_races = [
                    race for race in next_races if race["round"] == valgt_runde
                ]

            """Get route function."""
            return await aiohttp_jinja2.render_template_async(
                "start_edit.html",
                self.request,
                {
                    "action": action,
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "next_races": next_races,
                    "raceclasses": raceclasses,
                    "username": user["name"],
                    "valgt_klasse": valgt_klasse,
                    "valgt_runde": valgt_runde,
                },
            )
        except Exception as e:
            logging.exception("Error. Redirect to main page.")
            raise web.HTTPSeeOther(location=f"/?informasjon={e}") from e

    async def post(self) -> web.Response:
        """Post route function that creates deltakerliste."""
        # check login
        user = await check_login(self)
        informasjon = ""
        form = dict(await self.request.post())
        event_id = str(form["event_id"])
        valgt_klasse = str(form["klasse"])
        valgt_runde = str(form["runde"])
        action = ""
        try:
            if "create_start" in form:
                informasjon = await create_start(user, form)
            elif "delete_start" in form:
                informasjon = await delete_start(user, form)
            elif "move_start" in form:
                informasjon = "Flytting utført: "
                informasjon += await delete_start(user, form)
                informasjon += await create_start(user, form)

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
        info = (
            f"{informasjon}&klasse={valgt_klasse}&runde={valgt_runde}&action={action}"
        )
        raise web.HTTPSeeOther(
            location=f"/start_edit?event_id={event_id}&informasjon={info}"
        )
