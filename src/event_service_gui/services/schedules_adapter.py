"""Module for schedules adapter."""
import logging
import os
from typing import List

from aiohttp import ClientSession

EVENT_SERVICE_HOST = os.getenv("EVENT_SERVICE_HOST", "localhost")
EVENT_SERVICE_PORT = os.getenv("EVENT_SERVICE_PORT", "8082")
EVENT_SERVICE_URL = f"http://{EVENT_SERVICE_HOST}:{EVENT_SERVICE_PORT}"


class SchedulesAdapter:
    """Class representing schedules."""

    async def get_all_schedules(self) -> List:
        """Get all innstillinger function."""
        schedules = []
        async with ClientSession() as session:
            async with session.get(f"{EVENT_SERVICE_URL}/schedules") as resp:
                logging.debug(f"get_all_schedules - got response {resp.status}")
                if resp.status == "200":
                    schedules = await resp.json()
        return schedules
