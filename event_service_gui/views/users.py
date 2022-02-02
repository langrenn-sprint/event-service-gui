"""Resource module for users view."""
import logging

from aiohttp import web
import aiohttp_jinja2
from aiohttp_session import get_session

from event_service_gui.services import UserAdapter
from .utils import check_login


class Users(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get route function that return the index page."""
        try:
            user = await check_login(self)
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
                users = await UserAdapter().get_all_users(user["token"])
                logging.info(f"Users: {users}")

            event = {"name": "Administrasjon", "organiser": "Ikke valgt"}

            return await aiohttp_jinja2.render_template_async(
                "users.html",
                self.request,
                {
                    "lopsinfo": "Brukere",
                    "event": event,
                    "event_id": "",
                    "informasjon": informasjon,
                    "username": user["name"],
                    "users": users,
                    "create_new": create_new,
                },
            )
        except Exception as e:
            logging.error(f"Error: {e}. Redirect to main page.")
            return web.HTTPSeeOther(location=f"/?informasjon={e}")

    async def post(self) -> web.Response:
        """Get route function that return the index page."""
        informasjon = ""
        user = await check_login(self)

        try:
            form = await self.request.post()

            # Create new event
            if "create" in form.keys():
                session = await get_session(self.request)
                id = await UserAdapter().create_user(
                    user["token"],
                    str(form["newrole"]),
                    str(form["newusername"]),
                    str(form["newpassword"]),
                    session,
                )
                informasjon = f"Ny bruker opprettet med id {id}"
            elif "delete" in form.keys():
                id = str(form["id"])
                logging.info(f"Enter delete {id}")
                res = await UserAdapter().delete_user(user["token"], id)
                if res == "204":
                    informasjon = "Bruker er slettet."
                else:
                    informasjon = f"En feil oppstod {res}."
            else:
                informasjon = "Ingen endringer utført"

        except Exception as e:
            logging.error(f"Error: {e}")
            informasjon = f"Det har oppstått en feil - {e.args}."
            error_reason = str(e)
            if error_reason.startswith("401"):
                return web.HTTPSeeOther(
                    location=f"/login?informasjon=Ingen tilgang, vennligst logg inn på nytt. {e}"
                )

        return web.HTTPSeeOther(location=f"/users?informasjon={informasjon}")
