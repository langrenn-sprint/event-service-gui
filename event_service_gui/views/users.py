"""Resource module for users view."""

import logging
from datetime import UTC, datetime
from http import HTTPStatus
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

import aiohttp_jinja2
from aiohttp import web
from aiohttp_session import get_session

from event_service_gui.adapters import UserAdapter
from event_service_gui.adapters.user_adapter import (
    MIN_PASSWORD_LENGTH,
    PASSWORD_TOO_SHORT,
)

from .utils import (
    check_admin,
    error_message,
    raise_error,
)

NO_ACCESS = "Du har ikke tilgang til brukeradministrasjon. Krever rollen admin."
CANNOT_DELETE_SELF = "Du kan ikke slette brukeren du er logget inn som."
LOCAL_TIMEZONE = ZoneInfo("Europe/Oslo")
# Session key for a new activation link, shown once on the next page.
ACTIVATION_KEY = "new_activation"


def format_time(value: str) -> str:
    """Return an ISO time from user-service as local time, e.g. 08.11.2026 kl. 15:00."""
    time = datetime.fromisoformat(value).astimezone(LOCAL_TIMEZONE)
    return time.strftime("%d.%m.%Y kl. %H:%M")


def activation_status(user: dict) -> str:
    """Return whether the user has set a password, and until when a link works."""
    expires = str(user.get("activation_expires") or "")
    valid = bool(expires) and datetime.fromisoformat(expires) > datetime.now(UTC)
    if user.get("activated", True):
        if valid:
            return f"Aktivert (ny lenke gyldig til {format_time(expires)})"
        return "Aktivert"
    if valid:
        return f"Ikke aktivert (lenken er gyldig til {format_time(expires)})"
    if expires:
        return "Ikke aktivert (lenken er utløpt)"
    return "Ikke aktivert"


def too_short(password: str) -> bool:
    """Return True for a password that is given, but too short."""
    return bool(password) and len(password) < MIN_PASSWORD_LENGTH


def new_link(username: str, activation: dict) -> dict:
    """Return what is shown about a new activation link.

    The code is in the fragment (#), which browsers never send to a server, so
    it is not written to access logs. The username is not secret: the page
    shows it, so the browser can save the new password for it. The page adds
    the address the admin sees in the browser, so the link works behind a
    proxy.
    """
    return {
        "username": username,
        "path": f"/activate?{urlencode({'username': username})}#{activation['code']}",
        "expires": format_time(activation["expires"]),
    }


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
                for _user in users:
                    _user["status"] = activation_status(_user)
                logging.debug(f"Users: {len(users)}")

            # a new activation link is shown once:
            session = await get_session(self.request)
            activation_link = session.pop(ACTIVATION_KEY, None)

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
                    "activation_link": activation_link,
                    "min_password_length": MIN_PASSWORD_LENGTH,
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

            if "create" in form and too_short(str(form.get("newpassword", ""))):
                informasjon = PASSWORD_TOO_SHORT
            elif "create" in form:
                username = str(form["newusername"])
                password = str(form.get("newpassword", ""))
                w_id, activation = await UserAdapter().create_user(
                    user["token"], str(form["newrole"]), username, password
                )
                if activation:
                    session = await get_session(self.request)
                    session[ACTIVATION_KEY] = new_link(username, activation)
                    informasjon = f"Brukeren {username} er opprettet."
                else:
                    informasjon = f"Ny bruker opprettet med id {w_id}"
            elif "new_activation" in form:
                username = str(form.get("username", ""))
                activation = await UserAdapter().create_activation(
                    user["token"], str(form["id"])
                )
                session = await get_session(self.request)
                session[ACTIVATION_KEY] = new_link(username, activation)
                informasjon = f"Ny aktiveringslenke for {username} er laget."
            elif "delete" in form:
                w_id = str(form["id"])
                logging.info(f"Enter delete {w_id}")
                res = await UserAdapter().delete_user(user["token"], w_id)
                if res == HTTPStatus.NO_CONTENT:
                    informasjon = "Bruker er slettet."
                elif res == HTTPStatus.CONFLICT:
                    informasjon = CANNOT_DELETE_SELF
                else:
                    informasjon = f"En feil oppstod {res}."
            else:
                informasjon = "Ingen endringer utført"

        except web.HTTPForbidden as e:
            informasjon = e.reason
        except Exception as e:
            informasjon = error_message(self, e)

        raise web.HTTPSeeOther(location=f"/users?informasjon={informasjon}")
