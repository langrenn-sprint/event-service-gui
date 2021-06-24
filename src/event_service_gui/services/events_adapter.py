"""Module for events adapter."""
import logging
import os
from typing import List

from aiohttp import ClientSession
from aiohttp import hdrs
from aiohttp import web
from multidict import MultiDict

# TODO - hente fra configuration
EVENT_SERVICE_URL = "http://localhost:8082"


class EventsAdapter:
    """Class representing events."""

    async def get_all_events(self, token: str) -> List:
        """Get all events function."""
        events = []
        headers = MultiDict(
            {
                hdrs.CONTENT_TYPE: "application/json",
                hdrs.AUTHORIZATION: f"Bearer {token}",
            }
        )

        async with ClientSession() as session:
            async with session.get(
                f"{EVENT_SERVICE_URL}/events", headers=headers
            ) as resp:
                logging.info(f"get_all_events - got response {resp.status}")
                if resp.status == "200":
                    events = await resp.json()
                logging.info(f"events - got response {events}")
        return events

    async def create_event(self, token: str, name: str) -> str:
        """Create new event function."""
        request_body = {"name": name}
        id = ""
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
                if resp.status == 201:
                    logging.debug(f"result - got response {resp}")
                    location = resp.headers[hdrs.LOCATION]
                    id = location.split(os.path.sep)[-1]
                else:
                    logging.error(f"create_event failed - {resp.status} {name}")
                    raise web.HTTPBadRequest(reason="Create event failed.")

        return id
