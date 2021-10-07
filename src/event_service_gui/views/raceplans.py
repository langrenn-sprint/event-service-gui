"""Resource module for main view."""
import logging

from aiohttp import web
import aiohttp_jinja2

from event_service_gui.services import EventsAdapter
from event_service_gui.services import RaceplansAdapter
from .utils import check_login, get_event, get_raceplan_summary


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

            raceplans = await RaceplansAdapter().get_all_raceplans(
                user["token"], event_id
            )
            raceplan = {}
            raceplan_summary = []
            races = []
            if len(raceplans) > 0:
                races = raceplans[0]["races"]
                if len(races) == 0:
                    informasjon = f"{informasjon} Ingen kjøreplaner funnet."
                else:
                    raceplan = raceplans[0]
                    raceplan_summary = get_raceplan_summary(races)

            event = await EventsAdapter().get_event(user["token"], event_id)

            return await aiohttp_jinja2.render_template_async(
                "raceplans.html",
                self.request,
                {
                    "action": action,
                    "lopsinfo": "Kjøreplan",
                    "raceplan": raceplan,
                    "raceplan_summary": raceplan_summary,
                    "races": races,
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "username": user["name"],
                },
            )
        except Exception as e:
            logging.error(f"Error: {e}. Redirect to main page.")
            return web.HTTPSeeOther(location=f"/?informasjon={e}")

    async def post(self) -> web.Response:
        """Post route function that updates a collection of klasses."""
        user = await check_login(self)

        informasjon = ""
        form = await self.request.post()
        event_id = str(form["event_id"])
        logging.info(f"Form {form}")

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
            elif "delete_all" in form.keys():
                result = await RaceplansAdapter().delete_raceplans(
                    user["token"], str(form["id"])
                )
                informasjon = f"Kjøreplaner er slettet - {result}"

        except Exception as e:
            logging.error(f"Error: {e}")
            informasjon = f"Det har oppstått en feil - {e.args}."

        return web.HTTPSeeOther(
            location=f"/raceplans?event_id={event_id}&informasjon={informasjon}"
        )
