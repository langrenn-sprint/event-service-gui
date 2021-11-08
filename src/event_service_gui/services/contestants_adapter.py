"""Module for contestants adapter."""
import copy
import logging
import os
from typing import List

from aiohttp import ClientSession
from aiohttp import hdrs, web
from multidict import MultiDict

EVENTS_HOST_SERVER = os.getenv("EVENTS_HOST_SERVER", "localhost")
EVENTS_HOST_PORT = os.getenv("EVENTS_HOST_PORT", "8082")
EVENT_SERVICE_URL = f"http://{EVENTS_HOST_SERVER}:{EVENTS_HOST_PORT}"


class ContestantsAdapter:
    """Class representing contestants."""

    async def assign_bibs(self, token: str, event_id: str) -> str:
        """Generate bibs based upon registrations."""
        headers = MultiDict(
            {
                hdrs.AUTHORIZATION: f"Bearer {token}",
            }
        )
        url = f"{EVENT_SERVICE_URL}/events/{event_id}/contestants/assign-bibs"
        async with ClientSession() as session:
            async with session.post(url, headers=headers) as resp:
                res = resp.status
                logging.debug(f"assign_bibs result - got response {resp}")
                if res == 201:
                    pass
                else:
                    servicename = "assign_bibs"
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
            information = "Startnummer tildelt."
        return information

    async def create_contestant(
        self, token: str, event_id: str, request_body: dict
    ) -> str:
        """Create new contestant function."""
        id = ""
        headers = MultiDict(
            {
                hdrs.CONTENT_TYPE: "application/json",
                hdrs.AUTHORIZATION: f"Bearer {token}",
            }
        )

        async with ClientSession() as session:
            async with session.post(
                f"{EVENT_SERVICE_URL}/events/{event_id}/contestants",
                headers=headers,
                json=request_body,
            ) as resp:
                if resp.status == 201:
                    logging.debug(f"result - got response {resp}")
                    location = resp.headers[hdrs.LOCATION]
                    id = location.split(os.path.sep)[-1]
                else:
                    servicename = "create_contestant"
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return id

    async def create_contestants(self, token: str, event_id: str, inputfile) -> str:
        """Create new contestants function."""
        headers = {
            hdrs.CONTENT_TYPE: "text/csv",
            hdrs.AUTHORIZATION: f"Bearer {token}",
        }
        logging.debug(f"Create contestants - got file {inputfile}")
        async with ClientSession() as session:
            async with session.post(
                f"{EVENT_SERVICE_URL}/events/{event_id}/contestants",
                headers=headers,
                data=inputfile,
            ) as resp:
                res = resp.status
                logging.info(f"result - got response {res} - {resp}")
                if res == 200:
                    res = await resp.json()
                else:
                    servicename = "create_contestants"
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return str(res)

    async def delete_all_contestants(self, token: str, event_id: str) -> str:
        """Delete all contestants in one event function."""
        headers = {
            hdrs.AUTHORIZATION: f"Bearer {token}",
        }

        async with ClientSession() as session:
            async with session.delete(
                f"{EVENT_SERVICE_URL}/events/{event_id}/contestants",
                headers=headers,
            ) as resp:
                res = resp.status
                logging.debug(f"delete all result - got response {resp}")
                if res == 204:
                    pass
                else:
                    servicename = "delete_all_contestants"
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return str(res)

    async def delete_contestant(
        self, token: str, event_id: str, contestant_id: str
    ) -> str:
        """Delete one contestant function."""
        headers = {
            hdrs.AUTHORIZATION: f"Bearer {token}",
        }

        async with ClientSession() as session:
            async with session.delete(
                f"{EVENT_SERVICE_URL}/events/{event_id}/contestants/{contestant_id}",
                headers=headers,
            ) as resp:
                res = resp.status
                logging.debug(f"delete result - got response {resp}")
                if res == 204:
                    pass
                else:
                    servicename = "delete_contestant"
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return str(res)

    async def get_all_contestants(
        self, token: str, event_id: str, ageclass_name: str
    ) -> List:
        """Get all contestants / by class (optional) function."""
        headers = MultiDict(
            {
                hdrs.CONTENT_TYPE: "application/json",
                hdrs.AUTHORIZATION: f"Bearer {token}",
            }
        )
        contestants = []
        async with ClientSession() as session:
            async with session.get(
                f"{EVENT_SERVICE_URL}/events/{event_id}/contestants", headers=headers
            ) as resp:
                logging.debug(f"get_all_contestants - got response {resp.status}")
                if resp.status == 200:
                    contestants = await resp.json()
                else:
                    servicename = "get_all_contestants"
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )

        # TODO: Bør flyttes til backend
        if ageclass_name != "":
            tmp_contestants = []
            for x in contestants:
                if x["ageclass"] == ageclass_name:
                    tmp_contestants.append(x)
            contestants = tmp_contestants
        return contestants

    async def get_contestants_by_raceclass(
        self, token: str, event_id: str, raceclass: str
    ) -> List:
        """Get all contestants by raceclass function."""
        headers = MultiDict(
            {
                hdrs.CONTENT_TYPE: "application/json",
                hdrs.AUTHORIZATION: f"Bearer {token}",
            }
        )
        contestants = []
        async with ClientSession() as session:
            async with session.get(
                f"{EVENT_SERVICE_URL}/events/{event_id}/contestants?raceclass={raceclass}",
                headers=headers,
            ) as resp:
                logging.debug(
                    f"get_contestants_by_raceclass - got response {resp.status}"
                )
                if resp.status == 200:
                    contestants = await resp.json()
                else:
                    servicename = "get_contestants_by_raceclass"
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return contestants

    async def get_contestant(
        self, token: str, event_id: str, contestant_id: str
    ) -> dict:
        """Get all contestant function."""
        headers = MultiDict(
            {
                hdrs.CONTENT_TYPE: "application/json",
                hdrs.AUTHORIZATION: f"Bearer {token}",
            }
        )
        contestant = {}
        async with ClientSession() as session:
            async with session.get(
                f"{EVENT_SERVICE_URL}/events/{event_id}/contestants/{contestant_id}",
                headers=headers,
            ) as resp:
                logging.debug(f"get_contestant - got response {resp.status}")
                if resp.status == 200:
                    contestant = await resp.json()
                else:
                    servicename = "get_contestant"
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return contestant

    async def update_contestant(
        self, token: str, event_id: str, contestant: dict
    ) -> str:
        """Create new contestants function."""
        request_body = copy.deepcopy(contestant)
        logging.debug(f"update_contestants, got request_body {request_body}")

        url = f"{EVENT_SERVICE_URL}/events/{event_id}/contestants/{contestant['id']}"
        headers = MultiDict(
            {
                hdrs.CONTENT_TYPE: "application/json",
                hdrs.AUTHORIZATION: f"Bearer {token}",
            }
        )

        async with ClientSession() as session:
            async with session.put(url, headers=headers, json=request_body) as resp:
                res = resp.status
                if res == 204:
                    logging.debug(f"result - got response {resp}")
                else:
                    servicename = "update_contestant"
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )

        return str(resp.status)
