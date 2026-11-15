"""Module for photo timing service."""

import logging

from event_service_gui.adapters import (
    EventsAdapter,
    PhotosAdapter,
    RaceplansAdapter,
)

from .time_events_service import TimeEventsService


class PhotoTimingService:
    """Class representing service layer for photo_timing."""

    async def create_time_events_from_photos(self, user: dict, race_id: str) -> str:
        """Identify race_id for a time_event."""
        informasjon = ""
        try:
            race = await RaceplansAdapter().get_race_by_id(user["token"], race_id)
            event = await EventsAdapter().get_event(user["token"], race["event_id"])
            time_stamp_now = EventsAdapter().get_local_time(event, "log")
            photos = await PhotosAdapter().get_photos_by_race_id(user["token"], race_id)
            sorted_photos = sorted(
                photos, key=lambda photo: photo.get("creation_time", ""), reverse=False
            )
            rank = 0

            add_result_list = []
            for photo in sorted_photos:
                try:
                    bibs = photo["biblist"]
                    if len(bibs) == 1:
                        bib = bibs[0]
                        crossing_time = photo["creation_time"]
                        rank += 1
                        new_result = {
                            "id": "",
                            "event_id": photo["event_id"],
                            "bib": bib,
                            "rank": rank,
                            "registration_time": crossing_time,
                            "photo['id']": photo["id"],
                            "race": f"{race['raceclass']}-{race['round']}{race['index']}{race['heat']}",
                            "race_id": race["id"],
                            "timing_point": "Finish",
                            "next_race": "",
                            "next_race_id": "",
                            "next_race_position": 0,
                            "status": "OK",
                            "changelog": [
                                {
                                    "timestamp": time_stamp_now,
                                    "user_id": user["name"],
                                    "comment": "Resultat fra foto passering",
                                }
                            ],
                        }
                        add_result_list.append(new_result)

                except Exception as e:
                    informasjon = f"create_time_event_from_photo: Kunne ikke opprette passering automatisk {photo} - {e}"
                    logging.exception(informasjon)

            # delete old results - if new results exists
            delete_result_list = []
            if len(add_result_list) > 0:
                results = race["results"]
                if len(results) > 0:
                    if "Finish" in results:
                        finish_ranks = results["Finish"]["ranking_sequence"]
                        # check if racer already is in result list
                        delete_result_list.extend(
                            rank_event["id"] for rank_event in finish_ranks
                        )

            if len(add_result_list) > 0 or len(delete_result_list) > 0:
                informasjon = await TimeEventsService().update_finish_time_events(
                    user, delete_result_list, add_result_list
                )
            else:
                informasjon = "Ingen nye resultater funnet i målfoto. "
        except Exception as e:
            informasjon = f"create_time_event_from_photo: {e}"
            logging.exception(informasjon)
        return informasjon
