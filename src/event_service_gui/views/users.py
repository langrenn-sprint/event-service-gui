"""Resource module for users view."""
import logging

from aiohttp import web
import aiohttp_jinja2
from aiohttp_session import get_session

from event_service_gui.services import LoginAdapter


class Users(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get route function that return the index page."""
        # check login
        session = await get_session(self.request)
        loggedin = LoginAdapter().isloggedin(session)
        if not loggedin:
            return web.HTTPSeeOther(location="/login")
        token = session["token"]
        username = session["username"]
        users = []

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

        if not create_new:
            users = await LoginAdapter().get_all_users(token)
            logging.info(f"Users: {users}")

        return await aiohttp_jinja2.render_template_async(
            "users.html",
            self.request,
            {
                "lopsinfo": "Brukere",
                "event": [],
                "eventid": "",
                "informasjon": informasjon,
                "username": username,
                "users": users,
                "create_new": create_new,
            },
        )

    async def post(self) -> web.Response:
        """Get route function that return the index page."""
        informasjon = ""
        logging.debug(f"Login: {self}")

        # check login
        session = await get_session(self.request)
        loggedin = LoginAdapter().isloggedin(session)
        if not loggedin:
            return web.HTTPSeeOther(location="/login")
        token = session["token"]

        try:
            form = await self.request.post()

            # Create new event
            if "create" in form.keys():
                id = await LoginAdapter().create_user(
                    token,
                    form["newrole"],
                    form["newusername"],
                    form["newpassword"],
                    session,
                )
                informasjon = f"Ny bruker opprettet med id {id}"
            elif "delete" in form.keys():
                id = form["id"]
                logging.info(f"Enter delete {id}")
                res = await LoginAdapter().delete_user(token, id)
                if res == 204:
                    informasjon = "Bruker er slettet."
                else:
                    informasjon = f"En feil oppstod {res}."
            else:
                informasjon = "Ingen endringer utført"

        except Exception:
            informasjon = "En feil har oppstått"
            logging.error("Error handling post - users")

        return web.HTTPSeeOther(location=f"/users?informasjon={informasjon}")