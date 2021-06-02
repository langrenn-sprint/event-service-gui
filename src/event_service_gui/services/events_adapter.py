"""Module for events adapter."""
import logging
from typing import Any, List

BASE_URL = "localhost:8082/"


class EventsAdapter:
    """Class representing events."""

    async def get_all_events(self, session: Any) -> List:
        """Get all innstillinger function."""
        events = []
        async with session:
            async with session.get(BASE_URL + "events") as resp:
                logging.debug(resp.status)
                if resp.status == "200":
                    events = await resp.json()
        return events
