"""Resource module for main view."""
import logging
import xml.etree.ElementTree as ET

from aiohttp import web
import aiohttp_jinja2
from aiohttp_session import get_session

from event_service_gui.services import EventsAdapter
from event_service_gui.services import RaceclassesAdapter
from event_service_gui.services import UserAdapter
from .utils import get_ageclasses_from_xml, get_event_info_from_xml


class Events(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get route function that return the events page."""
        try:
            eventid = self.request.rel_url.query["eventid"]
        except Exception:
            eventid = ""
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

        # check login
        username = ""
        session = await get_session(self.request)
        loggedin = UserAdapter().isloggedin(session)
        if not loggedin:
            return web.HTTPSeeOther(location=f"/login?event={eventid}")
        username = session["username"]
        token = session["token"]

        event = {"name": "Nytt arrangement", "organiser": "Ikke valgt"}
        if (not create_new) and (eventid != ""):
            logging.debug(f"get_event {eventid}")
            event = await EventsAdapter().get_event(token, eventid)

        return await aiohttp_jinja2.render_template_async(
            "events.html",
            self.request,
            {
                "create_new": create_new,
                "lopsinfo": "Arrangement",
                "event": event,
                "eventid": eventid,
                "informasjon": informasjon,
                "username": username,
            },
        )

    async def post(self) -> web.Response:
        """Post route function that creates a collection of klasses."""
        # check login
        session = await get_session(self.request)
        loggedin = UserAdapter().isloggedin(session)
        if not loggedin:
            return web.HTTPSeeOther(location="/login")
        token = session["token"]

        informasjon = ""
        eventid = ""
        try:
            form = await self.request.post()
            logging.debug(f"Form {form}")

            # Create new event
            if "create_manual" in form.keys():
                request_body = {
                    "name": form["name"],
                    "date": form["date"],
                    "organiser": form["organiser"],
                    "webpage": form["webpage"],
                    "information": form["information"],
                }
                eventid = await EventsAdapter().create_event(token, request_body)
                informasjon = f"Opprettet nytt arrangement,  eventid {eventid}"
            elif "create_file" in form.keys():
                # create event based upon data in xml file
                file = form["file"]
                logging.info(f"File name {file.filename}")
                text_file = file.file
                content = text_file.read()
                logging.debug(f"Content {content}")
                xml_root = ET.fromstring(content)
                request_body = get_event_info_from_xml(xml_root.find("Competition"))
                eventid = await EventsAdapter().create_event(token, request_body)
                informasjon = f"Opprettet nytt arrangement,  eventid {eventid}"

                # add Ageclasses
                ageclasses = get_ageclasses_from_xml(eventid, xml_root.iter("Entry"))
                for ageclass in ageclasses:
                    id = await RaceclassesAdapter().create_ageclass(token, ageclass)
                    logging.info(f"Created ageclass with id: {id}")

            elif "update" in form.keys():
                # Update event
                request_body = {
                    "name": form["name"],
                    "date": form["date"],
                    "organiser": form["organiser"],
                    "webpage": form["webpage"],
                    "information": form["information"],
                }
                eventid = form["eventid"]
                res = await EventsAdapter().update_event(token, eventid, request_body)
                if res == 204:
                    informasjon = "Arrangementinformasjon er oppdatert."
                else:
                    logging.error(f"Error update event: {res}")
                    informasjon = f"En feil oppstod {res}."
            elif "delete" in form.keys():
                eventid = form["eventid"]
                logging.info(f"Enter delete {eventid}")
                res = await EventsAdapter().delete_event(token, eventid)
                if res == 204:
                    informasjon = "Arrangement er slettet."
                    return web.HTTPSeeOther(location=f"/?informasjon={informasjon}")
                else:
                    logging.error(f"Error delete event: {res}")
                    informasjon = f"Det har oppstått en feil - {res}."
        except Exception as e:
            logging.error(f"Error: {e}")
            informasjon = f"Det har oppstått en feil - {e.args}."

        return web.HTTPSeeOther(
            location=f"/events?eventid={eventid}&informasjon={informasjon}"
        )
