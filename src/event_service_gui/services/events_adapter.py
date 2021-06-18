"""Module for events adapter."""
import logging
import os
from typing import List

from aiohttp import ClientSession
from aiohttp import hdrs
import jwt
from multidict import MultiDict

# TODO - hente fra configuration
EVENT_SERVICE_URL = "http://localhost:8082"


# TODO - fikse
def token() -> str:
    """Create a valid token."""
    # secret = "secret"
    algorithm = "HS256"
    # payload = {"identity": "admin"}
    secret = os.getenv("JWT_SECRET")
    payload = {"identity": os.getenv("ADMIN_USERNAME")}
    return jwt.encode(payload, secret, algorithm)  # type: ignore


class EventsAdapter:
    """Class representing events."""

    async def get_all_events(self) -> List:
        """Get all events function."""
        events = []
        headers = {
            hdrs.AUTHORIZATION: f"Bearer {token()}",
        }

        async with ClientSession() as session:
            async with session.get(
                f"{EVENT_SERVICE_URL}/events", headers=headers
            ) as resp:
                logging.info(f"get_all_events - got response {resp.status}")
                if resp.status == "200":
                    events = await resp.json()
                logging.info(f"events - got response {events}")
        return events

    async def create_event(self, name: str) -> str:
        """Create new event function."""
        request_body = {"name": name}
        logging.info(f"create_event - {name}")
        headers = MultiDict(
            {
                hdrs.CONTENT_TYPE: "application/json",
                hdrs.AUTHORIZATION: f"Bearer {token()}",
            }
        )
        logging.info("create_event - header ok")

        async with ClientSession() as session:
            async with session.post(
                f"{EVENT_SERVICE_URL}/events", headers=headers, json=request_body
            ) as resp:
                logging.info(f"create_event - got response {resp}")
        return resp.status
