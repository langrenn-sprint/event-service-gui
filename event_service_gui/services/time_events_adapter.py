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

    async def create_time_event(self, token: str, time_event: dict) -> dict:
        """Create new time_event function, return new time event."""
        servicename = "create_time_event"
        new_time_event = {}
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )

        request_body = copy.deepcopy(time_event)

        async with ClientSession() as session:
            async with session.post(
                f"{RACE_SERVICE_URL}/time-events", headers=headers, json=request_body
            ) as resp:
                if resp.status == 200:
                    new_time_event = await resp.json()
                    logging.debug(f"time-event - got response {resp}, {new_time_event}")
                elif resp.status == 400:
                    functional_error = await resp.json()
                    raise web.HTTPBadRequest(reason=f"400 - {functional_error['detail']}")
                elif resp.status == 401:
                    raise web.HTTPBadRequest(reason=f"401 Unathorized - {servicename}")
                else:
                    logging.error(
                        f"create_time_event failed - {resp.status}, {resp} input data: {time_event}"
                    )
                    raise web.HTTPBadRequest(
                        reason=f"Create time_event failed Error: {resp}. Input data: {time_event}"
                    )
        return new_time_event

    async def delete_time_event(self, token: str, id: str) -> int:
        """Delete time_event function."""
        servicename = "delete_time_event"
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        url = f"{RACE_SERVICE_URL}/time-events/{id}"
        async with ClientSession() as session:
            async with session.delete(url, headers=headers) as resp:
                pass
            logging.debug(f"Delete time_event: {id} - res {resp.status}")
            if resp.status == 204:
                logging.debug(f"result - got response {resp}")
            elif resp.status == 401:
                raise web.HTTPBadRequest(reason=f"401 Unathorized - {servicename}")
            else:
                logging.error(f"delete_time_event failed - {resp.status}, {resp}")
                raise web.HTTPBadRequest(
                    reason=f"Delete time_event failed {resp.status}."
                )
        return resp.status

    async def update_time_event(self, token: str, id: str, time_event: dict) -> int:
        """Update time_event function."""
        servicename = "update_time_event"
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )

        async with ClientSession() as session:
            async with session.put(
                f"{RACE_SERVICE_URL}/time-events/{id}",
                headers=headers,
                json=time_event,
            ) as resp:
                if resp.status == 204:
                    logging.debug(f"update time_event - got response {resp}")
                elif resp.status == 401:
                    raise web.HTTPBadRequest(reason=f"401 Unathorized - {servicename}")
                else:
                    logging.error(
                        f"update_time_event failed - {resp.status} input data: {time_event}"
                    )
                    raise web.HTTPBadRequest(
                        reason=f"Update time_event failed - {resp.status} input data: {time_event}."
                    )
            logging.debug(f"Updated time_event: {id} - res {resp.status}")
        return resp.status

    async def get_time_event_by_id(self, token: str, id: str) -> dict:
        """Get one time_event - lap time or heat place function."""
        headers = MultiDict(
            [
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
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
            [
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        time_events = []
        async with ClientSession() as session:
            async with session.get(
                f"{RACE_SERVICE_URL}/time-events?eventId={event_id}", headers=headers
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

    async def get_time_events_by_event_id_and_timing_point(
        self, token: str, event_id: str, timing_point: str
    ) -> List:
        """Get all time_events - lap time or heat place function."""
        headers = MultiDict(
            [
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        time_events = []
        async with ClientSession() as session:
            async with session.get(
                f"{RACE_SERVICE_URL}/time-events?eventId={event_id}&timingPoint={timing_point}",
                headers=headers,
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

    async def get_time_events_by_race_id(self, token: str, race_id: str) -> List:
        """Get time_events - lap time or heat place function."""
        headers = MultiDict(
            [
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        time_events = []
        async with ClientSession() as session:
            async with session.get(
                f"{RACE_SERVICE_URL}/time-events?raceId={race_id}", headers=headers
            ) as resp:
                logging.debug(
                    f"get_time_events_by_race_id - got response {resp.status}"
                )
                if resp.status == 200:
                    time_events = await resp.json()
                elif resp.status == 401:
                    raise Exception(f"Login expired: {resp}")
                else:
                    servicename = "get_time_events_by_race_id"
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return time_events
