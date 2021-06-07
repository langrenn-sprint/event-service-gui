"""Module for events adapter."""
import logging
from typing import List

from aiohttp import ClientSession

# TODO - hente fra configuration
EVENT_SERVICE_URL = "http://localhost:8082/"


class EventsAdapter:
    """Class representing events."""

    async def get_all_events(self) -> List:
        """Get all innstillinger function."""
        events = []
        async with ClientSession() as session:
            async with session.get(EVENT_SERVICE_URL + "events") as resp:
                logging.debug(resp.status)
                if resp.status == "200":
                    events = await resp.json()
        return events
