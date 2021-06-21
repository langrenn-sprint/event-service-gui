"""Module for events adapter."""
import logging
from typing import List

from aiohttp import ClientSession
from aiohttp import hdrs
from multidict import MultiDict

# TODO - hente fra configuration
EVENT_SERVICE_URL = "http://localhost:8082"


class EventsAdapter:
    """Class representing events."""

    async def get_all_events(self) -> List:
        """Get all events function."""
        events = []

        async with ClientSession() as session:
            async with session.get(f"{EVENT_SERVICE_URL}/events") as resp:
                logging.info(f"get_all_events - got response {resp.status}")
                if resp.status == "200":
                    events = await resp.json()
                logging.info(f"events - got response {events}")
        return events

    async def create_event(self, token: str, name: str) -> str:
        """Create new event function."""
        request_body = {"name": name}
        headers = MultiDict(
            {
                hdrs.CONTENT_TYPE: "application/json",
                hdrs.AUTHORIZATION: f"Bearer {token}",
            }
        )

        async with ClientSession() as session:
            async with session.post(
                f"{EVENT_SERVICE_URL}/events", headers=headers, json=request_body
            ) as resp:
                logging.debug(f"create_event - got response {resp}")
        logging.info(f"create_event - {resp.status} {name}")
        return resp.status
