"""Resource module for main view."""
import logging

from aiohttp import web
import aiohttp_jinja2

from event_service_gui.services import (
    EventsAdapter,
    RaceclassesAdapter,
    RaceplansAdapter,
)
from .utils import check_login, get_event, get_qualification_text, get_raceplan_summary


class Raceplans(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get route function that return the index page."""
        informasjon = ""
        try:
            event_id = self.request.rel_url.query["event_id"]
        except Exception:
            event_id = ""

        try:
            user = await check_login(self)
            event = await get_event(user["token"], event_id)

            try:
                informasjon = self.request.rel_url.query["informasjon"]
            except Exception:
                informasjon = ""
            try:
                action = self.request.rel_url.query["action"]
            except Exception:
                action = ""
            logging.debug(f"Action: {action}")

            try:
                valgt_klasse = self.request.rel_url.query["klasse"]
            except Exception:
                valgt_klasse = ""  # noqa: F841

            raceclasses = await RaceclassesAdapter().get_raceclasses(
                user["token"], event_id
            )

            raceplans = await RaceplansAdapter().get_all_raceplans(
                user["token"], event_id
            )
            raceplan = {}
            raceplan_summary = []
            races = []
            if len(raceplans) > 0:
                races = await RaceplansAdapter().get_all_races(user["token"], event_id)
                if len(races) == 0:
                    informasjon = f"{informasjon} Ingen kjøreplaner funnet."
                else:
                    raceplan = raceplans[0]
                    logging.info(f"summary: {races}")
                    raceplan_summary = get_raceplan_summary(races, raceclasses)
                # generate text explaining qualificatoin rule (videre til)
                for race in races:
                    logging.info(f"qual: {race}")
                    race["next_race"] = get_qualification_text(race)

            event = await EventsAdapter().get_event(user["token"], event_id)

            return await aiohttp_jinja2.render_template_async(
                "raceplans.html",
                self.request,
                {
                    "action": action,
                    "lopsinfo": "Kjøreplan",
                    "raceclasses": raceclasses,
                    "raceplan": raceplan,
                    "raceplan_summary": raceplan_summary,
                    "races": races,
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "username": user["name"],
                    "valgt_klasse": valgt_klasse,
                },
            )
        except Exception as e:
            logging.error(f"Error: {e}. Redirect to main page.")
            return web.HTTPSeeOther(location=f"/?informasjon={e}")

    async def post(self) -> web.Response:
        """Post route function that updates a collection of klasses."""
        user = await check_login(self)

        informasjon = ""
        action = ""
        form = await self.request.post()
        event_id = str(form["event_id"])
        logging.debug(f"Form {form}")

        try:
            if "update_one" in form.keys():
                id = str(form["id"])
                request_body = {
                    "name": str(form["name"]),
                    "distance": str(form["distance"]),
                    "event_id": event_id,
                    "id": id,
                    "order": int(form["order"]),
                    "ageclass_name": str(form["ageclass_name"]),
                    "no_of_contestants": str(form["no_of_contestants"]),
                }

                res = await RaceplansAdapter().update_raceplan(
                    user["token"], event_id, request_body
                )
                informasjon = f"Informasjon er oppdatert - {res}"
            # Create classes from list of contestants
            elif "generate_raceplan" in form.keys():
                result = await RaceplansAdapter().generate_raceplan(
                    user["token"], event_id
                )
                informasjon = f"Opprettet kjøreplan - {result}"
                action = "next_start_time"
                info = f"action={action}&informasjon={informasjon}"
                return web.HTTPSeeOther(location=f"/tasks?event_id={event_id}&{info}")
            elif "delete_all" in form.keys():
                result = await RaceplansAdapter().delete_raceplans(
                    user["token"], str(form["id"])
                )
                informasjon = f"Kjøreplaner er slettet - {result}"
            elif "update_time" in form.keys():
                logging.info(
                    f"update_time - old:{form['old_time']}, new:{form['new_time']}"
                )
                informasjon = f"Tidplan er oppdatert {form['id']} - {form['round']}"
                action = "edit_time"
        except Exception as e:
            logging.error(f"Error: {e}")
            informasjon = f"Det har oppstått en feil - {e.args}."

        info = f"action={action}&informasjon={informasjon}"
        return web.HTTPSeeOther(location=f"/raceplans?event_id={event_id}&{info}")
