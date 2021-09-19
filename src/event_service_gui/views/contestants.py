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
            event_id = self.request.rel_url.query["event_id"]
        except Exception:
            event_id = ""
        if event_id == "":
            informasjon = "Ingen event valgt."
            return web.HTTPSeeOther(location=f"/?informasjon={informasjon}")

        # check login
        username = ""
        session = await get_session(self.request)
        try:
            loggedin = UserAdapter().isloggedin(session)
            if not loggedin:
                return web.HTTPSeeOther(location=f"/login?event_id={event_id}")
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
                        token, event_id, id
                    )

            except Exception:
                action = ""
            logging.debug(f"Action: {action}")

            event = await EventsAdapter().get_event(token, event_id)

            contestants = await ContestantsAdapter().get_all_contestants(
                token, event_id
            )
            logging.debug(f"Contestants: {contestants}")
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
                    "lopsinfo": "Deltakere",
                    "username": username,
                },
            )
        except Exception as e:
            logging.error(f"Error: {e}. Starting new session.")
            session.invalidate()
            return web.HTTPSeeOther(location="/login")

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
            event_id = str(form["event_id"])

            # Create new deltakere
            if "assign_bibs" in form.keys():
                informasjon = await ContestantsAdapter().assign_bibs(token, event_id)
            elif "create" in form.keys():
                file = form["file"]
                text_file = file.file
                logging.info(f"File type: {file.content_type}")

                # handle file - xml and csv supported
                if file.content_type == "text/xml":
                    content = text_file.read()
                    logging.debug(f"Content {content}")
                    # contestants = get_all_contestant_info_from_xml(content, event_id)
                    # loop all contestants in entry class
                elif file.content_type == "text/csv":
                    resp = await ContestantsAdapter().create_contestants(
                        token, event_id, text_file
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
                    "ageclass": str(form["ageclass"]),
                    "region": str(form["region"]),
                    "club": str(form["club"]),
                    "event_id": event_id,
                    "email": str(form["email"]),
                    "team": str(form["team"]),
                    "minidrett_id": str(form["minidrett_id"]),
                    "bib": str(form["bib"]),
                }
                if "create_one" in form.keys():
                    id = await ContestantsAdapter().create_contestant(
                        token, event_id, request_body
                    )
                    informasjon = f"Deltaker er opprettet - {id}"
                else:
                    request_body["id"] = str(form["id"])
                    result = await ContestantsAdapter().update_contestant(
                        token, event_id, request_body
                    )
                    informasjon = f"Informasjon er oppdatert - {result}"
            # delete
            elif "delete_one" in form.keys():
                result = await ContestantsAdapter().delete_contestant(
                    token, event_id, str(form["id"])
                )
                informasjon = f"Deltaker er slettet - {result}"
            # delete_all
            elif "delete_all" in form.keys():
                result = await ContestantsAdapter().delete_all_contestants(
                    token, event_id
                )
                informasjon = f"Deltakerne er slettet - {result}"
        except Exception as e:
            logging.error(f"Error: {e}")
            informasjon = f"Det har oppstått en feil - {e.args}."

        return web.HTTPSeeOther(
            location=f"/contestants?event_id={event_id}&informasjon={informasjon}"
        )
