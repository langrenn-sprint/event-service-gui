"""Module for raceclass results adapter."""
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


class RaceclassResultsAdapter:
    """Class representing raceclasses."""

    async def create_raceclass_results(
        self, token: str, event_id: str, request_body: dict
    ) -> int:
        """Create new raceclass results function."""
        servicename = "create_raceclass_results"
        id = ""
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )

        async with ClientSession() as session:
            async with session.post(
                f"{EVENT_SERVICE_URL}/events/{event_id}/results",
                headers=headers,
                json=request_body,
            ) as resp:
                res = resp.status
                if resp.status == 201:
                    location = resp.headers[hdrs.LOCATION]
                    id = location.split(os.path.sep)[-1]
                    logging.debug(f"{servicename} - got response {resp}, id {id}")
                elif resp.status == 401:
                    raise web.HTTPBadRequest(reason=f"401 Unathorized - {servicename}")
                else:
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )

        return res

    async def delete_raceclass_result(
        self, token: str, event_id: str, raceclass: str
    ) -> int:
        """Delete results for one raceclass function."""
        servicename = "delete_raceclass_result"
        headers = {
            hdrs.AUTHORIZATION: f"Bearer {token}",
        }

        async with ClientSession() as session:
            async with session.delete(
                f"{EVENT_SERVICE_URL}/events/{event_id}/results/{raceclass}",
                headers=headers,
            ) as resp:
                res = resp.status
                logging.debug(f"{servicename} - got response {resp}")
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
        return res

    async def get_raceclass_result(self, event_id: str, raceclass: str) -> dict:
        """Get all raceclass function."""
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
            ]
        )
        servicename = "get_raceclass_result"
        raceclass_result = {}
        async with ClientSession() as session:
            async with session.get(
                f"{EVENT_SERVICE_URL}/events/{event_id}/results/{raceclass}",
                headers=headers,
            ) as resp:
                logging.debug(f"{servicename} - got response {resp.status}")
                if resp.status == 200:
                    raceclass_result = await resp.json()
                else:
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return raceclass_result

    async def get_all_raceclass_results(self, event_id: str) -> List:
        """Get all raceclasses function."""
        raceclass_results = []
        servicename = "get_all_raceclass_results"
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
            ]
        )
        async with ClientSession() as session:
            async with session.get(
                f"{EVENT_SERVICE_URL}/events/{event_id}/raceclasses", headers=headers
            ) as resp:
                logging.debug(f"{servicename} - got response {resp.status}")
                if resp.status == 200:
                    all_raceclasses = await resp.json()
                    for raceclass in all_raceclasses:
                        logging.debug(f"Raceclasses order: {raceclass['order']}.")

                        try:
                            if raceclass["event_id"] == event_id:
                                raceclass_results.append(raceclass)
                        except Exception as e:
                            logging.error(f"Error - data quality: {e}")
                else:
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return raceclass_results
