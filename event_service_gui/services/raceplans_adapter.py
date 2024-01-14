"""Module for raceplans adapter."""
import datetime
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

    async def delete_race(self, token: str, race_id: str) -> str:
        """Delete one race function."""
        servicename = "delete_race"
        headers = {
            hdrs.AUTHORIZATION: f"Bearer {token}",
        }
        async with ClientSession() as session:
            async with session.delete(
                f"{RACE_SERVICE_URL}/races/{race_id}",
                headers=headers,
            ) as resp:
                res = resp.status
                logging.debug(f"delete_race result - got response {resp}")
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

    async def delete_raceplans(self, token: str, event_id: str) -> str:
        """Delete all raceplans in one event function."""
        servicename = "delete_raceplan"
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
                elif resp.status == 401:
                    raise web.HTTPBadRequest(reason=f"401 Unathorized - {servicename}")
                else:
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return str(res)

    async def generate_raceplan(self, token: str, event_id: str) -> int:
        """Generate classes based upon registered contestants."""
        servicename = "generate_raceplan"
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
                elif resp.status == 401:
                    raise web.HTTPBadRequest(reason=f"401 Unathorized - {servicename}")
                else:
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
        # ensure that round always exists by setting F(inal) if missing
        for race in races:
            if "round" in race.keys():
                break
            else:
                race["round"] = "F"
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
        # ensure that round always exists by setting F(inal) if missing
        if "round" in race.keys():
            pass
        else:
            race["round"] = "F"
        return race

    async def get_race_by_order(
        self, token: str, event_id: str, race_order: int
    ) -> dict:
        """Get one race for event function."""
        all_races = await RaceplansAdapter().get_all_races(token, event_id)
        race = {}
        for _race in all_races:
            if _race["order"] == race_order:
                race = await RaceplansAdapter().get_race_by_id(token, _race["id"])
                break
        # ensure that round always exists by setting F(inal) if missing
        if "round" in race.keys():
            pass
        else:
            race["round"] = "F"
        return race

    async def get_races_by_racesclass(
        self, token: str, event_id: str, valgt_klasse: str
    ) -> list:
        """Get all get_races_by_racesclass function."""
        headers = MultiDict(
            [
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        races = []
        async with ClientSession() as session:
            async with session.get(
                f"{RACE_SERVICE_URL}/races?eventId={event_id}&raceclass={valgt_klasse}",
                headers=headers,
            ) as resp:
                logging.debug(
                    f"get_all_races_by_racesclass - got response {resp.status}"
                )
                if resp.status == 200:
                    races = await resp.json()
                elif resp.status == 401:
                    raise Exception(f"Login expired: {resp}")
                else:
                    servicename = "get_all_races_by_racesclass"
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        # ensure that round always exists by setting F(inal) if missing
        for race in races:
            if "round" in race.keys():
                break
            else:
                race["round"] = "F"
        return races

    async def update_order(self, token: str, race_id: str, new_order: int) -> str:
        """Update race order function."""
        race = await RaceplansAdapter().get_race_by_id(token, race_id)
        race["order"] = new_order
        res = await RaceplansAdapter().update_race(token, race["id"], race)
        logging.debug(f"Raceplan update order, result: {res}. {race}")
        informasjon = f"Oppdatert heat {new_order}."

        return informasjon

    async def update_raceplan(self, token: str, id: str, new_data: dict) -> int:
        """Update klasser function."""
        servicename = "update_raceplan"
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
                elif resp.status == 401:
                    raise web.HTTPBadRequest(reason=f"401 Unathorized - {servicename}")
                else:
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )

        return returncode

    async def update_race(self, token: str, id: str, new_data: dict) -> int:
        """Update one race function."""
        servicename = "update_race"
        returncode = 201
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        async with ClientSession() as session:
            async with session.put(
                f"{RACE_SERVICE_URL}/races/{id}",
                headers=headers,
                json=new_data,
            ) as resp:
                returncode = resp.status
                logging.debug(f"update_race - got response {resp.status}")
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

    async def update_race_start_time(
        self, token: str, event_id: str, order: str, new_time: str
    ) -> str:
        """Update race start-time function."""
        servicename = "update_race_start_time"
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
                elif resp.status == 401:
                    raise web.HTTPBadRequest(reason=f"401 Unathorized - {servicename}")
                else:
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        informasjon = f"Tidplan er oppdatert {returncode}"

        return informasjon

    async def update_start_time(
        self, token: str, event_id: str, order: int, new_time: str
    ) -> str:
        """Update race start-time function."""
        delta_seconds = float(0)
        races = await RaceplansAdapter().get_all_races(token, event_id)
        for race in races:
            old_time_obj = datetime.datetime.strptime(
                race["start_time"], "%Y-%m-%dT%H:%M:%S"
            )
            if race["order"] >= order:
                # calculate time difference, delta seconds
                if race["order"] == order:
                    new_time_obj = datetime.datetime.strptime(
                        f"{race['start_time'][:11]}{new_time}", "%Y-%m-%dT%H:%M:%S"
                    )
                    delta_time = new_time_obj - old_time_obj
                    delta_seconds = delta_time.total_seconds()

                # calculate new time
                x = old_time_obj + datetime.timedelta(seconds=delta_seconds)
                new_time = x.strftime("%X")
                race["start_time"] = f"{race['start_time'][:11]}{new_time}"
                res = await RaceplansAdapter().update_race(token, race["id"], race)
                logging.debug(f"Raceplan update time, result: {res}. {race}")

        if delta_seconds < 0:
            delta_seconds_abs = abs(delta_seconds)
            hours, remainder = divmod(delta_seconds_abs, 3600)
            minutes, seconds = divmod(remainder, 60)
            informasjon = f"Fremskyndet med {int(hours)}:{int(minutes)}:{int(seconds)} fra heat {order}. "
        else:
            informasjon = f"Utsettelse på {delta_time} fra heat {order}. "

        return informasjon

    async def validate_raceplan(self, token: str, raceplan_id: str) -> dict:
        """Validate raceplan function."""
        servicename = "validate_raceplan"
        validation_result = {}
        headers = MultiDict(
            [
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        async with ClientSession() as session:
            async with session.post(
                f"{RACE_SERVICE_URL}/raceplans/{raceplan_id}/validate",
                headers=headers,
            ) as resp:
                if resp.status == 401:
                    raise Exception(
                        f"401 Login expired - vennligst logg inn på nytt. Service {servicename}"
                    )
                else:
                    validation_result = await resp.json()

        return validation_result
