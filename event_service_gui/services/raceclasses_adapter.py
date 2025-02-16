"""Module for raceclasses adapter."""

import logging
import os
from typing import List
import urllib.parse

from aiohttp import ClientSession
from aiohttp import hdrs
from aiohttp import web
from multidict import MultiDict

EVENTS_HOST_SERVER = os.getenv("EVENTS_HOST_SERVER", "localhost")
EVENTS_HOST_PORT = os.getenv("EVENTS_HOST_PORT", "8082")
EVENT_SERVICE_URL = f"http://{EVENTS_HOST_SERVER}:{EVENTS_HOST_PORT}"


class RaceclassesAdapter:
    """Class representing raceclasses."""

    async def create_raceclass(
        self, token: str, event_id: str, request_body: dict
    ) -> str:
        """Create new raceclass function."""
        servicename = "create_raceclass"
        id = ""
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )

        async with ClientSession() as session:
            async with session.post(
                f"{EVENT_SERVICE_URL}/events/{event_id}/raceclasses",
                headers=headers,
                json=request_body,
            ) as resp:
                if resp.status == 201:
                    logging.debug(f"create raceclass - got response {resp}")
                    location = resp.headers[hdrs.LOCATION]
                    id = location.split(os.path.sep)[-1]
                elif resp.status == 401:
                    raise web.HTTPBadRequest(reason=f"401 Unathorized - {servicename}")
                else:
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )

        return id

    async def delete_all_raceclasses(self, token: str, event_id: str) -> str:
        """Delete all raceclasses in one event function."""
        servicename = "delete_all_raceclasses"
        headers = {
            hdrs.AUTHORIZATION: f"Bearer {token}",
        }

        async with ClientSession() as session:
            async with session.delete(
                f"{EVENT_SERVICE_URL}/events/{event_id}/raceclasses",
                headers=headers,
            ) as resp:
                res = resp.status
                logging.debug(f"delete all result - got response {resp}")
                if res == 204:
                    pass
                elif resp.status == 401:
                    raise web.HTTPBadRequest(reason=f"401 Unathorized - {servicename}")
                else:
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return str(res)

    async def delete_raceclass(
        self, token: str, event_id: str, raceclass_id: str
    ) -> str:
        """Delete one raceclass function."""
        servicename = "delete_raceclass"
        headers = {
            hdrs.AUTHORIZATION: f"Bearer {token}",
        }

        async with ClientSession() as session:
            async with session.delete(
                f"{EVENT_SERVICE_URL}/events/{event_id}/raceclasses/{raceclass_id}",
                headers=headers,
            ) as resp:
                res = resp.status
                logging.debug(f"delete result - got response {resp}")
                if res == 204:
                    pass
                elif resp.status == 401:
                    raise web.HTTPBadRequest(reason=f"401 Unathorized - {servicename}")
                else:
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return str(res)

    async def get_raceclass(self, token: str, event_id: str, raceclass_id: str) -> dict:
        """Get all raceclass function."""
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        raceclass = {}
        async with ClientSession() as session:
            async with session.get(
                f"{EVENT_SERVICE_URL}/events/{event_id}/raceclasses/{raceclass_id}",
                headers=headers,
            ) as resp:
                logging.debug(f"get_raceclass - got response {resp.status}")
                if resp.status == 200:
                    raceclass = await resp.json()
                else:
                    servicename = "get_raceclass"
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return raceclass

    async def get_raceclass_by_ageclass(
        self, token: str, event_id: str, ageclass: str
    ) -> dict:
        """Get all raceclass function."""
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        raceclass = {}
        ageclass_url = urllib.parse.quote(ageclass, safe="")
        async with ClientSession() as session:
            async with session.get(
                f"{EVENT_SERVICE_URL}/events/{event_id}/raceclasses?ageclass-name={ageclass_url}",
                headers=headers,
            ) as resp:
                logging.debug(f"get_raceclass_by_ageclass - got response {resp.status}")
                if resp.status == 200:
                    raceclass = await resp.json()
                else:
                    servicename = "get_raceclass_by_ageclass"
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return raceclass[0]

    async def get_raceclasses(self, token: str, event_id: str) -> List:
        """Get all raceclasses function."""
        raceclasses = []
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        async with ClientSession() as session:
            async with session.get(
                f"{EVENT_SERVICE_URL}/events/{event_id}/raceclasses", headers=headers
            ) as resp:
                logging.debug(f"get_raceclasses - got response {resp.status}")
                if resp.status == 200:
                    all_raceclasses = await resp.json()
                    for raceclass in all_raceclasses:
                        logging.debug(f"Raceclasses order: {raceclass['order']}.")

                        try:
                            if raceclass["event_id"] == event_id:
                                raceclasses.append(raceclass)
                        except Exception as e:
                            logging.error(f"Error - data quality: {e}")
                else:
                    servicename = "get_raceclasses"
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return raceclasses

    async def update_raceclass(
        self, token: str, event_id: str, id: str, new_data: dict
    ) -> int:
        """Update klasser function."""
        servicename = "update_raceclass"
        returncode = 201
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        async with ClientSession() as session:
            async with session.put(
                f"{EVENT_SERVICE_URL}/events/{event_id}/raceclasses/{id}",
                headers=headers,
                json=new_data,
            ) as resp:
                returncode = resp.status
                logging.debug(f"update_raceclass - got response {resp.status}")
                if resp.status == 204:
                    pass
                elif resp.status == 401:
                    raise web.HTTPBadRequest(reason=f"401 Unathorized - {servicename}")
                else:
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )

        return returncode
