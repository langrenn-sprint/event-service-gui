"""Resource module for login view."""
import logging

from aiohttp import web
import aiohttp_jinja2
from aiohttp_session import get_session
from aiohttp_session import new_session

from event_service_gui.services import LoginAdapter


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
            eventid = self.request.rel_url.query["eventid"]
        except Exception:
            eventid = ""

        try:
            create_new = False
            new = self.request.rel_url.query["new"]
            if new != "":
                session = await get_session(self.request)
                loggedin = LoginAdapter().isloggedin(session)
                if loggedin:
                    create_new = True
                    username = session["username"]

        except Exception:
            create_new = False

        return await aiohttp_jinja2.render_template_async(
            "login.html",
            self.request,
            {
                "lopsinfo": "Login",
                "event": [],
                "eventid": eventid,
                "informasjon": informasjon,
                "username": username,
                "create_new": create_new,
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
                eventid = self.request.rel_url.query["eventid"]
                logging.debug(f"Event: {eventid}")
            except Exception:
                eventid = ""

            # Create new event
            if "create" in form.keys():
                session = await get_session(self.request)
                token = session["token"]
                id = await LoginAdapter().create_user(
                    token,
                    form["newrole"],
                    form["newusername"],
                    form["newpassword"],
                    session,
                )
                informasjon = f"Ny bruker opprettet med id {id}"
                return web.HTTPSeeOther(
                    location=f"/login?new=True&informasjon={informasjon}"
                )

            else:
                # Perform login
                session = await new_session(self.request)
                result = await LoginAdapter().login(
                    form["username"], form["password"], session
                )
                if result != 200:
                    informasjon = "Innlogging feilet"

        except Exception:
            logging.error("Error handling post - login")
            result = 400

        if result != 200:
            return await aiohttp_jinja2.render_template_async(
                "login.html",
                self.request,
                {
                    "lopsinfo": "Login resultat",
                    "event": [],
                    "eventid": eventid,
                    "informasjon": informasjon,
                },
            )
        elif eventid != "":
            return web.HTTPSeeOther(location=f"/events?event={eventid}")
        else:
            return web.HTTPSeeOther(location="/")
