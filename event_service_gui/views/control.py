"""Resource module for control resources."""
import logging

from aiohttp import web
import aiohttp_jinja2

from event_service_gui.services import (
    RaceclassesAdapter,
    TimeEventsAdapter,
)
from .utils import (
    check_login,
    get_event,
    get_passeringer,
)


class Control(web.View):
    """Class representing the control view."""

    async def get(self) -> web.Response:
        """Get route function that return the passeringer page."""
        event_id = self.request.rel_url.query["event_id"]
        try:
            informasjon = self.request.rel_url.query["informasjon"]
        except Exception:
            informasjon = ""
        try:
            action = self.request.rel_url.query["action"]
        except Exception:
            action = ""
            informasjon = f"Velg funksjon. {informasjon}"
        try:
            valgt_klasse = self.request.rel_url.query["valgt_klasse"]
        except Exception:
            valgt_klasse = ""
        try:
            valgt_heat = self.request.rel_url.query["heat"]
        except Exception:
            valgt_heat = ""

        try:
            user = await check_login(self)
            event = await get_event(user, event_id)

            raceclasses = await RaceclassesAdapter().get_raceclasses(
                user["token"], event_id
            )

            # get passeringer
            passeringer = await get_passeringer(
                user["token"], event_id, action, valgt_klasse
            )
            heatlist = get_heatliste(passeringer)

            """Get route function."""
            return await aiohttp_jinja2.render_template_async(
                "control.html",
                self.request,
                {
                    "action": action,
                    "event": event,
                    "event_id": event_id,
                    "heatlist": heatlist,
                    "informasjon": informasjon,
                    "passeringer": passeringer,
                    "raceclasses": raceclasses,
                    "username": user["name"],
                    "valgt_heat": valgt_heat,
                    "valgt_klasse": valgt_klasse,
                },
            )
        except Exception as e:
            logging.error(f"Error: {e}. Redirect to main page.")
            return web.HTTPSeeOther(location=f"/?informasjon={e}")

    async def post(self) -> web.Response:
        """Post route function that creates deltakerliste."""
        # check login
        user = await check_login(self)
        informasjon = ""
        action = ""
        try:
            form = await self.request.post()
            event_id = str(form["event_id"])
            valgt_klasse = str(form["valgt_klasse"])
            action = str(form["action"])
            if "resolve_error" in form.keys():
                informasjon = await delete_timing_events(user, form)  # type: ignore
        except Exception as e:
            logging.error(f"Error: {e}")
            informasjon = f"Det har oppstått en feil - {e.args}."
            error_reason = str(e)
            if error_reason.startswith("401"):
                return web.HTTPSeeOther(
                    location=f"/login?informasjon=Ingen tilgang, vennligst logg inn på nytt. {e}"
                )

        return web.HTTPSeeOther(
            location=f"/control?event_id={event_id}&informasjon={informasjon}&action={action}&valgt_klasse={valgt_klasse}"
        )


def get_heatliste(passeringer) -> list:
    """Return list of heat with registered passering."""
    heatliste = []
    for passering in passeringer:
        if passering["race"] not in heatliste:
            heatliste.append(passering["race"])
    return heatliste


async def delete_timing_events(user: dict, form: dict) -> str:
    """Extract form data and update time events."""
    informasjon = "Delete result: "
    for key in form.keys():
        if key.startswith("resolved_"):
            response = await TimeEventsAdapter().delete_time_event(
                user["token"], form[key]
            )
            informasjon = f"{informasjon} {response}"
    return informasjon
