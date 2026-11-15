"""Module for foto service."""

import json
import logging
from datetime import datetime, timedelta

from event_service_gui.adapters import (
    ConfigAdapter,
    ContestantsAdapter,
    EventsAdapter,
    PhotosAdapter,
    RaceclassesAdapter,
    RaceplansAdapter,
    StartAdapter,
)


class FotoService:
    """Class representing foto service."""

    async def delete_all_local_photos(self, token: str, event_id: str) -> str:
        """Delete all local copies of photo information."""
        photos = await PhotosAdapter().get_all_photos(token, event_id, starred=False)
        for photo in photos:
            result = await PhotosAdapter().delete_photo(token, photo["id"])
            logging.debug(f"Deleted photo with id {photo['id']}, result {result}")
        return "Alle bilder er slettet."

    async def delete_all_low_confidence_photos(
        self, token: str, event_id: str, limit: int
    ) -> str:
        """Delete all local copies of photo where confidence is below photo."""
        photos = await PhotosAdapter().get_all_photos(token, event_id, starred=False)
        i = 0
        for photo in photos:
            if photo["confidence"] < limit:
                result = await PhotosAdapter().delete_photo(token, photo["id"])
                i += 1
                logging.debug(f"Deleted photo with id {photo['id']}, result {result}")
        return f"{i} bilder med confidence under {limit} er slettet."

    async def star_photo(self, token: str, photo_id: str, starred: bool) -> str:
        """Mark photo as starred, or unstarr."""
        photo = await PhotosAdapter().get_photo(token, photo_id)
        photo["starred"] = starred
        result = await PhotosAdapter().update_photo(token, photo["id"], photo)
        logging.debug(f"Updated photo with id {photo_id} - {result}")
        return "Foto er stjernemerket." if starred else "Stjernemerke fjernet."

    async def update_race_info(self, token: str, event: dict, form: dict) -> str:
        """Update race information in phostos, biblist."""
        informasjon = ""
        icount = 0
        for key, value in form.items():
            if key.startswith("biblist_"):
                try:
                    new_biblist = value
                    photo_id = key[8:]
                    old_biblist = form[f"old_biblist_{photo_id}"]
                    if new_biblist != old_biblist:
                        raceclasses = await RaceclassesAdapter().get_raceclasses(
                            token, event["id"]
                        )
                        photo = await PhotosAdapter().get_photo(token, photo_id)
                        photo["biblist"] = []
                        photo["clublist"] = []

                        # try to identify race information
                        message = {
                            "ai_crop_numbers": json.loads(new_biblist),
                            "ai_numbers": [],
                        }
                        result = await link_ai_info_to_photo(
                            token, photo, message, event, raceclasses
                        )

                        result = await PhotosAdapter().update_photo(
                            token, photo["id"], photo
                        )
                        icount += 1
                        logging.debug(
                            f"Updated photo with id {photo_id} for event {event['name']} - {result}"
                        )
                except Exception:
                    logging.exception(f"Error reading biblist - {value}")
                    informasjon += "En Feil oppstod. "
            elif key.startswith("race_id_"):
                new_race_id = value
                photo_id = key[8:]
                old_race_id = form[f"old_race_id_{photo_id}"]
                if new_race_id != old_race_id:
                    photo = await PhotosAdapter().get_photo(token, photo_id)
                    photo["race_id"] = new_race_id
                    if new_race_id:
                        photo["raceclass"] = form[f"raceclass_{new_race_id}"]
                    else:
                        photo["raceclass"] = ""
                    result = await PhotosAdapter().update_photo(
                        token, photo["id"], photo
                    )
                    icount += 1
                    logging.debug(
                        f"Updated photo with id {photo_id} for event {event['name']} - {result}"
                    )
        return f"Utført {icount} oppdateringer."


async def link_ai_info_to_photo(
    token: str, photo_info: dict, ai_information: dict, event: dict, raceclasses: list
) -> int:
    """Link ai information to photo."""
    # first check for bib on cropped image
    result = 204
    for nummer in ai_information["ai_crop_numbers"]:
        result = await find_race_info_by_bib(
            token, nummer, photo_info, event, raceclasses, 100
        )
    # use time only if by bib was not successful
    if result == 204:
        result = await find_race_info_by_time(token, photo_info, event, 50)
    return result


async def find_race_info_by_bib(  # noqa: PLR0913
    token: str,
    bib: int,
    photo_info: dict,
    event: dict,
    raceclasses: list,
    confidence: int,
) -> int:
    """Analyse photo ai info and add race info to photo."""
    result = 204  # no content
    foundheat = ""
    raceduration = await ConfigAdapter().get_config_int(
        token, event["id"], "RACE_DURATION_ESTIMATE"
    )
    starter = await StartAdapter().get_start_entries_by_bib(token, event["id"], bib)
    if len(starter) > 0:
        for start in starter:
            # check heat (if not already found)
            if foundheat == "":
                foundheat = await verify_heat_time(
                    token,
                    event,
                    photo_info["creation_time"],
                    raceduration,
                    start["race_id"],
                )
                if foundheat != "":
                    photo_info["race_id"] = foundheat
                    result = 200  # OK, found a heat

                    # Get klubb and klasse
                    if bib not in photo_info["biblist"]:
                        try:
                            contestant = (
                                await ContestantsAdapter().get_contestant_by_bib(
                                    token, event["id"], bib
                                )
                            )
                            if contestant:
                                photo_info["biblist"].append(bib)
                                if contestant["club"] not in photo_info["clublist"]:
                                    photo_info["clublist"].append(contestant["club"])
                                photo_info["raceclass"] = find_raceclass(
                                    contestant["ageclass"], raceclasses
                                )
                                photo_info["confidence"] = (
                                    confidence  # identified by bib - high confidence!
                                )
                        except Exception:
                            logging.debug("Missing attribute")
                            result = 206  # Partial content
    return result


async def find_race_info_by_time(
    token: str, photo_info: dict, event: dict, confidence: int
) -> int:
    """Analyse photo time and identify race with best time-match."""
    result = 204  # no content
    raceduration = await ConfigAdapter().get_config_int(
        token, event["id"], "RACE_DURATION_ESTIMATE"
    )
    all_races = await RaceplansAdapter().get_all_races(token, event["id"])
    best_fit_race = {
        "race_id": "",
        "seconds_diff": 10000,
        "raceclass": "",
    }
    for race in all_races:
        seconds_diff = abs(
            get_seconds_diff(photo_info["creation_time"], race["start_time"])
            - raceduration
        )

        if seconds_diff < best_fit_race["seconds_diff"]:
            best_fit_race["seconds_diff"] = seconds_diff
            best_fit_race["race_id"] = race["id"]
            best_fit_race["raceclass"] = race["raceclass"]
            best_fit_race["name"] = f"{race['round']}{race['index']}{race['heat']}"

    if best_fit_race["seconds_diff"] < 10000:
        photo_info["race_id"] = best_fit_race["race_id"]
        photo_info["raceclass"] = best_fit_race["raceclass"]
        result = 200  # OK, found a heat
        photo_info["confidence"] = confidence  # identified by time - medium confidence!
        logging.info(f"Diff - best match race {best_fit_race}")
    return result


def find_raceclass(ageclass: str, raceclasses: list) -> str:
    """Analyse photo tags and identify løpsklasse."""
    funnetklasse = ""
    for klasse in raceclasses:
        if ageclass in klasse["ageclasses"]:
            funnetklasse = klasse["name"]
            break

    return funnetklasse


def format_time(timez: str, zulu: bool) -> str:
    """Convert to normalized time - string formats."""
    t2 = None
    time_zone_offset_g_photos = EventsAdapter().get_global_setting(
        "TIME_ZONE_OFFSET_G_PHOTOS"
    )
    date_patterns = EventsAdapter().get_global_setting("DATE_PATTERNS")
    date_pattern_list = date_patterns.split(";")
    for pattern in date_pattern_list:
        try:
            t1 = datetime.strptime(timez, pattern)
            # calculate new time
            delta_seconds = int(time_zone_offset_g_photos) * 3600
            t2 = t1 + timedelta(seconds=delta_seconds) if zulu else t1
            break
        except ValueError:
            logging.debug(f"Got error parsing time {ValueError}")
    if t2:
        time = f"{t2.strftime('%Y')}-{t2.strftime('%m')}-{t2.strftime('%d')}T{t2.strftime('%X')}"
    else:
        time = ""
    return time


def get_seconds_diff(time1: str, time2: str) -> int:
    """Compare time1 and time2, return time diff in min."""
    t1 = datetime.strptime("1", "%S")  # nitialize time to zero
    t2 = datetime.strptime("1", "%S")

    date_patterns = EventsAdapter().get_global_setting("DATE_PATTERNS")
    date_pattern_list = date_patterns.split(";")
    for pattern in date_pattern_list:
        try:
            t1 = datetime.strptime(time1, pattern)
        except ValueError:
            logging.debug(f"Got error parsing time {ValueError}")
        try:
            t2 = datetime.strptime(time2, pattern)
        except ValueError:
            logging.debug(f"Got error parsing time {ValueError}")

    return int((t1 - t2).total_seconds())


async def verify_heat_time(
    token: str,
    event: dict,
    datetime_foto: str,
    raceduration: int,
    race_id: str,
) -> str:
    """Analyse photo tags and identify heat."""
    foundheat = ""
    if datetime_foto is not None:
        race = await RaceplansAdapter().get_race_by_id(token, race_id)
        if race is not None:
            max_time_dev = await ConfigAdapter().get_config_int(
                token, event["id"], "RACE_TIME_DEVIATION_ALLOWED"
            )
            seconds = get_seconds_diff(datetime_foto, race["start_time"])
            if 0 < seconds < (max_time_dev + raceduration):
                foundheat = race["id"]
                race_name = (
                    f"{race['raceclass']}-{race['round']}{race['index']}{race['heat']}"
                )
                logging.info(
                    f"Diff - confirmed bib {seconds} seconds, for race {race_name}"
                )

    return foundheat
