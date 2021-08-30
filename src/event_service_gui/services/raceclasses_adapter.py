"""Module for raceclasses adapter."""
import logging
import os
from typing import List

from aiohttp import ClientSession

from event_service_gui.services import (
    DeltakereService,
)

EVENT_SERVICE_HOST = os.getenv("EVENT_SERVICE_HOST", "localhost")
EVENT_SERVICE_PORT = os.getenv("EVENT_SERVICE_PORT", "8082")
EVENT_SERVICE_URL = f"http://{EVENT_SERVICE_HOST}:{EVENT_SERVICE_PORT}"


class RaceclassesAdapter:
    """Class representing raceclasses."""

    async def get(self) -> List:
        """Get all ageclasses function."""
        ageclasses = []
        async with ClientSession() as session:
            async with session.get(f"{EVENT_SERVICE_URL}/raceclasses") as resp:
                if resp.status == "200":
                    ageclasses = await resp.json()
                else:
                    logging.error(f"Error in raceclasses: {resp}")
        return ageclasses

    async def get_mongo(self, db) -> List:
        """Get all klasser function."""
        ageclasses = []
        cursor = db.klasser_collection.find()
        for document in await cursor.to_list(length=100):
            ageclasses.append(document)
        return ageclasses

    async def update_mongo(self, db, new_data: dict) -> int:
        """Update klasser function."""
        returncode = 201
        for element in new_data:
            if element.startswith("ageclass_"):
                _myquery = {"Klasse": new_data[element]}
                # update raceclass
                _newvalue = {"Raceclass": new_data[f"raceclass_{new_data[element]}"]}
                result = await db.klasser_collection.update_one(
                    _myquery, {"$set": _newvalue}
                )
                logging.debug(result)
                # update raceclass
                _newvalue = {"Order": new_data[f"order_{new_data[element]}"]}
                result = await db.klasser_collection.update_one(
                    _myquery, {"$set": _newvalue}
                )
                logging.debug(f"Updated {new_data[element]}: {result}")

        return returncode

    async def update_participant_count_mongo(self, db, new_classes: dict) -> int:
        """Update klasser function."""
        returncode = 201
        try:
            ageclasses = await RaceclassesAdapter().get_mongo(db)

            for ageclass in ageclasses:
                _myquery = {"Klasse": ageclass["Klasse"]}
                _newvalue = {"Participants": new_classes[ageclass["Klasse"]]}
                result = await db.klasser_collection.update_one(
                    _myquery, {"$set": _newvalue}
                )
                logging.debug(result)
            logging.debug(f"Updated participants: {returncode}")
        except Exception as e:
            logging.error(f"Error: {e}")
            returncode = 401

        return returncode

    async def get_classes_with_participants(self, db) -> List:
        """Get all classes and count registered contestants."""
        try:
            contestants = await DeltakereService().get_all_deltakere(db)
            classes = {}

            for contestant in contestants:
                if contestant["ÅrsKlasse"] not in classes.keys():
                    classes[contestant["ÅrsKlasse"]] = 1
                else:
                    classes[contestant["ÅrsKlasse"]] = (
                        classes[contestant["ÅrsKlasse"]] + 1
                    )
            logging.info(f"Found classes : {classes.items()}")
        except Exception as e:
            logging.error(f"Error: {e}")

        return classes
