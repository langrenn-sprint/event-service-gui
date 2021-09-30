"""Resource module for main view."""
import logging

from aiohttp import web
import aiohttp_jinja2
from aiohttp_session import get_session

from event_service_gui.services import EventsAdapter
from event_service_gui.services import RaceplansAdapter
from event_service_gui.services import UserAdapter


class Raceplans(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get route function that return the index page."""
        informasjon = ""
        try:
            event_id = self.request.rel_url.query["event_id"]
        except Exception:
            informasjon = "Ingen event valgt."
            return web.HTTPSeeOther(location=f"/?informasjon={informasjon}")

        # check login
        username = ""
        session = await get_session(self.request)
        try:
            loggedin = UserAdapter().isloggedin(session)
            if not loggedin:
                return web.HTTPSeeOther(location=f"/login?event={event_id}")
            username = str(session["username"])
            token = str(session["token"])

            event = await EventsAdapter().get_event(token, event_id)

            try:
                informasjon = self.request.rel_url.query["informasjon"]
            except Exception:
                informasjon = ""
            try:
                action = self.request.rel_url.query["action"]
                if action == "update_one":
                    pass
            except Exception:
                action = ""
            logging.debug(f"Action: {action}")

            # TODO - get list of raceplans
            raceplans = await RaceplansAdapter().get_all_raceplans(token, event_id)
            races = raceplans[0]["races"]
            event = await EventsAdapter().get_event(token, event_id)

            return await aiohttp_jinja2.render_template_async(
                "raceplans.html",
                self.request,
                {
                    "action": action,
                    "lopsinfo": "Kjøreplan",
                    "raceplans": raceplans,
                    "races": races,
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "username": username,
                },
            )
        except Exception as e:
            logging.error(f"Error: {e}. Starting new session.")
            session.invalidate()
            return web.HTTPSeeOther(location="/login")

    async def post(self) -> web.Response:
        """Post route function that updates a collection of klasses."""
        # check login
        session = await get_session(self.request)
        loggedin = UserAdapter().isloggedin(session)
        if not loggedin:
            return web.HTTPSeeOther(location="/login")
        token = str(session["token"])

        informasjon = ""
        try:
            form = await self.request.post()
            logging.debug(f"Form {form}")
            event_id = str(form["event_id"])

            # Update
            if "update_one" in form.keys():
                id = str(form["id"])
                request_body = {
                    "name": str(form["name"]),
                    "distance": str(form["distance"]),
                    "event_id": event_id,
                    "id": id,
                    "order": str(form["order"]),
                    "ageclass_name": str(form["ageclass_name"]),
                    "no_of_contestants": str(form["no_of_contestants"]),
                }

                res = await RaceplansAdapter().update_raceplan(
                    token, event_id, request_body
                )
                informasjon = f"Informasjon er oppdatert - {res}"
            # Create classes from list of contestants
            elif "generate_raceplans" in form.keys():
                result = await RaceplansAdapter().generate_raceplans(token, event_id)
                informasjon = f"Opprettet kjøreplan - {result}"
            elif "delete_one" in form.keys():
                result = await RaceplansAdapter().delete_raceplan(
                    token, str(form["id"])
                )
                informasjon = f"Kjøreplaner er slettet - {result}"

        except Exception as e:
            logging.error(f"Error: {e}")
            informasjon = f"Det har oppstått en feil - {e.args}."

        return web.HTTPSeeOther(
            location=f"/raceplans?event_id={event_id}&informasjon={informasjon}"
        )
