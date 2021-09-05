"""Resource module for main view."""
import logging
import xml.etree.ElementTree as ET

from aiohttp import web
import aiohttp_jinja2
from aiohttp_session import get_session

from event_service_gui.services import (
    ContestantsAdapter,
    DeltakereService,
    EventsAdapter,
    UserAdapter,
)
from .utils import get_contestant_info_from_xml


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
        username = session["username"]
        token = session["token"]

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

        event = await EventsAdapter().get_event(token, eventid)

        # todo - get list of contestants
        # contestants = await ContestantsAdapter().get_all_contestants()
        contestants = await DeltakereService().get_all_deltakere(self.request.app["db"])
        logging.debug(f"Contestants: {contestants}")
        return await aiohttp_jinja2.render_template_async(
            "contestants.html",
            self.request,
            {
                "lopsinfo": "Deltakere",
                "contestants": contestants,
                "create_new": create_new,
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
        token = session["token"]

        informasjon = ""
        try:
            form = await self.request.post()
            logging.debug(f"Form {form}")
            eventid = form["eventid"]

            # Create new deltakere
            if "create" in form.keys():
                file = form["file"]
                logging.info(f"File name {file.filename}")
                text_file = file.file
                content = text_file.read()
                logging.debug(f"Content {content}")
                xml_root = ET.fromstring(content)
                # loop all entry classes
                ageclasses = []
                for entry in xml_root.iter("Entry"):
                    ageclass = {
                        "name": entry.find("EntryClass").get("shortName"),
                        "distance": entry.find("Exercise").get("name"),
                    }
                    ageclasses.append(ageclass)
                    logging.info(f"Entry: {entry.tag}, {entry.attrib}")
                    # loop all contestants in entry class
                    for contestant in entry.iter("Competitor"):
                        logging.info(f"Cont: {contestant.find('Person')}")
                        request_body = get_contestant_info_from_xml(
                            contestant.find("Person"), ageclass.get("name")
                        )

                        id = await ContestantsAdapter().create_contestant(
                            token, eventid, request_body
                        )
                        logging.info(f"Created contstant, id {id}")
        except Exception as e:
            logging.error(f"Error: {e}")
            informasjon = f"Det har oppstått en feil - {e.args}."

        return web.HTTPSeeOther(
            location=f"/contestants?eventid={eventid}&informasjon={informasjon}"
        )
