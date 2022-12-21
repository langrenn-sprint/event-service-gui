"""Resource module for main view."""
import logging

from aiohttp import web
import aiohttp_jinja2

from event_service_gui.services import (
    ContestantsAdapter,
    EventsAdapter,
    RaceclassesAdapter,
    RaceplansAdapter,
)
from .utils import check_login, check_login_open, get_event


class Contestants(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get route function that return the index page."""
        action = ""
        available_bib = 0
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

            contestant = {}
            contestants = []
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
                if action == "new_manual":
                    available_bib = await get_available_bib(user["token"], event_id)
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
                "contestants.html",
                self.request,
                {
                    "action": action,
                    "contestants": contestants,
                    "contestant": contestant,
                    "event": event,
                    "event_id": event_id,
                    "available_bib": available_bib,
                    "heat_separators": heat_separators,
                    "info_list": info_list,
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
        valgt_klasse = ""
        try:
            form = await self.request.post()
            logging.debug(f"Form {form}")
            event_id = str(form["event_id"])
            try:
                action = str(form["action"])
            except Exception:
                action = ""  # noqa: F841

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
                elif "seeding_manual" in file.filename:  # type: ignore
                    informasjon = await add_seeding_from_excel(
                        user["token"], event_id, text_file
                    )
                elif file.content_type in allowed_filetypes:  # type: ignore
                    informasjon = await ContestantsAdapter().create_contestants(
                        user["token"], event_id, text_file
                    )
                else:
                    raise Exception(f"Ugyldig filtype {file.content_type}")  # type: ignore
                return web.HTTPSeeOther(
                    location=f"/contestants?event_id={event_id}&informasjon={informasjon}"
                )
            elif "create_one" in form.keys():
                url = await create_one_contestant(user["token"], event_id, form)  # type: ignore
                return web.HTTPSeeOther(location=url)  # type: ignore
            elif "update_one" in form.keys():
                request_body = get_contestant_from_form(event_id, form)  # type: ignore
                request_body["id"] = str(form["id"])
                result = await ContestantsAdapter().update_contestant(
                    user["token"], event_id, request_body
                )
                informasjon = f"Informasjon er oppdatert - {result}"
            elif "delete_select" in form.keys():
                informasjon = "Sletting utført: "
                for key in form.keys():
                    if key.startswith("slett_"):
                        contestant_id = str(form[key])
                        contestant = await ContestantsAdapter().get_contestant(
                            user["token"], event_id, contestant_id
                        )
                        result = await ContestantsAdapter().delete_contestant(
                            user["token"], event_id, contestant
                        )
                        informasjon += f"{key} "
            elif "delete_all" in form.keys():
                result = await ContestantsAdapter().delete_all_contestants(
                    user["token"], event_id
                )
                informasjon = f"Deltakerne er slettet - {result}"
            elif "seeding" in form.keys():
                informasjon = await add_seeding_from_form(user["token"], event_id, form)  # type: ignore
                valgt_klasse = str(form["klasse"])
        except Exception as e:
            logging.error(f"Error: {e}")
            informasjon = f"Det har oppstått en feil - {e.args}."
            error_reason = str(e)
            if error_reason.startswith("401"):
                return web.HTTPSeeOther(
                    location=f"/login?informasjon=Ingen tilgang, vennligst logg inn på nytt. {e}"
                )

        info = f"action={action}&informasjon={informasjon}&klasse={valgt_klasse}"
        return web.HTTPSeeOther(location=f"/contestants?event_id={event_id}&{info}")


async def create_one_contestant(token: str, event_id: str, form: dict) -> str:
    """Load contestants from form."""
    url = ""
    informasjon = ""
    request_body = get_contestant_from_form(event_id, form)  # type: ignore
    if "create_one" in form.keys():
        id = await ContestantsAdapter().create_contestant(token, event_id, request_body)
        logging.debug(f"Etteranmelding {id}")
        informasjon = f"Deltaker med startnr {request_body['bib']} er lagt til."
        informasjon += " Plasser løper i ønsket heat."
        raceclasses = await RaceclassesAdapter().get_raceclasses(token, event_id)
        for raceclass in raceclasses:
            if request_body["ageclass"] in raceclass["ageclasses"]:
                klasse = raceclass["name"]
                # update number of contestants in raceclass
                raceclass["no_of_contestants"] += 1
                result = await RaceclassesAdapter().update_raceclass(
                    token, event_id, raceclass["id"], raceclass
                )
                logging.debug(f"Participant count updated: {result}")
                # redirect user to correct page to add start entry
                info = f"klasse={klasse}&event_id={event_id}"
                info += f"&informasjon={informasjon}"
                url = f"{form['url']}/start_edit?{info}"  # type: ignore
    return url


def get_contestant_from_form(event_id: str, form: dict) -> dict:
    """Load contestants from form."""
    try:
        if len(form["bib"]) > 0:  # type: ignore
            bib = int(form["bib"])  # type: ignore
        else:
            bib = None
    except Exception:
        bib = None
    try:
        if len(form["seeding_points"]) > 0:  # type: ignore
            seeding_points = int(form["seeding_points"])  # type: ignore
        else:
            seeding_points = None
    except Exception:
        seeding_points = None
    contestant = {
        "first_name": str(form["first_name"]),
        "last_name": str(form["last_name"]),
        "birth_date": str(form["birth_date"]),
        "gender": str(form["gender"]),
        "ageclass": str(form["ageclass"]),
        "region": str(form["region"]),
        "club": str(form["club"]),
        "event_id": event_id,
        "email": str(form["email"]),
        "team": str(form["team"]),
        "seeding_points": seeding_points,
        "minidrett_id": str(form["minidrett_id"]),
        "bib": bib,
    }
    return contestant


async def get_heat_separators(token: str, event_id: str, raceclass: str) -> list:
    """Indicate how many racers that will be placed in same heat."""
    heat_separators = []
    races = await RaceplansAdapter().get_races_by_racesclass(token, event_id, raceclass)
    count = 0
    for race in races:
        if race["round"] == "Q":
            count += race["no_of_contestants"]
            heat_separators.append(count)
    return heat_separators


async def add_seeding_from_form(token: str, event_id: str, form: dict) -> str:
    """Load seeding info from form."""
    informasjon = "Seeding oppdatert: "
    for key in form.keys():
        if key.startswith("bib_"):
            new_bib = form[key]
            if new_bib.isnumeric():
                contestant_id = key[4:]
                contestant = await ContestantsAdapter().get_contestant(
                    token, event_id, contestant_id
                )
                contestant["bib"] = int(new_bib)
                result = await ContestantsAdapter().update_contestant(
                    token, event_id, contestant
                )
                logging.debug(result)
                informasjon += (
                    f"Oppdatert: {contestant['bib']} {contestant['last_name']}. "
                )
    return informasjon


async def add_seeding_from_excel(token: str, event_id: str, file) -> str:
    """Load seeding info from excel-file."""
    informasjon = ""
    index_row = 0
    headers = {}
    i_contestants = 0
    contestants = await ContestantsAdapter().get_all_contestants(token, event_id)
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
            minidrett_id = elements[headers["Idrettnr"]]
            if minidrett_id and len(minidrett_id) > 0:
                for contestant in contestants:
                    if contestant["minidrett_id"] == minidrett_id:
                        contestant["seeding_points"] = elements[headers["Seedet"]]
                        result = await ContestantsAdapter().update_contestant(
                            token, event_id, contestant
                        )
                        logging.debug(
                            f"Added seeding for contestant {contestant['id']} - {result}"
                        )
                        i_contestants += 1
                        break
        informasjon = f"Deltakere er opprettet - {i_contestants} totalt"
    return informasjon


async def get_available_bib(token: str, event_id: str) -> int:
    """Find available bib, one above higest assigned."""
    contestants = await ContestantsAdapter().get_all_contestants(token, event_id)
    highest_bib = 0
    for contestant in contestants:
        if contestant["bib"]:
            if contestant["bib"] > highest_bib:
                highest_bib = contestant["bib"]
    available_bib = highest_bib + 1
    return available_bib


async def create_contestants_from_excel(token: str, event_id: str, file) -> str:
    """Load contestants from excel-file."""
    informasjon = ""
    index_row = 0
    headers = {}
    i_contestants = 0
    for oneline in file.readlines():
        index_row += 1
        str_oneline = oneline.decode("utf-8")
        str_oneline = str_oneline.replace("b'", "")
        str_oneline = str_oneline.replace("\r\n", "")
        elements = str_oneline.split(";")
        # identify headers
        if index_row == 1:
            index_column = 0
            for element in elements:
                headers[element] = index_column
                index_column += 1
        else:
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
                "club": elements[headers["Klubb"]],
                "region": elements[headers["Krets"]],
                "event_id": event_id,
                "email": "",
                "team": "",
                "minidrett_id": "",
            }
            try:
                bib = elements[headers["Startnr"]]
                if bib.isnumeric():
                    request_body["bib"] = int(bib)  # type: ignore
            except Exception:
                logging.debug("Startnr ignored")
            try:
                request_body["seeding_points"] = elements[headers["Seedet"]]
            except Exception:
                logging.debug("Seeding ignored")
            id = await ContestantsAdapter().create_contestant(
                token, event_id, request_body
            )
            logging.debug(f"Created contestant {id}")
            i_contestants += 1
        informasjon = f"Deltakere er opprettet - {i_contestants} totalt"
    return informasjon
