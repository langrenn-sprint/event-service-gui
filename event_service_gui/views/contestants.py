"""Resource module for main view."""
import logging

from aiohttp import web
import aiohttp_jinja2

from event_service_gui.services import (
    ContestantsAdapter,
    RaceclassesAdapter,
)
from .utils import check_login, check_login_open, get_event


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
            user = await check_login_open(self)
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
                mylist = []
                for ac_name in klasse["ageclasses"]:
                    mylist.append(ac_name.replace(" ", "%20"))
                klasse["ageclass_web"] = mylist

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

            if valgt_klasse == "":
                contestants = await ContestantsAdapter().get_all_contestants(
                    user["token"], event_id
                )
            else:
                contestants = (
                    await ContestantsAdapter().get_all_contestants_by_ageclass(
                        user["token"], event_id, valgt_klasse
                    )
                )
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
                # handle file - csv supported
                allowed_filetypes = ["text/csv", "application/vnd.ms-excel"]
                if "excel_manual" in file.filename:  # type: ignore
                    informasjon = await create_contestants_from_excel(
                        user["token"], event_id, text_file
                    )
                elif file.content_type in allowed_filetypes:  # type: ignore
                    resp = await ContestantsAdapter().create_contestants(
                        user["token"], event_id, text_file
                    )
                    informasjon = f"Opprettet deltakere: {resp}"
                else:
                    raise Exception(f"Ugyldig filtype {file.content_type}")  # type: ignore
                return web.HTTPSeeOther(
                    location=f"/tasks?event_id={event_id}&informasjon={informasjon}"
                )

            elif "create_one" in form.keys() or "update_one" in form.keys():
                request_body = get_contestant_from_form(event_id, form)  # type: ignore
                if "create_one" in form.keys():
                    id = await ContestantsAdapter().create_contestant(
                        user["token"], event_id, request_body
                    )
                    logging.debug(f"Etteranmelding {id}")
                    informasjon = (
                        f"Deltaker med startnr {request_body['bib']} er lagt til."
                    )
                    informasjon += " Plasser løper i ønsket heat."
                    raceclasses = await RaceclassesAdapter().get_raceclasses(
                        user["token"], event_id
                    )
                    for raceclass in raceclasses:
                        if request_body["ageclass"] in raceclass["ageclasses"]:
                            klasse = raceclass["name"]
                            info = f"klasse={klasse}&event_id={event_id}"
                            info += f"&informasjon={informasjon}"
                            url = f"{form['url']}/start_edit?{info}"  # type: ignore
                            return web.HTTPSeeOther(location=url)
                else:
                    request_body["id"] = str(form["id"])
                    result = await ContestantsAdapter().update_contestant(
                        user["token"], event_id, request_body
                    )
                    informasjon = f"Informasjon er oppdatert - {result}"
            # delete
            elif "delete_select" in form.keys():
                informasjon = "Sletting utført: "
                for key in form.keys():
                    if key.startswith("slett_"):
                        customer_id = str(form[key])
                        result = await ContestantsAdapter().delete_contestant(
                            user["token"], event_id, customer_id
                        )
                        informasjon += f"{key} "

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


def get_contestant_from_form(event_id: str, form: dict) -> dict:
    """Load contestants from form."""
    bib = None
    if len(form["bib"]) > 0:  # type: ignore
        bib = int(form["bib"])  # type: ignore
    ageclass = str(form["ageclass"])
    contestant = {
        "first_name": str(form["first_name"]),
        "last_name": str(form["last_name"]),
        "birth_date": str(form["birth_date"]),
        "gender": str(form["gender"]),
        "ageclass": ageclass,
        "region": str(form["region"]),
        "club": str(form["club"]),
        "event_id": event_id,
        "email": str(form["email"]),
        "team": str(form["team"]),
        "minidrett_id": str(form["minidrett_id"]),
        "bib": bib,
    }
    return contestant


async def create_contestants_from_excel(token: str, event_id: str, file) -> str:
    """Load contestants from excel-file."""
    informasjon = ""
    index_row = 0
    headers = {}
    i_contestants = 0
    for oneline in file.readlines():
        index_row += 1
        str_oneline = str(oneline)
        str_oneline = str_oneline.replace("b'", "")
        elements = str_oneline.split(";")
        # identify headers
        if index_row == 1:
            index_column = 0
            for element in elements:
                headers[element] = index_column
                index_column += 1
        else:
            bib = str(elements[0])
            if bib.isnumeric():
                name = elements[headers["Navn"]]
                all_names = name.split(" ")
                first_name = ""
                last_name = ""
                i = 0
                for one_name in all_names:
                    if i == 0:
                        first_name = one_name
                    else:
                        last_name += one_name + " "
                    i += 1
                request_body = {
                    "first_name": first_name,
                    "last_name": last_name,
                    "birth_date": "",
                    "gender": "",
                    "ageclass": elements[headers["Klasse"]],
                    "region": elements[headers["Krets"]],
                    "club": elements[headers["Klubb"]],
                    "event_id": event_id,
                    "email": "",
                    "team": "",
                    "minidrett_id": "",
                    "bib": int(bib),
                }
                id = await ContestantsAdapter().create_contestant(
                    token, event_id, request_body
                )
                logging.debug(f"Created contestant {id}")
                i_contestants += 1
        informasjon = f"Deltakere er opprettet - {i_contestants} totalt"
    return informasjon
