"""Resource module for main view."""

import ast
import logging

import aiohttp_jinja2
from aiohttp import web

from event_service_gui.services import EventsAdapter, RaceclassesAdapter

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
                    w_id = self.request.rel_url.query["id"]
                    klasse = await RaceclassesAdapter().get_raceclass(
                        user["token"], event_id, w_id
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
            logging.exception("Error.. Redirect to main page.")
            return web.HTTPSeeOther(location=f"/?informasjon={e}")

    async def post(self) -> web.Response:
        """Post route function that updates a collection of klasses."""
        user = await check_login(self)

        informasjon = ""
        action = "edit_mode"
        form = await self.request.post()
        event_id = str(form["event_id"])
        try:
            # delete_all
            if "delete_all" in form:
                res = await RaceclassesAdapter().delete_all_raceclasses(
                    user["token"], event_id
                )
                informasjon = f"Klasser er slettet - {res}"
            # delete
            elif "delete_one" in form:
                res = await RaceclassesAdapter().delete_raceclass(
                    user["token"], event_id, str(form["id"])
                )
                informasjon = f"Klasse er slettet - {res}"
            # Create classes from list of contestants
            elif "generate_raceclasses" in form:
                informasjon = await EventsAdapter().generate_classes(
                    user["token"], event_id
                )
                informasjon += (
                    " Neste steg: Velg slå sammen klasser eller rediger statrekkefølge."
                )
                return web.HTTPSeeOther(
                    location=f"/raceclasses?event_id={event_id}&action=edit_mode&informasjon={informasjon}"
                )
            elif "merge_ageclasses" in form:
                informasjon = await merge_ageclasses(user, event_id, dict(form))
            elif "refresh_no_of_contestants" in form:
                informasjon = "Ikke implementert. Rediger manuelt pr klasse."
            elif "update_one" in form:
                informasjon = await update_one(user, event_id, dict(form))
            elif "update_order" in form:
                informasjon = await update_order(user, event_id, dict(form))
                return web.HTTPSeeOther(
                    location=f"/tasks?event_id={event_id}&informasjon={informasjon}"
                )

        except Exception as e:
            logging.exception("Error")
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
    for x in form:
        if x.startswith("ageclass_"):
            klasse = await RaceclassesAdapter().get_raceclass(
                user["token"], event_id, form[x]
            )
            no_of_contestants += klasse["no_of_contestants"]
            merged_ageclasses.extend(klasse["ageclasses"])
            old_raceclasses.append(klasse)
    # create new-common class based upon first one - do not allow spaces in name
    new_raceclass_name = str(form["new_raceclass_name"])
    new_raceclass_name = new_raceclass_name.replace(" ", "")

    if len(old_raceclasses) > 1:
        request_body = {
            "name": new_raceclass_name,
            "distance": old_raceclasses[0]["distance"],
            "event_id": event_id,
            "id": old_raceclasses[0]["id"],
            "group": old_raceclasses[0]["group"],
            "order": old_raceclasses[0]["order"],
            "ranking": old_raceclasses[0]["ranking"],
            "seeding": False,
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


async def update_one(user: dict, event_id: str, form: dict) -> str:
    """Extract form data and perform update ageclass."""
    w_id = str(form["id"])
    ranking = False
    try:
        if form["ranking"] == "on":
            ranking = True
    except Exception:
        ranking = False
    ageclasses_str = form["ageclasses"]
    ageclasses = ast.literal_eval(ageclasses_str)
    request_body = {
        "name": str(form["name"]),
        "distance": str(form["distance"]),
        "event_id": event_id,
        "id": w_id,
        "group": int(form["group"]),
        "order": int(form["order"]),
        "ranking": ranking,
        "seeding": False,
        "ageclasses": ageclasses,
        "no_of_contestants": int(form["no_of_contestants"]),
    }
    result = await RaceclassesAdapter().update_raceclass(
        user["token"], event_id, w_id, request_body
    )
    return f"Informasjon er oppdatert - {result}"


async def update_order(user: dict, event_id: str, form: dict) -> str:
    """Extract form data and perform update order in ageclasses."""
    for key, value in form:
        if key.startswith("id_"):
            w_id = str(value)
            race_class = await RaceclassesAdapter().get_raceclass(
                user["token"], event_id, w_id
            )
            igroup = int(form[f"group_{w_id}"])
            iorder = int(form[f"order_{w_id}"])
            race_class["group"] = igroup
            race_class["order"] = iorder
            try:
                if form[f"ranking_{w_id}"] == "on":
                    race_class["ranking"] = True
            except Exception:
                race_class["ranking"] = False
            race_class["seeding"] = False
            result = await RaceclassesAdapter().update_raceclass(
                user["token"], event_id, w_id, race_class
            )
            logging.debug(f"New race_class: {race_class}- update result {result}")
    return "Rekkefølgen er oppdatert. Neste steg: Kjøreplan."
