"""Resource module for main view."""
import logging

from aiohttp import web
import aiohttp_jinja2
from aiohttp_session import get_session

from event_service_gui.services import EventsAdapter
from event_service_gui.services import UserAdapter


class Events(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get route function that return the events page."""
        try:
            event_id = self.request.rel_url.query["event_id"]
        except Exception:
            event_id = ""
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
            return web.HTTPSeeOther(location=f"/login?event={event_id}")
        username = str(session["username"])
        token = str(session["token"])

        event = {"name": "Nytt arrangement", "organiser": "Ikke valgt"}
        if (not create_new) and (event_id != ""):
            logging.debug(f"get_event {event_id}")
            event = await EventsAdapter().get_event(token, event_id)

        return await aiohttp_jinja2.render_template_async(
            "events.html",
            self.request,
            {
                "create_new": create_new,
                "lopsinfo": "Informasjon",
                "event": event,
                "event_id": event_id,
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
        token = str(session["token"])

        informasjon = ""
        event_id = ""
        try:
            form = await self.request.post()
            logging.debug(f"Form {form}")

            # Create new event
            if "create_manual" in form.keys():
                request_body = {
                    "name": form["name"],
                    "date_of_event": form["date_of_event"],
                    "competition_format": form["competition_format"],
                    "organiser": form["organiser"],
                    "webpage": form["webpage"],
                    "information": form["information"],
                }
                event_id = await EventsAdapter().create_event(token, request_body)
                informasjon = f"Opprettet nytt arrangement,  event_id {event_id}"
            elif "create_file" in form.keys():
                # create event based upon data in xml file
                file = form["file"]
                logging.info(f"File name {file.filename}")
                text_file = file.file
                content = text_file.read()
                logging.debug(f"Content {content}")
                # event_info = get_event_info_from_xml(content)
                # event_id = await EventsAdapter().create_event(token, event_info)
                informasjon = "Opprettet nytt arrangement"

                # add Ageclasses
                # ageclasses = get_ageclasses_from_xml(event_id, content)
                # for ageclass in ageclasses:
                #    id = await RaceclassesAdapter().create_ageclass(token, ageclass)
                #    logging.info(f"Created ageclass with id: {id}")

            elif "update" in form.keys():
                # Update event
                event_id = str(form["event_id"])
                request_body = {
                    "name": form["name"],
                    "date_of_event": form["date_of_event"],
                    "competition_format": form["competition_format"],
                    "organiser": form["organiser"],
                    "webpage": form["webpage"],
                    "information": form["information"],
                    "id": event_id,
                }
                res = await EventsAdapter().update_event(token, event_id, request_body)
                informasjon = f"Arrangementinformasjon er oppdatert {res}."
            elif "delete" in form.keys():
                event_id = str(form["event_id"])
                res = await EventsAdapter().delete_event(token, event_id)
                informasjon = f"Arrangement er slettet {res}."
                return web.HTTPSeeOther(location=f"/?informasjon={informasjon}")
        except Exception as e:
            logging.error(f"Error: {e}")
            informasjon = f"Det har oppstått en feil - {e.args}."

        return web.HTTPSeeOther(
            location=f"/events?event_id={event_id}&informasjon={informasjon}"
        )
