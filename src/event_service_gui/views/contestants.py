"""Resource module for main view."""
import logging

from aiohttp import web
import aiohttp_jinja2
from aiohttp_session import get_session

from event_service_gui.services import (
    ContestantsAdapter,
    EventsAdapter,
    UserAdapter,
)


class Contestants(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get route function that return the index page."""
        try:
            eventid = self.request.rel_url.query["eventid"]
        except Exception:
            eventid = ""
        if eventid == "":
            informasjon = "Ingen event valgt."
            return web.HTTPSeeOther(location=f"/?informasjon={informasjon}")

        # check login
        username = ""
        session = await get_session(self.request)
        loggedin = UserAdapter().isloggedin(session)
        if not loggedin:
            return web.HTTPSeeOther(location=f"/login?eventid={eventid}")
        username = str(session["username"])
        token = str(session["token"])

        try:
            informasjon = self.request.rel_url.query["informasjon"]
        except Exception:
            informasjon = ""

        contestant = {}
        try:
            action = self.request.rel_url.query["action"]
            if action == "update_one":
                id = self.request.rel_url.query["id"]
                contestant = await ContestantsAdapter().get_contestant(
                    token, eventid, id
                )

        except Exception:
            action = ""
        logging.debug(f"Action: {action}")

        event = await EventsAdapter().get_event(token, eventid)

        contestants = await ContestantsAdapter().get_all_contestants(token, eventid)
        logging.debug(f"Contestants: {contestants}")
        return await aiohttp_jinja2.render_template_async(
            "contestants.html",
            self.request,
            {
                "action": action,
                "contestants": contestants,
                "contestant": contestant,
                "event": event,
                "eventid": eventid,
                "informasjon": informasjon,
                "lopsinfo": "Deltakere",
                "username": username,
            },
        )

    async def post(self) -> web.Response:
        """Post route function that creates deltakerliste."""
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
            eventid = str(form["eventid"])

            # Create new deltakere
            if "create" in form.keys():
                file = form["file"]
                text_file = file.file
                logging.info(f"File type: {file.content_type}")

                # handle file - xml and csv supported
                if file.content_type == "text/xml":
                    content = text_file.read()
                    logging.debug(f"Content {content}")
                    # contestants = get_all_contestant_info_from_xml(content, eventid)
                    # loop all contestants in entry class
                elif file.content_type == "text/csv":
                    resp = await ContestantsAdapter().create_contestants(
                        token, eventid, text_file
                    )
                    logging.debug(f"Created contestants: {resp}")
                    informasjon = f"Opprettet deltakere: {resp}"
                else:
                    raise Exception(f"Ugyldig filtype {file.content_type}")

            elif "create_one" in form.keys() or "update_one" in form.keys():
                request_body = {
                    "first_name": str(form["first_name"]),
                    "last_name": str(form["last_name"]),
                    "birth_date": str(form["birth_date"]),
                    "gender": str(form["gender"]),
                    "age_class": str(form["age_class"]),
                    "region": str(form["region"]),
                    "club": str(form["club"]),
                    "event_id": eventid,
                    "email": str(form["email"]),
                    "team": str(form["team"]),
                    "minidrett_id": str(form["minidrett_id"]),
                    "bib": str(form["bib"]),
                }
                if "create_one" in form.keys():
                    id = await ContestantsAdapter().create_contestant(
                        token, eventid, request_body
                    )
                    informasjon = f"Deltaker er opprettet - {id}"
                else:
                    request_body["id"] = str(form["id"])
                    result = await ContestantsAdapter().update_contestant(
                        token, eventid, request_body
                    )
                    informasjon = f"Informasjon er oppdatert - {result}"
            # delete
            elif "delete_one" in form.keys():
                result = await ContestantsAdapter().delete_contestant(
                    token, eventid, str(form["id"])
                )
                informasjon = f"Deltaker er slettet - {result}"
            # delete_all
            elif "delete_all" in form.keys():
                result = await ContestantsAdapter().delete_all_contestants(
                    token, eventid
                )
                informasjon = f"Deltakerne er slettet - {result}"
        except Exception as e:
            logging.error(f"Error: {e}")
            informasjon = f"Det har oppstått en feil - {e.args}."

        return web.HTTPSeeOther(
            location=f"/contestants?eventid={eventid}&informasjon={informasjon}"
        )
