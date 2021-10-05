"""Resource module for main view."""
import logging

from aiohttp import web
import aiohttp_jinja2

from event_service_gui.services import EventsAdapter
from .utils import check_login, get_event


class Events(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get route function that return the events page."""
        try:
            event_id = self.request.rel_url.query["event_id"]
        except Exception:
            event_id = ""
        try:
            informasjon = self.request.rel_url.query["informasjon"]
        except Exception:
            informasjon = ""

        try:
            user = await check_login(self)
            event = await get_event(user["token"], event_id)

            try:
                create_new = False
                new = self.request.rel_url.query["new"]
                if new != "":
                    create_new = True
            except Exception:
                create_new = False

            competition_formats = await EventsAdapter().get_competition_formats(
                user["token"]
            )
            logging.debug(f"Format: {competition_formats}")

            return await aiohttp_jinja2.render_template_async(
                "events.html",
                self.request,
                {
                    "competition_formats": competition_formats,
                    "create_new": create_new,
                    "lopsinfo": "Informasjon",
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "username": user["name"],
                },
            )
        except Exception as e:
            logging.error(f"Error: {e}. Redirect to main page.")
            return web.HTTPSeeOther(location=f"/?informasjon={e}")

    async def post(self) -> web.Response:
        """Post route function that creates a collection of klasses."""
        # check login
        user = await check_login(self)

        informasjon = ""
        event_id = ""
        try:
            form = await self.request.post()
            logging.debug(f"Form {form}")

            # Create new event
            if "create_manual" in form.keys():
                request_body = {
                    "name": form["name"],
                    "date_of_event": form["date_of_event"],
                    "time_of_event": form["time_of_event"],
                    "competition_format": form["competition_format"],
                    "organiser": form["organiser"],
                    "webpage": form["webpage"],
                    "information": form["information"],
                }
                event_id = await EventsAdapter().create_event(
                    user["token"], request_body
                )
                informasjon = f"Opprettet nytt arrangement,  event_id {event_id}"
            elif "create_file" in form.keys():
                # create event based upon data in xml file
                file = form["file"]
                logging.info(f"File name {file.filename}")
                text_file = file.file
                content = text_file.read()
                logging.debug(f"Content {content}")
                # event_info = get_event_info_from_xml(content)
                # event_id = await EventsAdapter().create_event(user["token"], event_info)
                informasjon = "Opprettet nytt arrangement"

                # add Ageclasses
                # ageclasses = get_ageclasses_from_xml(event_id, content)
                # for ageclass in ageclasses:
                #    id = await RaceclassesAdapter().create_ageclass(user["token"], ageclass)
                #    logging.info(f"Created ageclass with id: {id}")

            elif "update" in form.keys():
                # Update event
                event_id = str(form["event_id"])
                request_body = {
                    "name": form["name"],
                    "date_of_event": form["date_of_event"],
                    "time_of_event": form["time_of_event"],
                    "competition_format": form["competition_format"],
                    "organiser": form["organiser"],
                    "webpage": form["webpage"],
                    "information": form["information"],
                    "time_between_heats": form["time_between_heats"],
                    "time_between_rounds": form["time_between_rounds"],
                    "id": event_id,
                }
                res = await EventsAdapter().update_event(
                    user["token"], event_id, request_body
                )
                informasjon = f"Arrangementinformasjon er oppdatert {res}."
            elif "delete" in form.keys():
                event_id = str(form["event_id"])
                res = await EventsAdapter().delete_event(user["token"], event_id)
                informasjon = f"Arrangement er slettet {res}."
                return web.HTTPSeeOther(location=f"/?informasjon={informasjon}")
        except Exception as e:
            logging.error(f"Error: {e}")
            informasjon = f"Det har oppstått en feil - {e.args}."

        return web.HTTPSeeOther(
            location=f"/events?event_id={event_id}&informasjon={informasjon}"
        )
