"""Module for raceclasses adapter."""
import logging
import os
from typing import List

from aiohttp import ClientSession
from aiohttp import hdrs
from aiohttp import web
from multidict import MultiDict

EVENT_SERVICE_HOST = os.getenv("EVENT_SERVICE_HOST", "localhost")
EVENT_SERVICE_PORT = os.getenv("EVENT_SERVICE_PORT", "8082")
EVENT_SERVICE_URL = f"http://{EVENT_SERVICE_HOST}:{EVENT_SERVICE_PORT}"


class RaceclassesAdapter:
    """Class representing raceclasses."""

    async def create_ageclass(
        self, token: str, event_id: str, request_body: dict
    ) -> str:
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
                f"{EVENT_SERVICE_URL}/events/{event_id}/ageclasses",
                headers=headers,
                json=request_body,
            ) as resp:
                if resp.status == 201:
                    logging.debug(f"create ageclass - got response {resp}")
                    location = resp.headers[hdrs.LOCATION]
                    id = location.split(os.path.sep)[-1]
                else:
                    logging.error(f"create_ageclass failed - {resp.status}")
                    raise web.HTTPBadRequest(reason="Create ageclass failed.")

        return id

    async def delete_all_ageclasses(self, token: str, event_id: str) -> str:
        """Delete all ageclasses in one event function."""
        headers = {
            hdrs.AUTHORIZATION: f"Bearer {token}",
        }

        async with ClientSession() as session:
            async with session.delete(
                f"{EVENT_SERVICE_URL}/events/{event_id}/ageclasses",
                headers=headers,
            ) as resp:
                res = resp.status
                logging.debug(f"delete all result - got response {resp}")
                if res == 204:
                    pass
                else:
                    raise Exception(f"delete_all_ageclasses failed: {resp}")
        return str(res)

    async def delete_ageclass(self, token: str, event_id: str, ageclass_id: str) -> str:
        """Delete one ageclass function."""
        headers = {
            hdrs.AUTHORIZATION: f"Bearer {token}",
        }

        async with ClientSession() as session:
            async with session.delete(
                f"{EVENT_SERVICE_URL}/events/{event_id}/ageclasses/{ageclass_id}",
                headers=headers,
            ) as resp:
                res = resp.status
                logging.debug(f"delete result - got response {resp}")
                if res == 204:
                    pass
                else:
                    raise Exception(f"delete_ageclass failed: {resp}")
        return str(res)

    async def generate_ageclasses(self, token: str, event_id: str) -> str:
        """Generate ageclasses based upon registrations."""
        headers = MultiDict(
            {
                hdrs.AUTHORIZATION: f"Bearer {token}",
            }
        )
        url = f"{EVENT_SERVICE_URL}/events/{event_id}/generate-ageclasses"
        async with ClientSession() as session:
            async with session.post(url, headers=headers) as resp:
                res = resp.status
                logging.debug(f"generate_ageclasses result - got response {resp}")
                if res == 201:
                    pass
                else:
                    raise Exception(f"generate_ageclasses failed: {resp}")
        information = "Opprettet aldersklasser."
        return information

    async def get_ageclass(self, token: str, event_id: str, ageclass_id: str) -> dict:
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
                f"{EVENT_SERVICE_URL}/events/{event_id}/ageclasses/{ageclass_id}",
                headers=headers,
            ) as resp:
                logging.debug(f"get_ageclass - got response {resp.status}")
                if resp.status == 200:
                    ageclass = await resp.json()
                else:
                    logging.error(f"Error in get_ageclass: {resp}")
        return ageclass

    async def get_ageclasses(self, token: str, event_id: str) -> List:
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
                f"{EVENT_SERVICE_URL}/events/{event_id}/ageclasses", headers=headers
            ) as resp:
                if resp.status == 200:
                    all_ageclasses = await resp.json()
                    for ageclass in all_ageclasses:
                        try:
                            if ageclass["event_id"] == event_id:
                                ageclasses.append(ageclass)
                        except Exception as e:
                            logging.error(f"Error - data quality: {e}")
                elif resp.status == 401:
                    logging.info("TODO Performing new login")
                    # Perform login
                else:
                    logging.error(f"Error {resp.status} getting ageclasses: {resp} ")
        return ageclasses

    async def update_ageclass(
        self, token: str, event_id: str, id: str, new_data: dict
    ) -> int:
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
                f"{EVENT_SERVICE_URL}/events/{event_id}/ageclasses/{id}",
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
