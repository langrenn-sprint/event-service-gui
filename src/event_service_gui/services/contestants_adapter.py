"""Module for contestants adapter."""
import logging
import os
from typing import List

from aiohttp import ClientSession
from aiohttp import hdrs, web
from multidict import MultiDict

EVENT_SERVICE_HOST = os.getenv("EVENT_SERVICE_HOST", "localhost")
EVENT_SERVICE_PORT = os.getenv("EVENT_SERVICE_PORT", "8082")
EVENT_SERVICE_URL = f"http://{EVENT_SERVICE_HOST}:{EVENT_SERVICE_PORT}"


class ContestantsAdapter:
    """Class representing contestants."""

    async def create_contestant(
        self, token: str, event_id: str, request_body: dict
    ) -> str:
        """Create new contestant function."""
        id = ""
        headers = MultiDict(
            {
                hdrs.CONTENT_TYPE: "application/json",
                hdrs.AUTHORIZATION: f"Bearer {token}",
            }
        )

        async with ClientSession() as session:
            async with session.post(
                f"{EVENT_SERVICE_URL}/events/{event_id}/contestants",
                headers=headers,
                json=request_body,
            ) as resp:
                if resp.status == 201:
                    logging.debug(f"result - got response {resp}")
                    location = resp.headers[hdrs.LOCATION]
                    id = location.split(os.path.sep)[-1]
                else:
                    logging.error(f"create_contestant failed - {resp.status}")
                    raise web.HTTPBadRequest(reason="Create contestant failed.")

        return id

    async def create_contestants(self, token: str, id: str, inputfile) -> str:
        """Create new contestants function."""
        headers = MultiDict(
            {
                hdrs.CONTENT_TYPE: "application/json",
                hdrs.AUTHORIZATION: f"Bearer {token}",
            }
        )

        async with ClientSession() as session:
            async with session.post(
                f"{EVENT_SERVICE_URL}/contestants/{id}", headers=headers, data=inputfile
            ) as resp:
                res = resp.status
                if res == 201:
                    logging.debug(f"result - got response {resp}")
                else:
                    logging.error(f"create_contestants failed: {resp}")

        return resp.status

    async def get_all_contestants(self, token: str, event_id: str) -> List:
        """Get all contestants function."""
        headers = MultiDict(
            {
                hdrs.CONTENT_TYPE: "application/json",
                hdrs.AUTHORIZATION: f"Bearer {token}",
            }
        )
        contestants = []
        async with ClientSession() as session:
            async with session.get(
                f"{EVENT_SERVICE_URL}/events/{event_id}/contestants", headers=headers
            ) as resp:
                logging.debug(f"get_all_contestants - got response {resp.status}")
                if resp.status == 200:
                    contestants = await resp.json()
                else:
                    logging.error(f"Error in contestants: {resp}")
        return contestants

    async def update_contestants(self, token: str, event_id: str, request_body) -> str:
        """Create new contestants function."""
        logging.info(f"update_contestants, got request_body {request_body}")

        url = f"{EVENT_SERVICE_URL}/events/{event_id}/contestants"
        headers = MultiDict(
            {
                hdrs.CONTENT_TYPE: "application/json",
                hdrs.AUTHORIZATION: f"Bearer {token}",
            }
        )

        async with ClientSession() as session:
            async with session.put(url, headers=headers, json=request_body) as resp:
                res = resp.status
                if res == 204:
                    logging.debug(f"result - got response {resp}")
                else:
                    logging.error(f"create_contestants failed: {resp}")

        return resp.status
