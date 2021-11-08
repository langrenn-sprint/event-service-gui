"""Module for time events adapter."""
import copy
import logging
import os
from typing import List

from aiohttp import ClientSession
from aiohttp import hdrs
from aiohttp import web
from multidict import MultiDict

RACE_HOST_SERVER = os.getenv("RACE_HOST_SERVER", "localhost")
RACE_HOST_PORT = os.getenv("RACE_HOST_PORT", "8088")
RACE_SERVICE_URL = f"http://{RACE_HOST_SERVER}:{RACE_HOST_PORT}"


class TimeEventsAdapter:
    """Class representing time_events."""

    async def create_time_event(self, token: str, time_event: dict) -> str:
        """Create new time_event function."""
        id = ""
        headers = MultiDict(
            {
                hdrs.CONTENT_TYPE: "application/json",
                hdrs.AUTHORIZATION: f"Bearer {token}",
            }
        )
        request_body = copy.deepcopy(time_event)

        async with ClientSession() as session:
            async with session.post(
                f"{RACE_SERVICE_URL}/time-events", headers=headers, json=request_body
            ) as resp:
                if resp.status == 201:
                    logging.debug(f"time-event - got response {resp}")
                    location = resp.headers[hdrs.LOCATION]
                    id = location.split(os.path.sep)[-1]
                else:
                    logging.error(f"create_time_event failed - {resp.status}")
                    raise web.HTTPBadRequest(reason="Create time_event failed.")

        return id

    async def delete_time_event(self, token: str, id: str) -> str:
        """Delete time_event function."""
        headers = MultiDict(
            {
                hdrs.CONTENT_TYPE: "application/json",
                hdrs.AUTHORIZATION: f"Bearer {token}",
            }
        )
        url = f"{RACE_SERVICE_URL}/time-events/{id}"
        async with ClientSession() as session:
            async with session.delete(url, headers=headers) as response:
                pass
            logging.debug(f"Delete time_event: {id} - res {response.status}")
            if response.status == 204:
                logging.debug(f"result - got response {response}")
            else:
                logging.error(
                    f"delete_time_event failed - {response.status}, {response}"
                )
                raise web.HTTPBadRequest(
                    reason=f"Delete time_event failed {response.status}."
                )
        return str(response.status)

    async def update_time_event(self, token: str, id: str, request_body: dict) -> str:
        """Update time_event function."""
        headers = MultiDict(
            {
                hdrs.CONTENT_TYPE: "application/json",
                hdrs.AUTHORIZATION: f"Bearer {token}",
            }
        )

        async with ClientSession() as session:
            async with session.put(
                f"{RACE_SERVICE_URL}/time-events/{id}",
                headers=headers,
                json=request_body,
            ) as resp:
                if resp.status == 204:
                    logging.debug(f"update time_event - got response {resp}")
                else:
                    logging.error(f"update_time_event failed - {resp.status}")
                    raise web.HTTPBadRequest(
                        reason=f"Update time_event failed - {resp.status}."
                    )
            logging.debug(f"Updated time_event: {id} - res {resp.status}")
        return str(resp.status)

    async def get_time_event_by_id(self, token: str, id: str) -> dict:
        """Get all time_events - lap time or heat place function."""
        headers = MultiDict(
            {
                hdrs.AUTHORIZATION: f"Bearer {token}",
            }
        )
        time_event = {}
        async with ClientSession() as session:
            async with session.get(
                f"{RACE_SERVICE_URL}/time-events/{id}", headers=headers
            ) as resp:
                logging.debug(f"get_time_event_by_id - got response {resp.status}")
                if resp.status == 200:
                    time_event = await resp.json()
                elif resp.status == 401:
                    raise Exception(f"Login expired: {resp}")
                else:
                    servicename = "get_time_event_by_id"
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return time_event

    async def get_time_events_by_event_id(self, token: str, event_id: str) -> List:
        """Get all time_events - lap time or heat place function."""
        headers = MultiDict(
            {
                hdrs.AUTHORIZATION: f"Bearer {token}",
            }
        )
        time_events = []
        async with ClientSession() as session:
            async with session.get(
                f"{RACE_SERVICE_URL}/time-events?event-id={event_id}", headers=headers
            ) as resp:
                logging.debug(
                    f"get_all_time_events_by_event_id - got response {resp.status}"
                )
                if resp.status == 200:
                    time_events = await resp.json()
                elif resp.status == 401:
                    raise Exception(f"Login expired: {resp}")
                else:
                    servicename = "get_all_time_events"
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return time_events
