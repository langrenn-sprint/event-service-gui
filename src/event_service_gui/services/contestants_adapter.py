"""Module for contestants adapter."""
import logging
from typing import List

from aiohttp import ClientSession
from aiohttp import hdrs
from multidict import MultiDict

# TODO - hente fra configuration
EVENT_SERVICE_URL = "http://localhost:8082/"


class ContestantsAdapter:
    """Class representing contestants."""

    async def get_all_contestants(self) -> List:
        """Get all innstillinger function."""
        contestants = []
        async with ClientSession() as session:
            async with session.get(EVENT_SERVICE_URL + "contestants") as resp:
                logging.debug(f"get_all_contestants - got response {resp.status}")
                if resp.status == "200":
                    contestants = await resp.json()
        return contestants

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
