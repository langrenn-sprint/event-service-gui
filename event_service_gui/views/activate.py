"""Resource module for the activation page, where users set their password (#222).

Admin gives the user a link /activate#<code>. The code is in the fragment,
which browsers never send to a server, so it is not in the access logs. The
page puts it in the form, and it is sent in the body of the POST.
"""

import logging
from http import HTTPStatus
from urllib.parse import urlencode

import aiohttp_jinja2
from aiohttp import web

from event_service_gui.adapters import UserAdapter
from event_service_gui.adapters.user_adapter import (
    INVALID_ACTIVATION,
    MIN_PASSWORD_LENGTH,
    PASSWORD_TOO_SHORT,
)

from .utils import error_text

MISSING_CODE = "Lenken mangler aktiveringskoden. Be admin om en ny lenke."
NOT_EQUAL = "Passordene er ikke like."
ACTIVATED = "Passordet er satt. Logg inn med brukernavnet ditt og det nye passordet."


class Activate(web.View):
    """The activation page. Open: the user is not logged in."""

    async def get(self) -> web.Response:
        """Show the form. The page reads the code from the fragment."""
        return await render(self.request, code="", informasjon="")

    async def post(self) -> web.Response:
        """Set the password, and send the user to the login page."""
        form = await self.request.post()
        code = str(form.get("code", "")).strip()
        password = str(form.get("password", ""))
        if not code:
            informasjon = MISSING_CODE
        elif password != str(form.get("confirm", "")):
            informasjon = NOT_EQUAL
        elif len(password) < MIN_PASSWORD_LENGTH:
            informasjon = PASSWORD_TOO_SHORT
        else:
            informasjon = ""
            try:
                status = await UserAdapter().activate(code, password)
            except Exception as e:
                logging.exception("Error in POST /activate")
                status = 0
                informasjon = error_text(e)
            if status == HTTPStatus.NO_CONTENT:
                query = urlencode({"informasjon": ACTIVATED})
                raise web.HTTPSeeOther(location=f"/login?{query}")
            if status == HTTPStatus.BAD_REQUEST:
                informasjon = INVALID_ACTIVATION
            elif status == HTTPStatus.UNPROCESSABLE_ENTITY:
                informasjon = PASSWORD_TOO_SHORT
            elif status:
                informasjon = "Det har oppstått en feil. Prøv igjen senere."
        return await render(self.request, code=code, informasjon=informasjon)


async def render(request: web.Request, code: str, informasjon: str) -> web.Response:
    """Render the activation page; the code is kept when the form is shown again."""
    response = await aiohttp_jinja2.render_template_async(
        "activate.html",
        request,
        {
            "lopsinfo": "Velg passord",
            "event": {"name": "Administrasjon", "organiser": "Ikke valgt"},
            "event_id": "",
            "informasjon": informasjon,
            "username": "",
            "code": code,
            "min_password_length": MIN_PASSWORD_LENGTH,
        },
    )
    # The page may hold the code: do not let browsers or proxies store it.
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response
