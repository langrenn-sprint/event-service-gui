"""Resource module for main view."""
import logging

from aiohttp import web
import aiohttp_jinja2

from event_service_gui.services import EventsAdapter
from event_service_gui.services import RaceclassesAdapter
from .utils import check_login, get_event


class Raceclasses(web.View):
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
            klasse = {}
            try:
                action = self.request.rel_url.query["action"]
                if action == "update_one":
                    id = self.request.rel_url.query["id"]
                    klasse = await RaceclassesAdapter().get_raceclass(
                        user["token"], event_id, id
                    )

            except Exception:
                action = ""
            logging.debug(f"Action: {action}")

            raceclasses = await RaceclassesAdapter().get_raceclasses(
                user["token"], event_id
            )

            return await aiohttp_jinja2.render_template_async(
                "raceclasses.html",
                self.request,
                {
                    "action": action,
                    "raceclasses": raceclasses,
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "lopsinfo": "Klasser",
                    "klasse": klasse,
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
        action = ""
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
                    "order": int(form["order"]),
                    "ageclass_name": str(form["ageclass_name"]),
                    "no_of_contestants": str(form["no_of_contestants"]),
                }

                result = await RaceclassesAdapter().update_raceclass(
                    user["token"], event_id, id, request_body
                )
                informasjon = f"Informasjon er oppdatert - {result}"
            elif "update_order" in form.keys():
                for input in form.keys():
                    if input.startswith("id_"):
                        id = str(form[input])
                        race_class = await RaceclassesAdapter().get_raceclass(
                            user["token"], event_id, id
                        )
                        race_class["order"] = int(form[f"order_{id}"])
                        result = await RaceclassesAdapter().update_raceclass(
                            user["token"], event_id, id, race_class
                        )
                        logging.info(
                            f"New race_class: {race_class}- update result {result}"
                        )
                informasjon = "Rekkefølgen er oppdatert."
                action = "next_bibs"
            # Create classes from list of contestants
            elif "generate_raceclasses" in form.keys():
                informasjon = await EventsAdapter().generate_classes(
                    user["token"], event_id
                )
                action = "next_order"
            elif "refresh_no_of_contestants" in form.keys():
                informasjon = "TODO: Antall deltakere pr. klasse er oppdatert."
            # delete
            elif "delete_one" in form.keys():
                res = await RaceclassesAdapter().delete_raceclass(
                    user["token"], event_id, str(form["id"])
                )
                informasjon = f"Klasse er slettet - {res}"
            # delete_all
            elif "delete_all" in form.keys():
                res = await RaceclassesAdapter().delete_all_raceclasses(
                    user["token"], event_id
                )
                informasjon = f"Klasser er slettet - {res}"

        except Exception as e:
            logging.error(f"Error: {e}")
            informasjon = f"Det har oppstått en feil - {e.args}."

        return web.HTTPSeeOther(
            location=f"/raceclasses?event_id={event_id}&action={action}&informasjon={informasjon}"
        )
