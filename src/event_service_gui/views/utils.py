"""Utilities module for events resources."""

import logging


def get_ageclasses_from_xml(eventid: str, entries: list) -> list:
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
        logging.debug(f"Ageclass found: {ageclass}")

    return ageclasses


def get_contestant_info_from_xml(contestant, ageclass: str, event_id: str) -> dict:
    """Extract person info from xml object."""
    name = contestant.find("Name")
    c_family = name.find("Family").text
    c_given = name.find("Given").text
    birthdate = contestant.find("BirthDate").attrib
    c_birthdate = (
        f"{birthdate.get('year')}-{birthdate.get('month')}-{birthdate.get('day')}"
    )
    c_gender = contestant.get("sex")
    c_club = contestant.get("clubName")
    c_team = contestant.find("Team").get("name")
    c_region = contestant.find("District").get("name")
    c_email = contestant.find("Email").text
    c_idrett_id = contestant.find("Identity").get("value")

    request_body = {
        "bib": "",
        "first_name": c_given,
        "last_name": c_family,
        "birth_date": c_birthdate,
        "gender": c_gender,
        "age_class": ageclass,
        "club": c_club,
        "team": c_team,
        "region": c_region,
        "event_id": event_id,
        "minidrett_id": c_idrett_id,
        "email": c_email,
    }
    logging.debug(f"Contestant, request body: {request_body}")

    return request_body


def get_event_info_from_xml(event) -> dict:
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
    logging.debug(f"Event, request body: {request_body}")

    return request_body
