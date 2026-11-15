"""Resource module for single result update via ajax."""

import json
import logging

from aiohttp import web

from event_service_gui.adapters import (
    EventsAdapter,
    RaceclassesAdapter,
    TimeEventsAdapter,
)
from event_service_gui.services import (
    RaceclassResultsService,
)

from .utils import check_login, get_event, get_race_kpis


class ResultatUpdate(web.View):
    """Class representing the simple photo update service."""

    async def post(self) -> web.Response:
        """Post route function that updates a collection of photos."""
        informasjon = ""
        form = dict(await self.request.post())
        try:
            action = str(form["action"])
            user = await check_login(self)
            if action in ["DNF", "DNS", "Start"]:
                informasjon = await create_event(user, form, action)
                if "json" in form:
                    event_id = str(form["event_id"])
                    event = await get_event(user["token"], event_id)
                    runde = str(form["runde"])
                    raceclass_name = str(form["raceclass"])
                    raceclass = await RaceclassesAdapter().get_raceclass_by_name(
                        user["token"], event_id, raceclass_name
                    )
                    raceplan_kpis = await get_race_kpis(
                        user["token"], event, [raceclass], runde
                    )
                    response = {
                        "raceplan_kpis": raceplan_kpis,
                        "informasjon": informasjon,
                    }
                    json_response = json.dumps(response)
                    return web.Response(text=json_response)
            elif action == "generate_resultlist":
                event_id = str(form["event_id"])
                event = await get_event(user["token"], event_id)
                raceclass_name = str(form["raceclass"])
                res = await RaceclassResultsService().create_raceclass_results(
                    user["token"], event, raceclass_name
                )
                logging.debug(f"Resultat for {raceclass_name} er publisert. {res}")
                informasjon = f"Resultat for {raceclass_name} er publisert. "
        except Exception as e:
            informasjon = f"Det har oppstått en feil: {e}"
            logging.exception("Result update")
        if "json" in form:
            response = {
                "informasjon": informasjon,
            }
            json_response = json.dumps(response)
            return web.Response(text=json_response)
        return web.Response(text=informasjon)


async def create_event(user: dict, form: dict, action: str) -> str:
    """Extract form data and create one time_event, DNS, DNF or Start."""
    informasjon = ""
    event_id = form["event_id"]
    event = await get_event(user["token"], event_id)
    time_stamp_now = EventsAdapter().get_local_time(event, "log")
    if form["checked"] == "true":
        request_body = {
            "id": "",
            "bib": int(form["bib"]),
            "name": form["name"],
            "club": form["club"],
            "event_id": event_id,
            "race": form["race"],
            "race_id": form["race_id"],
            "timing_point": action,
            "rank": 0,
            "registration_time": time_stamp_now,
            "next_race": "",
            "next_race_id": "",
            "next_race_position": 0,
            "status": "OK",
            "changelog": [
                {
                    "timestamp": time_stamp_now,
                    "user_id": user["name"],
                    "comment": f"{action} created",
                }
            ],
        }
        new_t_e = await TimeEventsAdapter().create_time_event(
            user["token"], request_body
        )
        informasjon = f" Nr {new_t_e['bib']} - {action} registrert. "

        # if Start event delete DNS event if it exists
        if action == "Start":
            # get dns event for bib
            dns_time_events = (
                await TimeEventsAdapter().get_time_events_by_event_id_and_bib(
                    user["token"], event_id, int(form["bib"])
                )
            )
            for dns_time_event in dns_time_events:
                if dns_time_event["timing_point"] == "DNS":
                    # delete
                    await TimeEventsAdapter().delete_time_event(
                        user["token"], dns_time_event["id"]
                    )
                    informasjon += " Slettet DNS registrering. "

    else:
        time_event_id = form["time_event_id"]
        if not time_event_id:
            time_events = await TimeEventsAdapter().get_time_events_by_event_id_and_bib(
                user["token"], event_id, int(form["bib"])
            )
            for time_event in time_events:
                if time_event["race_id"] == form["race_id"]:
                    time_event_id = time_event["id"]
                    break
        await TimeEventsAdapter().delete_time_event(user["token"], time_event_id)
        informasjon = f" Nr {form['bib']} - {action} slettet. "

    # delete old entry if existing
    try:
        if form["old_id"]:
            await TimeEventsAdapter().delete_time_event(user["token"], form["old_id"])
            informasjon += " Slettet gammel registrering."
    except Exception as e:
        logging.debug(f"Delete failed - ignoring {e}")

    return informasjon
