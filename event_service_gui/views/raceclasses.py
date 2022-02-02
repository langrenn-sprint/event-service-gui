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
            igroup = 0
            iorder = 0
            # delete_all
            if "delete_all" in form.keys():
                res = await RaceclassesAdapter().delete_all_raceclasses(
                    user["token"], event_id
                )
                informasjon = f"Klasser er slettet - {res}"
            # delete
            elif "delete_one" in form.keys():
                res = await RaceclassesAdapter().delete_raceclass(
                    user["token"], event_id, str(form["id"])
                )
                informasjon = f"Klasse er slettet - {res}"
            # Create classes from list of contestants
            elif "generate_raceclasses" in form.keys():
                informasjon = await EventsAdapter().generate_classes(
                    user["token"], event_id
                )
                informasjon += " Velg funksjonen slå sammen klasser for å redigere."
                return web.HTTPSeeOther(
                    location=f"/tasks?event_id={event_id}&informasjon={informasjon}"
                )
            elif "merge_ageclasses" in form.keys():
                informasjon = await merge_ageclasses(user, event_id, form)  # type: ignore
            elif "refresh_no_of_contestants" in form.keys():
                informasjon = "TODO: Antall deltakere pr. klasse er oppdatert."
            elif "update_one" in form.keys():
                id = str(form["id"])
                request_body = {
                    "name": str(form["name"]),
                    "distance": str(form["distance"]),
                    "event_id": event_id,
                    "id": id,
                    "group": int(form["group"]),  # type: ignore
                    "order": int(form["order"]),  # type: ignore
                    "ageclass": [str(form["ageclass"])],
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
                        igroup = int(form[f"group_{id}"])  # type: ignore
                        iorder = int(form[f"order_{id}"])  # type: ignore
                        race_class["group"] = igroup
                        race_class["order"] = iorder
                        result = await RaceclassesAdapter().update_raceclass(
                            user["token"], event_id, id, race_class
                        )
                        logging.info(
                            f"New race_class: {race_class}- update result {result}"
                        )
                informasjon = "Rekkefølgen er oppdatert."
                return web.HTTPSeeOther(
                    location=f"/tasks?event_id={event_id}&informasjon={informasjon}"
                )

        except Exception as e:
            logging.error(f"Error: {e}")
            informasjon = f"Det har oppstått en feil - {e.args}."
            error_reason = str(e)
            if error_reason.startswith("401"):
                return web.HTTPSeeOther(
                    location=f"/login?informasjon=Ingen tilgang, vennligst logg inn på nytt. {e}"
                )

        info = f"action={action}&informasjon={informasjon}"
        return web.HTTPSeeOther(location=f"/raceclasses?event_id={event_id}&{info}")


async def merge_ageclasses(user: dict, event_id: str, form: dict) -> str:
    """Extract form data and perform merge ageclasses."""
    old_raceclasses = []
    merged_ageclasses = []
    no_of_contestants = 0
    # get classes to be merged
    for x in form.keys():
        if x.startswith("ageclass_"):
            klasse = await RaceclassesAdapter().get_raceclass(
                user["token"], event_id, form[x]
            )
            no_of_contestants += klasse["no_of_contestants"]
            for ageclass in klasse["ageclasses"]:
                merged_ageclasses.append(ageclass)
            old_raceclasses.append(klasse)
    # create new-common class based upon first one
    if len(old_raceclasses) > 1:
        request_body = {
            "name": str(form["new_raceclass_name"]),
            "distance": old_raceclasses[0]["distance"],
            "event_id": event_id,
            "id": old_raceclasses[0]["id"],
            "group": None,
            "order": None,
            "ageclasses": merged_ageclasses,
            "no_of_contestants": no_of_contestants,
        }
        result = await RaceclassesAdapter().update_raceclass(
            user["token"], event_id, old_raceclasses[0]["id"], request_body
        )
        logging.debug(f"Updated raceclass {request_body}, result {result}")
        # delete remaining
        for raceclass in old_raceclasses[1:]:
            res = await RaceclassesAdapter().delete_raceclass(
                user["token"], event_id, raceclass["id"]
            )
            logging.debug(f"Deleted raceclass {raceclass['id']}, result {res}")
        informasjon = f"Slått sammen klasser {merged_ageclasses}."
        informasjon += " Husk å sette rekkefølge på nytt."
    else:
        informasjon = "Slå sammen klasser - ingen endringer utført"

    return informasjon
