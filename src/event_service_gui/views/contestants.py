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
            return web.HTTPSeeOther(location="/")
        if eventid == "":
            return web.HTTPSeeOther(location="/")

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
        try:
            create_new = False
            new = self.request.rel_url.query["new"]
            if new != "":
                create_new = True
        except Exception:
            create_new = False
        try:
            edit_mode = False
            edit = self.request.rel_url.query["edit_mode"]
            if edit != "":
                edit_mode = True
        except Exception:
            edit_mode = False

        event = await EventsAdapter().get_event(token, eventid)

        contestants = await ContestantsAdapter().get_all_contestants(token, eventid)
        logging.debug(f"Contestants: {contestants}")
        return await aiohttp_jinja2.render_template_async(
            "contestants.html",
            self.request,
            {
                "lopsinfo": "Deltakere",
                "contestants": contestants,
                "create_new": create_new,
                "edit_mode": edit_mode,
                "event": event,
                "eventid": eventid,
                "informasjon": informasjon,
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
                logging.info(f"File type: {file.content_type}")
                i = 0

                # handle file - xml and csv supported
                if file.content_type == "text/xml":
                    text_file = file.file
                    content = text_file.read()
                    logging.debug(f"Content {content}")
                    # contestants = get_all_contestant_info_from_xml(content, eventid)
                    # loop all contestants in entry class
                elif file.content_type == "text/csv":
                    resp = await ContestantsAdapter().create_contestants(
                        token, eventid, form
                    )
                    logging.info(f"Created contestants: {resp}")
                else:
                    raise Exception(f"Ugyldig filtype {file.content_type}")

                informasjon = f"Opprettet {i} deltakere."
            # Update
            elif "update" in form.keys():
                contestant = await ContestantsAdapter().get_contestant(
                    token, eventid, str(form["contestantid"])
                )
                contestant.update({"age_class": form["age_class"]})
                contestant.update({"bib": form["bib"]})

                result = await ContestantsAdapter().update_contestant(
                    token, eventid, contestant
                )
                informasjon = f"Informasjon er oppdatert - {result}"
            # delete
            elif "delete_one" in form.keys():
                result = await ContestantsAdapter().delete_contestant(
                    token, eventid, str(form["contestantid"])
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
