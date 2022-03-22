"""Utilities module for gui services."""
import datetime
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


def get_local_time(format: str, time_zone_offset: int) -> str:
    """Return local time, time zone adjusted from global setting."""
    delta_seconds = time_zone_offset * 3600
    local_time_obj = datetime.datetime.now() + datetime.timedelta(seconds=delta_seconds)
    local_time = ""
    if format == "HH:MM":
        local_time = f"{local_time_obj.strftime('%H')}:{local_time_obj.strftime('%M')}"
    else:
        local_time = local_time_obj.strftime("%X")
    return local_time


def get_qualification_text(race: dict) -> str:
    """Generate a text with info about qualification rules."""
    text = ""
    if race["round"] == "R1":
        text = "Alle til runde 2"
    elif race["round"] == "R2":
        text = ""
    else:
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
                if text.count("Resten") == 0:
                    text += "Resten er ute. "
    logging.debug(f"Regel hele: {text}")
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
                    if race["round"] in ["Q", "R1"]:
                        class_summary["timeQ"] = race["start_time"][-8:]
                        class_summary["orderQ"] = race["order"]
                    elif race["round"] in ["S", "R2"]:
                        class_summary["timeS"] = race["start_time"][-8:]
                        class_summary["orderS"] = race["order"]
                    elif race["round"] == "F":
                        class_summary["timeF"] = race["start_time"][-8:]
                        class_summary["orderF"] = race["order"]
        summary.append(class_summary)
    logging.debug(summary)
    return summary


def get_club_logos(contestants: list) -> list:
    """Add link to image with club logo in list."""
    club_logos = {
        "Aske": "https://harnaes.no/sprint/web/asker_logo.png",
        "Bækk": "https://harnaes.no/sprint/web/bsk_logo.png",
        "Bæru": "https://harnaes.no/sprint/web/barums_logo.png",
        "Dike": "https://harnaes.no/sprint/web/dikemark_logo.png",
        "Drøb": "https://harnaes.no/sprint/web/dfi_logo.png",
        "Eids": "https://harnaes.no/sprint/web/eidsvold_logo.png",
        "Fet ": "https://harnaes.no/sprint/web/fet_logo.png",
        "Frog": "https://harnaes.no/sprint/web/frogner_logo.png",
        "Foss": "https://harnaes.no/sprint/web/fossum_logo.png",
        "Gjel": "https://harnaes.no/sprint/web/gjellerasen_logo.png",
        "Gjer": "https://harnaes.no/sprint/web/gjerdrum_logo.png",
        "Gui ": "https://harnaes.no/sprint/web/gui_logo.png",
        "Haka": "https://harnaes.no/sprint/web/hakadal_logo.png",
        "Hasl": "https://harnaes.no/sprint/web/haslum_logo.png",
        "Hemi": "https://harnaes.no/sprint/web/heming_logo.png",
        "Holm": "https://harnaes.no/sprint/web/holmen_logo.png",
        "Høyb": "https://harnaes.no/sprint/web/hsil_logo.png",
        "IL J": "https://harnaes.no/sprint/web/jardar_logo.png",
        "Jutu": "https://harnaes.no/sprint/web/jutul_logo.png",
        "Kjel": "https://harnaes.no/sprint/web/kjelsaas_logo.png",
        "Koll": "https://harnaes.no/sprint/web/koll_log.png",
        "Lill": "https://harnaes.no/sprint/web/lillomarka_logo.png",
        "Lomm": "https://harnaes.no/sprint/web/lommedalens_logo.png",
        "Lyn ": "https://harnaes.no/sprint/web/lyn_ski_logo.png",
        "Løre": "https://harnaes.no/sprint/web/lorenskog_ski_logo.png",
        "Moss": "https://harnaes.no/sprint/web/moss_logo.png",
        "Nes ": "https://harnaes.no/sprint/web/nes_logo.png",
        "Neso": "https://harnaes.no/sprint/web/nesodden_logo.png",
        "Nitt": "https://harnaes.no/sprint/web/nittedal_logo.png",
        "Njår": "https://harnaes.no/sprint/web/njard_logo.png",
        "Oppe": "https://harnaes.no/sprint/web/oppegard_logo.png",
        "Rust": "https://harnaes.no/sprint/web/rustad_logo.png",
        "Røa ": "https://harnaes.no/sprint/web/roa_logo.png",
        "Ræli": "https://harnaes.no/sprint/web/ralingen_logo.png",
        "Sked": "https://harnaes.no/sprint/web/skedsmo_logo.png",
        "Spyd": "https://harnaes.no/sprint/web/spydeberg_logo.png",
        "Stra": "https://harnaes.no/sprint/web/strandbygda_logo.png",
        "Sørk": "https://harnaes.no/sprint/web/sif_logo.png",
        "Tist": "https://harnaes.no/sprint/web/tistedalen_logo.png",
        "Trøs": "https://harnaes.no/sprint/web/trosken_logo.png",
        "Idre": "https://harnaes.no/sprint/web/try_logo.png",
        "Vest": "https://harnaes.no/sprint/web/vestreaker_logo.png",
        "Ørsk": "https://harnaes.no/sprint/web/orskog_logo.png",
        "Øvre": "https://harnaes.no/sprint/web/overvoll_logo.png",
        "Årvo": "https://harnaes.no/sprint/web/arvoll_logo.png",
    }
    for contestant in contestants:
        try:
            contestant["club_logo"] = club_logos[contestant["club"][:4]]
        except Exception:
            logging.error(f"Unknown club - {contestant}")

    return contestants
