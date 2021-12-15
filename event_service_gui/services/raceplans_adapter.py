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


class RaceplansAdapter:
    """Class representing raceplans."""

    async def delete_raceplans(self, token: str, event_id: str) -> str:
        """Delete all raceplans in one event function."""
        raceplans = await RaceplansAdapter().get_all_raceplans(token, event_id)
        raceplan = raceplans[0]

        headers = {
            hdrs.AUTHORIZATION: f"Bearer {token}",
        }
        logging.info(f"delete raceplans, id: {raceplan['id']}")
        async with ClientSession() as session:
            async with session.delete(
                f"{RACE_SERVICE_URL}/raceplans/{raceplan['id']}",
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

    async def generate_raceplan(self, token: str, event_id: str) -> int:
        """Generate classes based upon registered contestants."""
        headers = MultiDict(
            [
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
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
        """Get all raceplans for event function."""
        headers = MultiDict(
            [
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        raceplans = []
        async with ClientSession() as session:
            async with session.get(
                f"{RACE_SERVICE_URL}/raceplans?eventId={event_id}", headers=headers
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

    async def get_all_races(self, token: str, event_id: str) -> List:
        """Get all races for event function."""
        headers = MultiDict(
            [
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        races = []
        async with ClientSession() as session:
            async with session.get(
                f"{RACE_SERVICE_URL}/races?eventId={event_id}", headers=headers
            ) as resp:
                logging.debug(f"get_all_races - got response {resp.status}")
                if resp.status == 200:
                    races = await resp.json()
                elif resp.status == 401:
                    raise Exception(f"Login expired: {resp}")
                else:
                    servicename = "get_all_races"
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return races

    async def get_race_by_id(self, token: str, race_id: str) -> dict:
        """Get one race for event function."""
        headers = MultiDict(
            [
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        race = {}
        async with ClientSession() as session:
            async with session.get(
                f"{RACE_SERVICE_URL}/races/{race_id}", headers=headers
            ) as resp:
                logging.debug(f"get_race_by_id - got response {resp.status}")
                if resp.status == 200:
                    race = await resp.json()
                elif resp.status == 401:
                    raise Exception(f"Login expired: {resp}")
                else:
                    servicename = "get_race_by_id"
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return race

    async def get_races_by_racesclass(
        self, token: str, event_id: str, valgt_klasse: str
    ) -> list:
        """Get all get_races_by_racesclass function."""
        races = []
        _tmp_races = await RaceplansAdapter().get_all_races(token, event_id)
        for race in _tmp_races:
            if race["raceclass"] == valgt_klasse or ("" == valgt_klasse):
                races.append(race)
        return races

    async def update_raceplan(self, token: str, id: str, new_data: dict) -> int:
        """Update klasser function."""
        returncode = 201
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        async with ClientSession() as session:
            async with session.put(
                f"{RACE_SERVICE_URL}/raceplans/{id}",
                headers=headers,
                json=new_data,
            ) as resp:
                returncode = resp.status
                logging.debug(f"update_raceplan - got response {resp.status}")
                if resp.status == 204:
                    pass
                else:
                    servicename = "update_raceplan"
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )

        return returncode

    async def update_race_start_time(
        self, token: str, event_id: str, order: str, new_time: str
    ) -> str:
        """Update race start-time function."""
        returncode = 0
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        new_data = {
            "order": order,
            "new_time": new_time,
        }
        logging.info(f"New data - update time: {new_data}")

        async with ClientSession() as session:
            async with session.put(
                f"{RACE_SERVICE_URL}/raceplans/update-start-time/{event_id}",
                headers=headers,
                json=new_data,
            ) as resp:
                returncode = resp.status
                logging.debug(f"update_race_start_time - got response {resp.status}")
                if resp.status == 204:
                    pass
                else:
                    servicename = "update_race_start_time"
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        informasjon = f"Tidplan er oppdatert {returncode}"

        return informasjon
