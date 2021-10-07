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

    async def delete_raceplans(self, token: str, id: str) -> str:
        """Delete all raceplans in one event function."""
        headers = {
            hdrs.AUTHORIZATION: f"Bearer {token}",
        }
        logging.info(f"delete raceplans, id: {id}")
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

    async def generate_raceplan(self, token: str, event_id: str) -> str:
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
        """Get all raceplans for event function."""
        headers = MultiDict(
            {
                hdrs.AUTHORIZATION: f"Bearer {token}",
            }
        )
        raceplans = []
        async with ClientSession() as session:
            async with session.get(
                f"{RACE_SERVICE_URL}/raceplans?event-id={event_id}", headers=headers
            ) as resp:
                logging.debug(f"get_all_raceplans - got response {resp.status}")
                if resp.status == 200:
                    raceplans = await resp.json()
                    all_raceplans = await resp.json()
                    for plan in all_raceplans:
                        try:
                            raceplans.append(plan)
                        except Exception as e:
                            logging.error(f"Error - data quality: {e}")
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

    async def get_all_races(self, token: str, event_id: str) -> dict:
        """Get all races for event function."""
        raceplans = await RaceplansAdapter().get_all_raceplans(token, event_id)
        logging.debug(f"Raceplans len {len(raceplans)}")

        races = {}
        if len(raceplans) > 0:
            races = raceplans[0]["races"]
        return races

    async def get_race_by_class(
        self, token: str, event_id: str, valgt_klasse: str
    ) -> dict:
        """Get all races function."""
        races = await RaceplansAdapter().get_all_races(token, event_id)
        for race in races:
            if race["raceclass"] == valgt_klasse:
                return race
        # no match on class - raise error
        logging.error(f"get_race_by_class, no races found for {valgt_klasse}")
        raise web.HTTPBadRequest(reason=f"Ingen løp funnet for {valgt_klasse}.")

        return races

    async def update_raceplan(self, token: str, id: str, new_data: dict) -> int:
        """Update klasser function."""
        returncode = 201
        headers = MultiDict(
            {
                hdrs.CONTENT_TYPE: "application/json",
                hdrs.AUTHORIZATION: f"Bearer {token}",
            }
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
