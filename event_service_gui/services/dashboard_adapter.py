"""Module for events adapter."""
import copy
import logging
import os
from typing import List

from aiohttp import ClientSession
from aiohttp import hdrs
from aiohttp import web
from multidict import MultiDict

EVENTS_HOST_SERVER = os.getenv("EVENTS_HOST_SERVER", "localhost")
EVENTS_HOST_PORT = os.getenv("EVENTS_HOST_PORT", "8082")
EVENT_SERVICE_URL = f"http://{EVENTS_HOST_SERVER}:{EVENTS_HOST_PORT}"


class DashboardAdapter:
    """Class representing events."""

    async def get_all_events(self, token: str) -> List:
        """Get all events function."""
        events = []
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )

        async with ClientSession() as session:
            async with session.get(
                f"{EVENT_SERVICE_URL}/events", headers=headers
            ) as resp:
                logging.debug(f"get_all_events - got response {resp.status}")
                if resp.status == 200:
                    events = await resp.json()
                    logging.debug(f"events - got response {events}")
                elif resp.status == 401:
                    logging.info("TODO Performing new login")
                    # Perform login
                else:
                    logging.error(f"Error {resp.status} getting events: {resp} ")
        return events

    async def get_event(self, token: str, id: str) -> dict:
        """Get event function."""
        event = {}
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )

        async with ClientSession() as session:
            async with session.get(
                f"{EVENT_SERVICE_URL}/events/{id}", headers=headers
            ) as resp:
                logging.debug(f"get_event {id} - got response {resp.status}")
                if resp.status == 200:
                    event = await resp.json()
                    logging.debug(f"event - got response {event}")
                else:
                    logging.error(f"Error {resp.status} getting events: {resp} ")
        return event

    async def create_event(self, token: str, event: dict) -> str:
        """Create new event function."""
        id = ""
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        request_body = copy.deepcopy(event)

        async with ClientSession() as session:
            async with session.post(
                f"{EVENT_SERVICE_URL}/events", headers=headers, json=request_body
            ) as resp:
                if resp.status == 201:
                    logging.debug(f"result - got response {resp}")
                    location = resp.headers[hdrs.LOCATION]
                    id = location.split(os.path.sep)[-1]
                else:
                    logging.error(f"create_event failed - {resp.status}")
                    raise web.HTTPBadRequest(reason="Create event failed.")

        return id

    async def delete_event(self, token: str, id: str) -> str:
        """Delete event function."""
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        url = f"{EVENT_SERVICE_URL}/events/{id}"
        async with ClientSession() as session:
            async with session.delete(url, headers=headers) as response:
                pass
            logging.debug(f"Delete event: {id} - res {response.status}")
            if response.status == 204:
                logging.debug(f"result - got response {response}")
            else:
                logging.error(f"delete_event failed - {response.status}, {response}")
                raise web.HTTPBadRequest(reason="Delete event failed.")
        return str(response.status)

    async def update_event(self, token: str, id: str, request_body: dict) -> str:
        """Update event function."""
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )

        async with ClientSession() as session:
            async with session.put(
                f"{EVENT_SERVICE_URL}/events/{id}", headers=headers, json=request_body
            ) as resp:
                if resp.status == 204:
                    logging.debug(f"update event - got response {resp}")
                else:
                    logging.error(f"update_event failed - {resp.status}")
                    raise web.HTTPBadRequest(reason="Update event failed.")
            logging.debug(f"Updated event: {id} - res {resp.status}")
        return str(resp.status)
