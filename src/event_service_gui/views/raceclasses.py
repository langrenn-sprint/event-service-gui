"""Resource module for main view."""
import logging

from aiohttp import web
import aiohttp_jinja2
from aiohttp_session import get_session

from event_service_gui.services import EventsAdapter
from event_service_gui.services import RaceclassesAdapter
from event_service_gui.services import UserAdapter


class Raceclasses(web.View):
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
            klasse = {}
            try:
                action = self.request.rel_url.query["action"]
                if action == "update_one":
                    id = self.request.rel_url.query["id"]
                    klasse = await RaceclassesAdapter().get_ageclass(
                        token, event_id, id
                    )

            except Exception:
                action = ""
            logging.debug(f"Action: {action}")

            ageclasses = await RaceclassesAdapter().get_ageclasses(token, event_id)

            return await aiohttp_jinja2.render_template_async(
                "raceclasses.html",
                self.request,
                {
                    "action": action,
                    "ageclasses": ageclasses,
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "lopsinfo": "Klasser",
                    "klasse": klasse,
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
                    "raceclass": str(form["raceclass"]),
                    "no_of_contestants": str(form["no_of_contestants"]),
                }

                result = await RaceclassesAdapter().update_ageclass(
                    token, event_id, id, request_body
                )
                informasjon = f"Informasjon er oppdatert - {result}"
            elif "update_order" in form.keys():
                for input in form.keys():
                    if input.startswith("id_"):
                        id = str(form[input])
                        age_class = await RaceclassesAdapter().get_ageclass(
                            token, event_id, id
                        )
                        age_class["order"] = str(form[f"order_{id}"])
                        result = await RaceclassesAdapter().update_ageclass(
                            token, event_id, id, age_class
                        )
                        logging.info(f"Age_class: {age_class} - update result {result}")
                informasjon = "Klasser er oppdatert."
            # Create classes from list of contestants
            elif "generate_ageclasses" in form.keys():
                informasjon = await EventsAdapter().generate_classes(token, event_id)
            elif "refresh_no_of_contestants" in form.keys():
                informasjon = "TODO: Antall deltakere pr. klasse er oppdatert."
            # delete
            elif "delete_one" in form.keys():
                res = await RaceclassesAdapter().delete_ageclass(
                    token, event_id, str(form["id"])
                )
                informasjon = f"Klasse er slettet - {res}"
            # delete_all
            elif "delete_all" in form.keys():
                res = await RaceclassesAdapter().delete_all_ageclasses(token, event_id)
                informasjon = f"Klasser er slettet - {res}"

        except Exception as e:
            logging.error(f"Error: {e}")
            informasjon = f"Det har oppstått en feil - {e.args}."

        return web.HTTPSeeOther(
            location=f"/raceclasses?event_id={event_id}&informasjon={informasjon}"
        )
