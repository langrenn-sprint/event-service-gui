"""Resource module for login view."""
import logging

from aiohttp import web
import aiohttp_jinja2
from aiohttp_session import get_session
from aiohttp_session import new_session

from event_service_gui.services import UserAdapter


class Login(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get route function that return the index page."""
        username = ""
        try:
            informasjon = self.request.rel_url.query["informasjon"]
        except Exception:
            informasjon = ""
        try:
            event_id = self.request.rel_url.query["event_id"]
        except Exception:
            event_id = ""
        try:
            action = self.request.rel_url.query["action"]
        except Exception:
            action = ""

        if action == "create_new":
            session = await get_session(self.request)
            loggedin = UserAdapter().isloggedin(session)
            if loggedin:
                username = session["username"]

        event = {"name": "Administrasjon", "organiser": "Ikke valgt"}

        return await aiohttp_jinja2.render_template_async(
            "login.html",
            self.request,
            {
                "action": action,
                "lopsinfo": "Login",
                "event": event,
                "event_id": event_id,
                "informasjon": informasjon,
                "username": username,
            },
        )

    async def post(self) -> web.Response:
        """Get route function that return the index page."""
        informasjon = ""
        result = 0
        logging.debug(f"Login: {self}")

        try:
            form = await self.request.post()
            try:
                event_id = self.request.rel_url.query["event_id"]
                logging.debug(f"Event: {event_id}")
            except Exception:
                event_id = ""
            try:
                action = self.request.rel_url.query["action"]
            except Exception:
                action = ""

            # Create new event
            if "create" in form.keys():
                session = await get_session(self.request)
                token = str(session["token"])
                id = await UserAdapter().create_user(
                    token,
                    str(form["newrole"]),
                    str(form["newusername"]),
                    str(form["newpassword"]),
                    session,
                )
                informasjon = f"Ny bruker opprettet med id {id}"
                result = 201
            # Perform login
            elif action == "login":
                session = await new_session(self.request)
                result = await UserAdapter().login(
                    str(form["username"]), str(form["password"]), session
                )
                if result == 200:
                    informasjon = "Innlogget!"
                else:
                    informasjon = f"Innlogging feilet - {result}"

        except Exception as e:
            logging.error(f"Error: {e}")
            informasjon = f"Det har oppstått en feil - {e.args}."
            result = 400

        event = {"name": "Langrenn", "organiser": "Ikke valgt"}
        if result != 200:
            return await aiohttp_jinja2.render_template_async(
                "login.html",
                self.request,
                {
                    "lopsinfo": "Login resultat",
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                },
            )
        else:
            return web.HTTPSeeOther(location=f"/?informasjon={informasjon}")
