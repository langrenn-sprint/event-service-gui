"""Module for schedules adapter."""
import logging
from typing import List

from aiohttp import ClientSession

# TODO - hente fra configuration
EVENT_SERVICE_URL = "http://localhost:8082/"


class SchedulesAdapter:
    """Class representing schedules."""

    async def get_all_schedules(self) -> List:
        """Get all innstillinger function."""
        schedules = []
        async with ClientSession() as session:
            async with session.get(EVENT_SERVICE_URL + "schedules") as resp:
                logging.debug(f"get_all_schedules - got response {resp.status}")
                if resp.status == "200":
                    schedules = await resp.json()
        return schedules
