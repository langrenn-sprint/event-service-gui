"""Resource module for main view."""
import logging

from aiohttp import web
import aiohttp_jinja2
from aiohttp_session import get_session

from event_service_gui.services import ContestantsAdapter, EventsAdapter, UserAdapter


class Contestants(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get route function that return the index page."""
        try:
            id = self.request.rel_url.query["eventid"]
        except Exception:
            return web.HTTPSeeOther(location="/")

        # check login
        username = ""
        session = await get_session(self.request)
        loggedin = UserAdapter().isloggedin(session)
        if not loggedin:
            return web.HTTPSeeOther(location=f"/login?eventid={id}")
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

        event = await EventsAdapter().get_event(token, id)

        # todo - get list of contestants
        contestants = await ContestantsAdapter().get_all_contestants()
        logging.debug(f"Contestants: {contestants}")
        return await aiohttp_jinja2.render_template_async(
            "contestants.html",
            self.request,
            {
                "lopsinfo": "Deltakere",
                "contestants": contestants,
                "create_new": create_new,
                "event": event,
                "eventid": id,
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
            id = form["eventid"]

            # Create new deltakere
            if "create" in form.keys():
                file = form["file"]
                logging.info(f"File {file}")
                text_file = file.file
                content = text_file.read()
                logging.debug(f"Content {content}")

                # todo: test when backend service is available
                res = "0"
                res = await ContestantsAdapter().create_contestants(token, id, content)
                if res == 201:
                    informasjon = "Deltakere ble registrert."
                else:
                    informasjon = f"Det har oppstått en feil, kode: {res}."

        except Exception as e:
            logging.error(f"Error: {e}")
            informasjon = f"Det har oppstått en feil - {e.args}."

        return web.HTTPSeeOther(
            location=f"/contestants?eventid={id}&informasjon={informasjon}"
        )
