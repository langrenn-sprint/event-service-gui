"""Module for raceclasses adapter."""
import logging
from typing import List

from aiohttp import ClientSession

# TODO - hente fra configuration
EVENT_SERVICE_URL = "http://localhost:8082/"


class RaceclassesAdapter:
    """Class representing raceclasses."""

    async def get_all_raceclasses(self) -> List:
        """Get all innstillinger function."""
        raceclasses = []
        async with ClientSession() as session:
            async with session.get(EVENT_SERVICE_URL + "raceclasses") as resp:
                logging.debug(f"get_all_raceclasses - got response {resp.status}")
                if resp.status == "200":
                    raceclasses = await resp.json()
        return raceclasses
