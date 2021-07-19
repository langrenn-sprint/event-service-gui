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
        id = ""
        try:
            form = await self.request.post()
            logging.debug(f"Form {form}")

            # Create new event
            if "create" in form.keys():
                request_body = {
                    "name": form["name"],
                    "date": form["date"],
                    "organiser": form["organiser"],
                    "webpage": form["webpage"],
                    "information": form["information"],
                }
                id = await EventsAdapter().create_event(token, request_body)
                informasjon = f"Opprettet nytt arrangement,  id {id}"
            elif "delete" in form.keys():
                id = form["id"]
                logging.info(f"Enter delete {id}")
                res = await EventsAdapter().delete_event(token, id)
                if res == 204:
                    informasjon = "Arrangement er slettet."
                    return web.HTTPSeeOther(location=f"/?informasjon={informasjon}")
                else:
                    logging.error(f"Error: {res}")
                    informasjon = f"Det har oppstått en feil - {res}."
        except Exception as e:
            logging.error(f"Error: {e}")
            informasjon = f"Det har oppstått en feil - {e.args}."

        return web.HTTPSeeOther(
            location=f"/events?eventid={id}&informasjon={informasjon}"
        )

    async def put(self) -> web.Response:
        """Put route function."""
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

            # Update event
            request_body = {
                "name": form["name"],
                "date": form["date"],
                "organiser": form["organiser"],
                "webpage": form["webpage"],
                "information": form["information"],
            }
            id = form["id"]
            res = await EventsAdapter().update_event(token, id, request_body)
            if res == 204:
                informasjon = "Arrangementinformasjon er oppdatert."
            else:
                informasjon = f"En feil oppstod {res}."
        except Exception as e:
            logging.error(f"Error: {e}")
            informasjon = f"Det har oppstått en feil - {e.args}."

        return web.HTTPSeeOther(
            location=f"/events?eventid={id}&informasjon={informasjon}"
        )
