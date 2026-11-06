"""Resource module for users view."""

import logging
from http import HTTPStatus

import aiohttp_jinja2
from aiohttp import web

from event_service_gui.adapters import UserAdapter

from .utils import (
    check_admin,
    error_message,
    raise_error,
)

NO_ACCESS = "Du har ikke tilgang til brukeradministrasjon. Krever rollen admin."


class Users(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get route function that return the index page."""
        user = await check_admin(self, NO_ACCESS)
        try:
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
                try:
                    users = await UserAdapter().get_all_users(user["token"])
                except web.HTTPForbidden as e:
                    informasjon = e.reason
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
            raise_error(self, e)

    async def post(self) -> web.Response:
        """Get route function that return the index page."""
        informasjon = ""
        user = await check_admin(self, NO_ACCESS)

        try:
            form = await self.request.post()

            # Create new event
            if "create" in form:
                w_id = await UserAdapter().create_user(
                    user["token"],
                    str(form["newrole"]),
                    str(form["newusername"]),
                    str(form["newpassword"]),
                )
                informasjon = f"Ny bruker opprettet med id {w_id}"
            elif "delete" in form:
                w_id = str(form["id"])
                logging.info(f"Enter delete {w_id}")
                res = await UserAdapter().delete_user(user["token"], w_id)
                if res == HTTPStatus.NO_CONTENT:
                    informasjon = "Bruker er slettet."
                else:
                    informasjon = f"En feil oppstod {res}."
            else:
                informasjon = "Ingen endringer utført"

        except web.HTTPForbidden as e:
            informasjon = e.reason
        except Exception as e:
            informasjon = error_message(self, e)

        raise web.HTTPSeeOther(location=f"/users?informasjon={informasjon}")
