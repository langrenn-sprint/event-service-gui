"""Module for raceclasses adapter."""
import logging
import os
from typing import List

from aiohttp import ClientSession
from aiohttp import hdrs
from aiohttp import web
from multidict import MultiDict

from event_service_gui.services import (
    DeltakereService,
)

EVENT_SERVICE_HOST = os.getenv("EVENT_SERVICE_HOST", "localhost")
EVENT_SERVICE_PORT = os.getenv("EVENT_SERVICE_PORT", "8082")
EVENT_SERVICE_URL = f"http://{EVENT_SERVICE_HOST}:{EVENT_SERVICE_PORT}"


class RaceclassesAdapter:
    """Class representing raceclasses."""

    async def create_ageclass(self, token: str, request_body: dict) -> str:
        """Create new ageclass function."""
        id = ""
        headers = MultiDict(
            {
                hdrs.CONTENT_TYPE: "application/json",
                hdrs.AUTHORIZATION: f"Bearer {token}",
            }
        )

        async with ClientSession() as session:
            async with session.post(
                f"{EVENT_SERVICE_URL}/ageclasses", headers=headers, json=request_body
            ) as resp:
                if resp.status == 201:
                    logging.debug(f"create ageclass - got response {resp}")
                    location = resp.headers[hdrs.LOCATION]
                    id = location.split(os.path.sep)[-1]
                else:
                    logging.error(f"create_ageclass failed - {resp.status}")
                    raise web.HTTPBadRequest(reason="Create ageclass failed.")

        return id

    async def get_ageclasses(self, token: str, eventid: str) -> List:
        """Get all ageclasses function."""
        ageclasses = []
        headers = MultiDict(
            {
                hdrs.CONTENT_TYPE: "application/json",
                hdrs.AUTHORIZATION: f"Bearer {token}",
            }
        )
        async with ClientSession() as session:
            async with session.get(
                f"{EVENT_SERVICE_URL}/ageclasses", headers=headers
            ) as resp:
                if resp.status == 200:
                    all_ageclasses = await resp.json()
                    for ageclass in all_ageclasses:
                        if ageclass["eventid"] == eventid:
                            ageclasses.append(ageclass)
                elif resp.status == 401:
                    logging.info("TODO Performing new login")
                    # Perform login
                else:
                    logging.error(f"Error {resp.status} getting ageclasses: {resp} ")
        return ageclasses

    async def update_ageclasses(self, token, new_data: dict) -> int:
        """Update klasser function."""
        returncode = 201
        for element in new_data:
            if element.startswith("ageclass_"):
                request_body = {
                    "name": new_data[element],
                    "raceclass": new_data[f"raceclass_{new_data[element]}"],
                    "order": new_data[f"order_{new_data[element]}"],
                }
                id = new_data[f"id_{new_data[element]}"]
                headers = MultiDict(
                    {
                        hdrs.CONTENT_TYPE: "application/json",
                        hdrs.AUTHORIZATION: f"Bearer {token}",
                    }
                )
                async with ClientSession() as session:
                    async with session.put(
                        f"{EVENT_SERVICE_URL}/ageclasses/{id}",
                        headers=headers,
                        json=request_body,
                    ) as resp:
                        returncode = resp.status
                        if resp.status == 200:
                            pass
                        elif resp.status == 401:
                            logging.info("TODO Performing new login")
                            # Perform login
                        else:
                            logging.error(
                                f"Error {resp.status} getting ageclasses: {resp} "
                            )

        return returncode

    # todo - update
    async def update_participant_count_mongo(self, db, new_classes: dict) -> int:
        """Update klasser function."""
        returncode = 201
        try:
            ageclasses = []

            for ageclass in ageclasses:
                _myquery = {"name": ageclass["name"]}
                _newvalue = {"Participants": new_classes[ageclass["name"]]}
                result = await db.klasser_collection.update_one(
                    _myquery, {"$set": _newvalue}
                )
                logging.debug(result)
            logging.debug(f"Updated participants: {returncode}")
        except Exception as e:
            logging.error(f"Error: {e}")
            returncode = 401

        return returncode

    async def get_classes_with_participants(self, db) -> dict:
        """Get all classes and count registered contestants."""
        # todo: bør telle direkte i backend - og oppdatere i databasen.
        try:
            contestants = await DeltakereService().get_all_deltakere(db)
            classes = {}

            for contestant in contestants:
                if contestant["name"] not in classes.keys():
                    classes[contestant["name"]] = 1
                else:
                    classes[contestant["name"]] = classes[contestant["name"]] + 1
            logging.info(f"Found classes : {classes.items()}")
        except Exception as e:
            logging.error(f"Error: {e}")

        return classes
