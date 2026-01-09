"""Module for start adapter."""

import logging
import os
from http import HTTPStatus

from aiohttp import ClientSession, hdrs, web
from multidict import MultiDict

from .raceclasses_adapter import RaceclassesAdapter
from .raceplans_adapter import RaceplansAdapter

RACE_HOST_SERVER = os.getenv("RACE_HOST_SERVER", "localhost")
RACE_HOST_PORT = os.getenv("RACE_HOST_PORT", "8088")
RACE_SERVICE_URL = f"http://{RACE_HOST_SERVER}:{RACE_HOST_PORT}"


class StartAdapter:
    """Class representing start."""

    async def generate_startlist_for_event(self, token: str, event_id: str) -> str:
        """Generate new start_list function."""
        servicename = "generate_startlist_for_event"
        informasjon = ""
        headers = MultiDict(
            [
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        request_body = {"event_id": event_id}
        async with ClientSession() as session, session.post(
            f"{RACE_SERVICE_URL}/startlists/generate-startlist-for-event",
            headers=headers,
            json=request_body,
        ) as resp:
            if resp.status == HTTPStatus.CREATED:
                logging.debug(f"generate_startlist_for_event - got response {resp}")
                location = resp.headers[hdrs.LOCATION]
                s_id = location.split(os.path.sep)[-1]
                informasjon = f"Suksess! Opprettet startlister. Id: {s_id}"
            elif resp.status == HTTPStatus.UNAUTHORIZED:
                err_msg = f"401 Unathorized - {servicename}"
                raise web.HTTPBadRequest(reason=err_msg)
            else:
                body = await resp.json()
                logging.error(f"{servicename} failed: {resp.status} - {body['detail']}")
                raise web.HTTPBadRequest(
                    reason=f"{servicename} failed - {body['detail']}."
                )
        # shuffle urangerte - this function is intended to be moved to race-service
        informasjon += await shuffle_round2(token, event_id)
        
        return informasjon

    async def delete_start_entry(
        self, token: str, race_id: str, start_entry_id: str
    ) -> str:
        """Delete one start_entry function."""
        servicename = "delete_start_entry"
        headers = {
            hdrs.AUTHORIZATION: f"Bearer {token}",
        }

        async with ClientSession() as session, session.delete(
            f"{RACE_SERVICE_URL}/races/{race_id}/start-entries/{start_entry_id}",
            headers=headers,
        ) as resp:
            res = resp.status
            logging.debug(f"delete result - got response {resp}")
            if res == HTTPStatus.NO_CONTENT:
                pass
            elif resp.status == HTTPStatus.UNAUTHORIZED:
                err_msg = f"401 Unathorized - {servicename}"
                raise web.HTTPBadRequest(reason=err_msg)
            else:
                body = await resp.json()
                logging.error(f"{servicename} failed - {resp.status} - {body}")
                raise web.HTTPBadRequest(
                    reason=f"Error - {resp.status}: {body['detail']}."
                )
        return str(res)

    async def delete_start_list(self, token: str, start_list_id: str) -> str:
        """Delete one start_list function."""
        servicename = "delete_start_list"
        headers = {
            hdrs.AUTHORIZATION: f"Bearer {token}",
        }
        async with ClientSession() as session, session.delete(
            f"{RACE_SERVICE_URL}/startlists/{start_list_id}",
            headers=headers,
        ) as resp:
            res = resp.status
            logging.debug(f"delete result - got response {resp}")
            if res == HTTPStatus.NO_CONTENT:
                pass
            elif resp.status == HTTPStatus.UNAUTHORIZED:
                err_msg = f"401 Unathorized - {servicename}"
                raise web.HTTPBadRequest(reason=err_msg)
            else:
                body = await resp.json()
                logging.error(f"{servicename} failed: {resp.status} - {body['detail']}")
                raise web.HTTPBadRequest(
                    reason=f"{servicename} failed - {body['detail']}."
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
        async with ClientSession() as session, session.get(
            f"{RACE_SERVICE_URL}/races/{race_id}/start-entries",
            headers=headers,
        ) as resp:
            logging.debug(f"get_start_entries_by_race_id - got response {resp.status}")
            if resp.status == HTTPStatus.OK:
                start_entries = await resp.json()
            elif resp.status == HTTPStatus.UNAUTHORIZED:
                err_msg = f"Login expired: {resp}"
                raise Exception(err_msg)

            else:
                servicename = "get_start_entries_by_race_id"
                body = await resp.json()
                logging.error(f"{servicename} failed: {resp.status} - {body['detail']}")
                raise web.HTTPBadRequest(
                    reason=f"{servicename} failed - {body['detail']}."
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
        async with ClientSession() as session, session.get(
            f"{RACE_SERVICE_URL}/races/{race_id}/start-entries/{start_id}",
            headers=headers,
        ) as resp:
            logging.debug(f"get_start_entry_by_id - got response {resp.status}")
            if resp.status == HTTPStatus.OK:
                start_entry = await resp.json()
            elif resp.status == HTTPStatus.UNAUTHORIZED:
                err_msg = f"Login expired: {resp}"
                raise Exception(err_msg)

            else:
                servicename = "get_start_entry_by_id"
                body = await resp.json()
                logging.error(f"{servicename} failed - {resp.status} - {body}")
                raise web.HTTPBadRequest(
                    reason=f"Error - {resp.status}: {body['detail']}."
                )
        return start_entry

    async def get_start_entries_by_bib(
        self, token: str, event_id: str, bib: int
    ) -> list:
        """Get all start_entries by bib function."""
        startlists: list[dict] = []
        start_entries: list[dict] = []
        headers = MultiDict(
            [
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )

        async with ClientSession() as session, session.get(
            f"{RACE_SERVICE_URL}/startlists?eventId={event_id}&bib={bib}",
            headers=headers,
        ) as resp:
            logging.debug(f"get_start_entries_by_bib - got response {resp.status}")
            if resp.status == HTTPStatus.OK:
                startlists = await resp.json()
            else:
                servicename = "get_start_entries_by_bib"
                body = await resp.json()
                logging.error(f"{servicename} failed - {resp.status} - {body}")
                raise web.HTTPBadRequest(
                    reason=f"Error - {resp.status}: {body['detail']}."
                )

        if len(startlists) > 0:
            start_entries = startlists[0]["start_entries"]
        return start_entries

    async def get_all_starts_by_event(self, token: str, event_id: str) -> list:
        """Get all starts function."""
        headers = MultiDict(
            [
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        starts = []
        async with ClientSession() as session, session.get(
            f"{RACE_SERVICE_URL}/startlists?eventId={event_id}", headers=headers
        ) as resp:
            logging.debug(f"get_all_starts_by_event - got response {resp.status}")
            if resp.status == HTTPStatus.OK:
                starts = await resp.json()
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
        servicename = "create_start_entry"
        headers = {
            hdrs.CONTENT_TYPE: "application/json",
            hdrs.AUTHORIZATION: f"Bearer {token}",
        }
        logging.debug(f"New start: {new_start}")
        async with ClientSession() as session, session.post(
            f"{RACE_SERVICE_URL}/races/{new_start['race_id']}/start-entries",
            headers=headers,
            json=new_start,
        ) as resp:
            logging.debug(f"create_start_entry - got response {resp.status}")
            if resp.status == HTTPStatus.CREATED:
                pass
            elif resp.status == HTTPStatus.UNAUTHORIZED:
                err_msg = f"401 Unathorized - {servicename}"
                raise web.HTTPBadRequest(reason=err_msg)
            else:
                body = await resp.json()
                logging.error(f"{servicename} failed: {resp.status} - {body['detail']}")
                raise web.HTTPBadRequest(
                    reason=f"{servicename} failed - {body['detail']}."
                )
        return resp.status

    async def update_start_entry(self, token: str, s_id: str, new_start: dict) -> int:
        """Update one start in the start_list."""
        servicename = "update_start_entry"
        headers = {
            hdrs.CONTENT_TYPE: "application/json",
            hdrs.AUTHORIZATION: f"Bearer {token}",
        }
        logging.debug(f"New start: {new_start}")
        async with ClientSession() as session, session.put(
            f"{RACE_SERVICE_URL}/races/{new_start['race_id']}/start-entries/{s_id}",
            headers=headers,
            json=new_start,
        ) as resp:
            logging.debug(f"update_start_entry - got response {resp.status}")
            if resp.status == HTTPStatus.CREATED:
                pass
            elif resp.status == HTTPStatus.UNAUTHORIZED:
                err_msg = f"401 Unathorized - {servicename}"
                raise web.HTTPBadRequest(reason=err_msg)
            else:
                body = await resp.json()
                logging.error(f"{servicename} failed: {resp.status} - {body['detail']}")
                raise web.HTTPBadRequest(
                    reason=f"{servicename} failed - {body['detail']}."
                )
        return resp.status


async def shuffle_round2(token: str, event_id: str) -> str:
    """Shuffle round 2 start-lists to avoid same heat twice."""
    informasjon = ""
    swap_count = 0
    raceclasses = await RaceclassesAdapter().get_raceclasses(token, event_id)
    for raceclass in raceclasses:
        if not raceclass["ranking"]:
            races = await RaceplansAdapter().get_races_by_racesclass(
                token, event_id, raceclass["name"]
            )
            previous_race_id = ""
            r2_race_info = []
            # find relevant races
            for race in races:
                if race["round"] == "R2":
                    race_info = {
                        "heat": race["heat"],
                        "race_id": race["id"],
                        "previous_race_id": previous_race_id,
                    }
                    r2_race_info.append(race_info)
                previous_race_id = race["id"]
            first = True
            # Oddetallsheat: Bytte ut 2 og 4 til heatet før
            # Partallheat: Bytte ut 1, 3 og 5 til heatet før
            for r2_race in r2_race_info:
                if first:
                    first = False
                elif r2_race["heat"] % 2 == 1:
                    await swap_starts(
                        token,
                        r2_race["race_id"],
                        r2_race["previous_race_id"],
                        [1, 3],
                    )
                    swap_count += 2
                else:
                    await swap_starts(
                        token,
                        r2_race["race_id"],
                        r2_race["previous_race_id"],
                        [0, 2, 4],
                    )
                    swap_count += 3
    if swap_count > 0:
        informasjon = f" R2 for urangerte er stokket - {swap_count} flyttinger."
    return informasjon


async def swap_starts(
    token: str, from_race_id: str, to_race_id: str, start_indexes: list
) -> str:
    """Shuffle round 2 start-lists to avoid same heat twice."""
    from_race = await RaceplansAdapter().get_race_by_id(token, from_race_id)
    to_race = await RaceplansAdapter().get_race_by_id(token, to_race_id)
    for start_index in start_indexes:
        try:
            start1 = from_race["start_entries"][start_index]
            start2 = to_race["start_entries"][start_index]
            new_start1 = {
                "startlist_id": start1["startlist_id"],
                "race_id": start1["race_id"],
                "bib": start2["bib"],
                "starting_position": start1["starting_position"],
                "scheduled_start_time": start1["scheduled_start_time"],
                "name": start2["name"],
                "club": start2["club"],
            }
            new_start2 = {
                "startlist_id": start2["startlist_id"],
                "race_id": start2["race_id"],
                "bib": start1["bib"],
                "starting_position": start2["starting_position"],
                "scheduled_start_time": start2["scheduled_start_time"],
                "name": start1["name"],
                "club": start1["club"],
            }
            await delete_start(token, start1)
            await delete_start(token, start2)
            await create_start(token, new_start1)
            await create_start(token, new_start2)
        except Exception:
            # if error dont change anytning
            logging.debug("Error: Skipping swap of urangert starts")
    return "swapped_starts"


async def delete_start(token: str, form: dict) -> str:
    """Extract form data and delete one start event."""
    w_id = await StartAdapter().delete_start_entry(token, form["race_id"], form["id"])
    logging.debug(f"delete_start {w_id} - {form}")
    return "Slettet start."


async def create_start(token: str, form: dict) -> str:
    """Extract form data and create one start."""
    new_start = {
        "startlist_id": form["startlist_id"],
        "race_id": form["race_id"],
        "bib": int(form["bib"]),
        "starting_position": int(form["starting_position"]),
        "scheduled_start_time": form["scheduled_start_time"],
        "name": form["name"],
        "club": form["club"],
    }
    w_id = await StartAdapter().create_start_entry(token, new_start)
    logging.debug(f"create_start {w_id} - {new_start}")
    return f"Lagt til nr {new_start['bib']}"
