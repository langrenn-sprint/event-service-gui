"""Module for raceclasses adapter."""
import logging
import os
from typing import List

from aiohttp import ClientSession

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
                _newvalue = {"Løpsklasse": new_data[f"raceclass_{new_data[element]}"]}
                result = await db.klasser_collection.update_one(
                    _myquery, {"$set": _newvalue}
                )
                logging.debug(result)
                # update raceclass
                _newvalue = {"Rekkefølge": new_data[f"order_{new_data[element]}"]}
                result = await db.klasser_collection.update_one(
                    _myquery, {"$set": _newvalue}
                )
                logging.debug(f"Updated {new_data[element]}: {result}")

        return returncode
