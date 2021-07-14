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

    async def get_all_ageclasses(self) -> List:
        """Get all ageclasses function."""
        ageclasses = []
        async with ClientSession() as session:
            async with session.get(f"{EVENT_SERVICE_URL}/raceclasses") as resp:
                logging.debug(f"get_all_ageclasses - got response {resp.status}")
                if resp.status == "200":
                    ageclasses = await resp.json()
                else:
                    logging.error(f"Error in raceclasses: {resp}")
        return ageclasses

    async def get_all_raceclasses(self) -> List:
        """Get all innstillinger function."""
        raceclasses = []
        async with ClientSession() as session:
            async with session.get(f"{EVENT_SERVICE_URL}/raceclasses") as resp:
                logging.debug(f"get_all_raceclasses - got response {resp.status}")
                if resp.status == "200":
                    raceclasses = await resp.json()
                else:
                    logging.error(f"Error in raceclasses: {resp}")
        return raceclasses
