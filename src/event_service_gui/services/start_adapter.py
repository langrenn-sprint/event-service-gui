"""Module for raceplans adapter."""
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


class StartAdapter:
    """Class representing start."""

    async def generate_startlist_for_event(self, token: str, event_id: str) -> str:
        """Generate new start_list function."""
        id = ""
        headers = MultiDict(
            {
                hdrs.AUTHORIZATION: f"Bearer {token}",
            }
        )
        request_body = {"event_id": event_id}
        async with ClientSession() as session:
            async with session.post(
                f"{RACE_SERVICE_URL}/startlists/generate-startlist-for-event",
                headers=headers,
                json=request_body,
            ) as resp:
                if resp.status == 201:
                    logging.debug(f"generate_startlist_for_event - got response {resp}")
                    location = resp.headers[hdrs.LOCATION]
                    id = location.split(os.path.sep)[-1]
                else:
                    breakpoint()
                    logging.error(
                        f"generate_startlist_for_event failed - {resp.status}"
                    )
                    raise web.HTTPBadRequest(
                        reason="Generate_startlist_for_event failed."
                    )

        return id

    # todo: update
    async def get_startliste_by_lopsklasse(
        self, token: str, event_id: str, raceclass: str
    ) -> List:
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
                logging.debug(
                    f"get_all_raceplans - got response {resp.status}, raceclass: {raceclass}"
                )
                if resp.status == 200:
                    raceplans = await resp.json()
                elif resp.status == 401:
                    raise Exception(f"Login expired: {resp}")
                else:
                    servicename = "get_startliste_by_lopsklasse"
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return raceplans

    # todo: update
    async def get_startliste_by_nr(
        self, token: str, event_id: str, start_bib: str
    ) -> List:
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
                logging.debug(
                    f"get_all_raceplans - got response {resp.status}, bib {start_bib}"
                )
                if resp.status == 200:
                    raceplans = await resp.json()
                elif resp.status == 401:
                    raise Exception(f"Login expired: {resp}")
                else:
                    servicename = "get_startliste_by_nr"
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return raceplans

    async def get_all_starts_by_event(self, token: str, event_id: str) -> List:
        """Get all starts function."""
        headers = MultiDict(
            {
                hdrs.AUTHORIZATION: f"Bearer {token}",
            }
        )
        starts = []
        async with ClientSession() as session:
            async with session.get(
                f"{RACE_SERVICE_URL}/startlists?event-id={event_id}", headers=headers
            ) as resp:
                logging.debug(f"get_all_starts - got response {resp.status}")
                if resp.status == 200:
                    starts = await resp.json()
                elif resp.status == 401:
                    raise Exception(f"Login expired: {resp}")
                else:
                    servicename = "get_all_starts"
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return starts
