"""Module for raceclass results adapter."""

import logging
import os
import random
from typing import List
import urllib.parse

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
        raceclass_url = urllib.parse.quote(raceclass, safe="")

        async with ClientSession() as session:
            async with session.delete(
                f"{EVENT_SERVICE_URL}/events/{event_id}/results/{raceclass_url}",
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
        """Get all raceclass result function."""
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
            ]
        )
        servicename = "get_raceclass_result"
        raceclass_result = {}
        raceclass_url = urllib.parse.quote(raceclass, safe="")
        async with ClientSession() as session:
            async with session.get(
                f"{EVENT_SERVICE_URL}/events/{event_id}/results/{raceclass_url}",
                headers=headers,
            ) as resp:
                logging.debug(f"{servicename} - got response {resp.status}")
                if resp.status == 200:
                    raceclass_result = await resp.json()
                elif resp.status == 404:
                    # No results yet for this raceclass
                    raise web.HTTPBadRequest(
                        reason=f"Resultater er ikke klare for {raceclass_url}."
                    )
                else:
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return raceclass_result

    async def get_raceclass_result_shuffeled(
        self, event_id: str, raceclass: str, i_keep: int
    ) -> dict:
        """Get all raceclass result function. Shuffeled, except the n first."""
        raceclass_result = await self.get_raceclass_result(event_id, raceclass)
        if raceclass_result and raceclass_result.get(
            "ranking_sequence"
        ):  # Check if ranking_sequence exists
            raceclass_result["ranking_sequence"] = shuffle_list_keep_first(
                raceclass_result["ranking_sequence"], i_keep
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
                f"{EVENT_SERVICE_URL}/events/{event_id}/results", headers=headers
            ) as resp:
                logging.debug(f"{servicename} - got response {resp.status}")
                if resp.status == 200:
                    raceclass_results = await resp.json()
                else:
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return raceclass_results


def shuffle_list_keep_first(my_list: list, n: int) -> list:
    """Shuffles a list, keeping the first n elements fixed."""
    if len(my_list) <= n:  # Nothing to shuffle if list is shorter than n
        return my_list

    head = my_list[:n]
    tail = my_list[n:]
    random.shuffle(tail)  # Shuffle only the tail portion
    return head + tail
