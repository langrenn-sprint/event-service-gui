"""Module for raceplans adapter."""
import logging
import os
from typing import List

from aiohttp import ClientSession
from aiohttp import hdrs
from aiohttp import web
from multidict import MultiDict

RACE_SERVICE_HOST = os.getenv("RACE_SERVICE_HOST", "localhost")
RACE_SERVICE_PORT = os.getenv("RACE_SERVICE_PORT", "8088")
RACE_SERVICE_URL = f"http://{RACE_SERVICE_HOST}:{RACE_SERVICE_PORT}"


class RaceplansAdapter:
    """Class representing raceplans."""

    async def delete_raceplan(self, token: str, id: str) -> str:
        """Delete all raceplans in one event function."""
        headers = {
            hdrs.AUTHORIZATION: f"Bearer {token}",
        }
        async with ClientSession() as session:
            async with session.delete(
                f"{RACE_SERVICE_URL}/raceplans/{id}",
                headers=headers,
            ) as resp:
                res = resp.status
                logging.debug(f"delete raceplan result - got response {resp}")
                if res == 204:
                    pass
                else:
                    servicename = "delete_raceplan"
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return str(res)

    async def generate_raceplans(self, token: str, event_id: str) -> str:
        """Generate classes based upon registered contestants."""
        headers = MultiDict(
            {
                hdrs.AUTHORIZATION: f"Bearer {token}",
            }
        )
        request_body = {"event_id": event_id}
        url = f"{RACE_SERVICE_URL}/raceplans/generate-raceplan-for-event"
        async with ClientSession() as session:
            async with session.post(url, headers=headers, json=request_body) as resp:
                res = resp.status
                logging.debug(f"generate_raceplan result - got response {resp}")
                if res == 201:
                    pass
                else:
                    servicename = "generate_raceplan"
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return res

    async def get_all_raceplans(self, token: str, event_id: str) -> List:
        """Get all raceplans function."""
        headers = MultiDict(
            {
                hdrs.AUTHORIZATION: f"Bearer {token}",
            }
        )
        raceplans = []
        async with ClientSession() as session:
            async with session.get(
                f"{RACE_SERVICE_URL}/raceplans", headers=headers
            ) as resp:
                logging.debug(f"get_all_raceplans - got response {resp.status}")
                if resp.status == 200:
                    raceplans = await resp.json()
                elif resp.status == 401:
                    raise Exception(f"Login expired: {resp}")
                else:
                    servicename = "get_all_raceplans"
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return raceplans

    async def get_raceplan(self, token: str, id: str) -> dict:
        """Get event function."""
        raceplan = {}
        headers = MultiDict(
            {
                hdrs.CONTENT_TYPE: "application/json",
                hdrs.AUTHORIZATION: f"Bearer {token}",
            }
        )

        async with ClientSession() as session:
            async with session.get(
                f"{RACE_SERVICE_URL}/raceplans/{id}", headers=headers
            ) as resp:
                logging.debug(f"get_raceplan {id} - got response {resp.status}")
                if resp.status == 200:
                    raceplan = await resp.json()
                    logging.debug(f"get_raceplan - got response {raceplan}")
                elif resp.status == 401:
                    raise Exception(f"Login expired: {resp}")
                else:
                    servicename = "get_raceplan"
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return raceplan
