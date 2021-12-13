"""Module for start adapter."""
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
        informasjon = ""
        headers = MultiDict(
            [
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
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
                    informasjon = f"Suksess! Opprettet startlister. Id: {id}"
                else:
                    logging.error(
                        f"generate_startlist_for_event failed - {resp.status}"
                    )
                    raise web.HTTPBadRequest(
                        reason="Generate_startlist_for_event failed."
                    )

        return informasjon

    async def delete_start_entry(
        self, token: str, race_id: str, start_entry_id: str
    ) -> str:
        """Delete one start_entry function."""
        headers = {
            hdrs.AUTHORIZATION: f"Bearer {token}",
        }

        async with ClientSession() as session:
            async with session.delete(
                f"{RACE_SERVICE_URL}/races/{race_id}/start-entries/{start_entry_id}",
                headers=headers,
            ) as resp:
                res = resp.status
                logging.debug(f"delete result - got response {resp}")
                if res == 204:
                    pass
                else:
                    servicename = "delete_start_entry"
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return str(res)

    async def get_start_entries_by_race_id(self, token: str, race_id: str) -> list:
        """Get one start_entry - lap time or heat place function."""
        headers = MultiDict(
            [
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        start_entries = []
        async with ClientSession() as session:
            async with session.get(
                f"{RACE_SERVICE_URL}/races/{race_id}/start-entries",
                headers=headers,
            ) as resp:
                logging.debug(
                    f"get_start_entries_by_race_id - got response {resp.status}"
                )
                if resp.status == 200:
                    start_entries = await resp.json()
                elif resp.status == 401:
                    raise Exception(f"Login expired: {resp}")
                else:
                    servicename = "get_start_entries_by_race_id"
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return start_entries

    async def get_start_entry_by_id(
        self, token: str, race_id: str, start_id: str
    ) -> dict:
        """Get one start_entry - lap time or heat place function."""
        headers = MultiDict(
            [
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        start_entry = {}
        async with ClientSession() as session:
            async with session.get(
                f"{RACE_SERVICE_URL}/races/{race_id}/start-entries/{start_id}",
                headers=headers,
            ) as resp:
                logging.debug(f"get_start_entry_by_id - got response {resp.status}")
                if resp.status == 200:
                    start_entry = await resp.json()
                elif resp.status == 401:
                    raise Exception(f"Login expired: {resp}")
                else:
                    servicename = "get_start_entry_by_id"
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return start_entry

    # todo: update
    async def get_startliste_by_lopsklasse(
        self, token: str, event_id: str, raceclass: str
    ) -> List:
        """Get all raceplans function."""
        headers = MultiDict(
            [
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
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
    async def get_startlist_by_bib(
        self, token: str, event_id: str, start_bib: str
    ) -> List:
        """Get all raceplans function."""
        headers = MultiDict(
            [
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
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
            [
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        starts = []
        async with ClientSession() as session:
            async with session.get(
                f"{RACE_SERVICE_URL}/startlists?eventId={event_id}", headers=headers
            ) as resp:
                logging.debug(f"get_all_starts_by_event - got response {resp.status}")
                if resp.status == 200:
                    starts = await resp.json()
                elif resp.status == 401:
                    raise Exception(f"Login expired: {resp}")
                else:
                    servicename = "get_all_starts_by_event"
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return starts

    async def create_start_entry(self, token: str, new_start: dict) -> int:
        """Add one start to the start_list."""
        headers = {
            hdrs.CONTENT_TYPE: "application/json",
            hdrs.AUTHORIZATION: f"Bearer {token}",
        }
        logging.debug(f"New start: {new_start}")
        async with ClientSession() as session:
            async with session.post(
                f"{RACE_SERVICE_URL}/races/{new_start['race_id']}/start-entries",
                headers=headers,
                json=new_start,
            ) as resp:
                logging.debug(f"create_start_entry - got response {resp.status}")
                if resp.status == 201:
                    pass
                elif resp.status == 401:
                    raise Exception(f"Login expired: {resp}")
                else:
                    servicename = "create_start_entry"
                    body = await resp.json()
                    logging.error(
                        f"{servicename} failed - {resp.status} - {body} {new_start}"
                    )
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return resp.status

    async def update_start_entry(self, token: str, id: str, new_start: dict) -> int:
        """Update one start in the start_list."""
        headers = {
            hdrs.CONTENT_TYPE: "application/json",
            hdrs.AUTHORIZATION: f"Bearer {token}",
        }
        logging.debug(f"New start: {new_start}")
        async with ClientSession() as session:
            async with session.put(
                f"{RACE_SERVICE_URL}/races/{new_start['race_id']}/start-entries/{id}",
                headers=headers,
                json=new_start,
            ) as resp:
                logging.debug(f"update_start_entry - got response {resp.status}")
                if resp.status == 201:
                    pass
                elif resp.status == 401:
                    raise Exception(f"Login expired: {resp}")
                else:
                    servicename = "update_start_entry"
                    body = await resp.json()
                    logging.error(
                        f"{servicename} failed - {resp.status} - {body} {new_start}"
                    )
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return resp.status
