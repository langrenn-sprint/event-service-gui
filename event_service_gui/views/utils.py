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
        return web.HTTPSeeOther(location=f"/login?informasjon={informasjon}")  # type: ignore

    return {"name": session["username"], "token": session["token"]}


async def check_login_open(self) -> dict:
    """Check loging and return user credentials."""
    user = {}
    session = await get_session(self.request)
    loggedin = UserAdapter().isloggedin(session)
    if loggedin:
        user = {
            "name": session["username"],
            "loggedin": True,
            "token": session["token"],
        }
    else:
        user = {"name": "Gjest", "loggedin": False, "token": ""}

    return user


async def get_event(token: str, event_id: str) -> dict:
    """Get event - return new if no event found."""
    event = {"id": event_id, "name": "Langrenn-sprint", "organiser": "Ikke valgt"}
    if event_id != "":
        logging.debug(f"get_event {event_id}")
        event = await EventsAdapter().get_event(token, event_id)

    return event


def get_qualification_text(race: dict) -> str:
    """Generate a text with info about qualification rules."""
    text = ""
    if race["datatype"] == "individual_sprint":
        for key, value in race["rule"].items():
            if key == "S":
                for x, y in value.items():
                    if x == "A" and y > 0:
                        text += f"{y} til semi A. "
                    elif x == "C" and y > 0:
                        text += "Resten til semi C. "
            elif key == "F":
                for x, y in value.items():
                    if x == "A":
                        text += f"{y} til finale A. "
                    elif x == "B" and y > 8:
                        text += "Resten til finale B. "
                    elif x == "B":
                        text += f"{y} til finale B. "
                    elif x == "C" and y > 8:
                        text += "Resten til finale C. "
                    elif x == "C":
                        text += f"{y} til finale C. "
    return text


def get_raceplan_summary(races: list, raceclasses: list) -> list:
    """Generate a summary with key timing for the raceplan."""
    summary = []
    # create a dict of all raceclasses and populate
    # loop raceclasses and find key parameters
    for raceclass in raceclasses:
        class_summary = {"name": raceclass["name"]}
        class_summary["no_of_contestants"] = raceclass["no_of_contestants"]
        # loop through races - update start time pr round pr class
        for race in reversed(races):
            if race["raceclass"] == raceclass["name"]:
                if race["datatype"] == "individual_sprint":
                    if race["round"] == "Q":
                        class_summary["timeQ"] = race["start_time"][-8:]
                        class_summary["orderQ"] = race["order"]
                    elif race["round"] == "S":
                        class_summary["timeS"] = race["start_time"][-8:]
                        class_summary["orderS"] = race["order"]
                    elif race["round"] == "F":
                        class_summary["timeF"] = race["start_time"][-8:]
                        class_summary["orderF"] = race["order"]
        summary.append(class_summary)
    logging.debug(summary)
    return summary
