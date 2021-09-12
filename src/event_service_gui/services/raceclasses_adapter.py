"""Module for raceclasses adapter."""
import logging
import os
from typing import List

from aiohttp import ClientSession
from aiohttp import hdrs
from aiohttp import web
from multidict import MultiDict

from event_service_gui.services import (
    ContestantsAdapter,
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

    async def generate_ageclasses(self, token: str, eventid: str) -> str:
        """Generate ageclasses based upon registrations."""
        contestants = await ContestantsAdapter().get_all_contestants(token, eventid)
        logging.debug(f"Contestants: {contestants}")
        information = ""
        classes = {}

        for contestant in contestants:
            if contestant["age_class"] in classes:
                tmp = classes[contestant["age_class"]]
                classes[contestant["age_class"]] = tmp + 1
            else:
                classes[contestant["age_class"]] = 1

        i = 0
        for age_class in classes:
            i = i + 1
            race_class = age_class.replace(" ", "")
            race_class = race_class.replace("år", "")
            race_class = race_class.replace("År", "")
            race_class = race_class.replace("Menn", "M")
            race_class = race_class.replace("Kvinner", "K")
            race_class = race_class.replace("Junior", "J")
            race_class = race_class.replace("Senior", "S")
            request_body = {
                "age_class": age_class,
                "distance": "None",
                "event_id": eventid,
                "order": i,
                "race_class": race_class,
                "contestants": classes[age_class],
            }
            result = await RaceclassesAdapter().create_ageclass(token, request_body)
            logging.debug(f"Create ageclass: {result}")
        information = f"Opprettet {i} aldersklasser: {classes}"
        return information

    async def get_ageclass(self, token: str, ageclass_id: str) -> dict:
        """Get all ageclass function."""
        headers = MultiDict(
            {
                hdrs.CONTENT_TYPE: "application/json",
                hdrs.AUTHORIZATION: f"Bearer {token}",
            }
        )
        ageclass = {}
        async with ClientSession() as session:
            async with session.get(
                f"{EVENT_SERVICE_URL}/ageclasses/{ageclass_id}",
                headers=headers,
            ) as resp:
                logging.debug(f"get_ageclass - got response {resp.status}")
                if resp.status == 200:
                    ageclass = await resp.json()
                else:
                    logging.error(f"Error in get_ageclass: {resp}")
        return ageclass

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
                        try:
                            if ageclass["event_id"] == eventid:
                                ageclasses.append(ageclass)
                        except Exception as e:
                            logging.error(f"Error - data quality: {e}")
                elif resp.status == 401:
                    logging.info("TODO Performing new login")
                    # Perform login
                else:
                    logging.error(f"Error {resp.status} getting ageclasses: {resp} ")
        return ageclasses

    async def update_ageclass(self, token: str, id: str, new_data: dict) -> int:
        """Update klasser function."""
        returncode = 201
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
                json=new_data,
            ) as resp:
                returncode = resp.status
                if resp.status == 200:
                    pass
                elif resp.status == 401:
                    logging.info("TODO Performing new login")
                    # Perform login
                else:
                    logging.error(f"Error {resp.status} update ageclass: {resp} ")

        return returncode

    # todo - update
    async def update_participant_count_mongo(self, db, new_classes: dict) -> int:
        """Update klasser function."""
        returncode = 201
        try:

            for ageclass in new_classes:
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
