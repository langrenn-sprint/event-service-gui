"""Utilities module for gui services."""
import logging

from aiohttp import web
from aiohttp_session import get_session

from event_service_gui.services import EventsAdapter, UserAdapter


async def check_login(self) -> dict:
    """Check loging and return user credentials."""
    session = await get_session(self.request)
    loggedin = UserAdapter().isloggedin(session)
    if not loggedin:
        informasjon = "Logg inn for å se denne siden"
        return web.HTTPSeeOther(location=f"/login?informasjon={informasjon}")

    return {"name": session["username"], "token": session["token"]}


async def get_event(token: str, event_id: str) -> dict:
    """Get event - return new if no event found."""
    event = {"id": event_id, "name": "Nytt arrangement", "organiser": "Ikke valgt"}
    if event_id != "":
        logging.debug(f"get_event {event_id}")
        event = await EventsAdapter().get_event(token, event_id)

    return event


def get_raceplan_summary(races: list) -> list:
    """Generate a summary with key timing for the raceplan."""
    summary = []
    raceclasses = {}

    # create a dict of all raceclasses and populate
    for race in races:
        raceclasses[race["raceclass"]] = race["raceclass"]
    # loop raceclasses and find key parameters
    for raceclassname in raceclasses:
        class_summary = {"name": raceclassname}
        # loop through races - update start time pr round pr class
        for race in races:
            if race["raceclass"] == raceclassname:
                if race["heat"] == 1:
                    if race["round"] == "Q":
                        class_summary["timeQ"] = race["start_time"][-8:]
                    elif race["round"] == "S":
                        class_summary["timeS"] = race["start_time"][-8:]
                    elif race["round"] == "F":
                        class_summary["timeF"] = race["start_time"][-8:]
        summary.append(class_summary)
    logging.info(summary)

    return summary
