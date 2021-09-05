"""Utilities module for events resources."""

import logging
from typing import Optional


def get_ageclasses_from_xml(eventid, entries) -> list:
    """Extract ageclasses info from xml object."""
    # enrich data send event to backend
    ageclasses = []
    order = 0
    for entry in entries:
        order = order + 1
        name = entry.find("EntryClass").get("shortName")
        raceclass = name.replace(" ", "")
        raceclass = raceclass.replace("Menn", "M")
        raceclass = raceclass.replace("Kvinner", "K")
        raceclass = raceclass.replace("junior", "J")
        raceclass = raceclass.replace("Junior", "J")
        raceclass = raceclass.replace("Felles", "F")
        raceclass = raceclass.replace("år", "")
        ageclass = {
            "name": name,
            "order": order,
            "raceclass": raceclass,
            "eventid": eventid,
            "distance": entry.find("Exercise").get("name"),
        }
        ageclasses.append(ageclass)
        logging.info(f"Ageclass found: {ageclass}")

    return ageclasses


def get_contestant_info_from_xml(contestant, ageclass: str) -> Optional[str]:
    """Extract person info from xml object."""
    c_name = ""
    c_birthdate = ""
    c_club = ""
    c_team = ""
    c_district = ""
    c_email = ""

    name = contestant.find("Name")
    family = name.find("Family")
    given = name.find("Given")
    c_name = f"{given.text} {family.text}"
    birthdate = contestant.find("BirthDate").attrib
    c_birthdate = (
        f"{birthdate.get('year')}.{birthdate.get('month')}.{birthdate.get('day')}"
    )
    c_club = contestant.get("clubName")
    c_team = contestant.find("Team").get("name")
    c_district = contestant.find("District").get("name")
    c_email = contestant.find("Email").text
    # send contestant to backend
    request_body = {
        "name": c_name,
        "birthdate": c_birthdate,
        "club": c_club,
        "team": c_team,
        "district": c_district,
        "email": c_email,
        "ageclass": ageclass,
    }
    logging.info(f"Person, request body: {request_body}")

    return request_body


def get_event_info_from_xml(event) -> Optional[str]:
    """Extract person info from xml object."""
    c_name = event.find("EventName").text
    c_nifeventid = event.find("EventId").text
    c_date = event.get("startDate")
    c_organiser = event.find("OrganizerName").text
    c_venue = event.find("CompetitionVenue").get("startingvenue")
    # send event to backend
    request_body = {
        "name": c_name,
        "nifid": c_nifeventid,
        "date": c_date,
        "organiser": c_organiser,
        "venue": c_venue,
    }
    logging.info(f"Event, request body: {request_body}")

    return request_body
