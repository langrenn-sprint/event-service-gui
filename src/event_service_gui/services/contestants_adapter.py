"""Module for contestants adapter."""
import logging
from typing import List

from aiohttp import ClientSession

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
