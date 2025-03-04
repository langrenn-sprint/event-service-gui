"""Module for contestants adapter."""

import copy
import logging
import os
from typing import List
import urllib.parse

from aiohttp import ClientSession
from aiohttp import hdrs, web
from multidict import MultiDict

from .raceclasses_adapter import RaceclassesAdapter
from .start_adapter import StartAdapter

EVENTS_HOST_SERVER = os.getenv("EVENTS_HOST_SERVER", "localhost")
EVENTS_HOST_PORT = os.getenv("EVENTS_HOST_PORT", "8082")
EVENT_SERVICE_URL = f"http://{EVENTS_HOST_SERVER}:{EVENTS_HOST_PORT}"


class ContestantsAdapter:
    """Class representing contestants."""

    async def assign_bibs(
        self, token: str, event_id: str, start_bib: int = None  # type: ignore
    ) -> str:
        """Generate bibs based upon registrations."""
        servicename = "assign_bibs"
        headers = MultiDict([(hdrs.AUTHORIZATION, f"Bearer {token}")])

        url = f"{EVENT_SERVICE_URL}/events/{event_id}/contestants/assign-bibs"
        if start_bib:
            url += f"?start-bib={start_bib}"
        async with ClientSession() as session:
            async with session.post(url, headers=headers) as resp:
                res = resp.status
                logging.debug(f"assign_bibs result - got response {resp}")
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
            information = "Startnummer tildelt."
        return information

    async def create_contestant(
        self, token: str, event_id: str, contestant: dict
    ) -> str:
        """Create new contestant function."""
        servicename = "create_contestant"
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        request_body = copy.deepcopy(contestant)
        # Trim club name
        if "club" in request_body:
            request_body["club"] = request_body["club"].strip()
            request_body["club"] = request_body["club"].replace("-", "")

        async with ClientSession() as session:
            async with session.post(
                f"{EVENT_SERVICE_URL}/events/{event_id}/contestants",
                headers=headers,
                json=request_body,
            ) as resp:
                if resp.status == 201:
                    logging.debug(f"result - got response {resp}")
                elif resp.status == 401:
                    raise web.HTTPBadRequest(reason=f"401 Unathorized - {servicename}")
                else:
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise Exception(body["detail"]) from None
        return "201"

    async def create_contestants(self, token: str, event_id: str, inputfile) -> str:
        """Create new contestants function."""
        servicename = "create_contestants"
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
                    body = await resp.json()
                elif resp.status == 401:
                    raise web.HTTPBadRequest(reason=f"401 Unathorized - {servicename}")
                else:
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        # trying to parse result - skip if it fails
        informasjon = ""
        try:
            informasjon = f"Opprettet {body['created']} av {body['total']} deltakere."
            if body["updated"]:
                informasjon += f"<br><br>Duplikater ({len(body['updated'])}):"
                for update in body["updated"]:
                    informasjon += f"<br>- {update}"
            if body["failures"]:
                informasjon += f"<br><br>Error ({len(body['failures'])}):"
                for failure in body["failures"]:
                    informasjon += f"<br>- {failure}"
        except Exception:
            logging.error(f"Error parsing result {body}")

        return informasjon

    async def delete_all_contestants(self, token: str, event_id: str) -> str:
        """Delete all contestants in one event function."""
        servicename = "delete_all_contestants"
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
                elif resp.status == 401:
                    raise web.HTTPBadRequest(reason=f"401 Unathorized - {servicename}")
                else:
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return str(res)

    async def delete_contestant(
        self, token: str, event_id: str, contestant: dict
    ) -> str:
        """Delete one contestant function."""
        servicename = "delete_contestant"

        # validation - if racer is in start-list, deletion not allowed
        current_contestant = await ContestantsAdapter().get_contestant(
            token, event_id, contestant["id"]
        )
        start_entries = await StartAdapter().get_start_entries_by_bib(
            token, event_id, current_contestant["bib"]
        )
        if start_entries:
            raise web.HTTPBadRequest(
                reason=f"Startnr {current_contestant['bib']} kan ikke slettes fordi løper er i startliste."
            )

        headers = {
            hdrs.AUTHORIZATION: f"Bearer {token}",
        }
        async with ClientSession() as session:
            async with session.delete(
                f"{EVENT_SERVICE_URL}/events/{event_id}/contestants/{contestant['id']}",
                headers=headers,
            ) as resp:
                res = resp.status
                logging.debug(f"delete result - got response {resp}")
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
        # update number of contestants in raceclass
        try:
            klasse = await RaceclassesAdapter().get_raceclass_by_ageclass(
                token, event_id, contestant["ageclass"]
            )
            if klasse:
                klasse["no_of_contestants"] = klasse["no_of_contestants"] - 1
            result = await RaceclassesAdapter().update_raceclass(
                token, event_id, klasse["id"], klasse
            )
            logging.debug(f"No_of_contestants updated - {result}")
        except Exception as e:
            logging.error(
                f"{servicename} failed on update no of contestants in raceclass {e} - {contestant['ageclass']}"
            )
        return str(res)

    async def get_all_contestants(self, token: str, event_id: str) -> List:
        """Get all contestants function."""
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
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
        return contestants

    async def get_all_contestants_by_ageclass(
        self, token: str, event_id: str, ageclass_name: str
    ) -> List:
        """Get all contestants by ageclass function."""
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        contestants = []
        ageclass_name_url = urllib.parse.quote(ageclass_name, safe="")
        query_param = f"ageclass={ageclass_name_url}"
        async with ClientSession() as session:
            async with session.get(
                f"{EVENT_SERVICE_URL}/events/{event_id}/contestants?{query_param}",
                headers=headers,
            ) as resp:
                logging.debug(f"get_all_contestants - got response {resp.status}")
                if resp.status == 200:
                    contestants = await resp.json()
                else:
                    servicename = "get_all_contestants_by_ageclass"
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return contestants

    async def get_all_contestants_by_raceclass(
        self, token: str, event_id: str, raceclass_name: str
    ) -> List:
        """Get all contestants / by raceclass function."""
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        contestants = []
        raceclass_name_url = urllib.parse.quote(raceclass_name, safe="")
        async with ClientSession() as session:
            async with session.get(
                f"{EVENT_SERVICE_URL}/events/{event_id}/contestants?raceclass={raceclass_name_url}",
                headers=headers,
            ) as resp:
                logging.debug(
                    f"get_all_contestants_by_raceclass ({raceclass_name}) - got response {resp.status}"
                )
                if resp.status == 200:
                    contestants = await resp.json()
                else:
                    servicename = "get_all_contestants_by_raceclass"
                    body = await resp.json()
                    logging.error(
                        f"{servicename} ({raceclass_name}) failed - {resp.status} - {body}"
                    )
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return contestants

    async def get_contestant_by_bib(self, token: str, event_id: str, bib: int) -> dict:
        """Get contestant by bib function."""
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        contestant = []
        async with ClientSession() as session:
            async with session.get(
                f"{EVENT_SERVICE_URL}/events/{event_id}/contestants?bib={bib}",
                headers=headers,
            ) as resp:
                logging.debug(
                    f"get_contestants_by_raceclass - got response {resp.status}"
                )
                if resp.status == 200:
                    contestant = await resp.json()
                else:
                    servicename = "get_contestants_by_bib"
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
            if len(contestant) == 0:
                return {}
        return contestant[0]

    async def get_contestants_by_raceclass(
        self, token: str, event_id: str, raceclass: str
    ) -> List:
        """Get all contestants by raceclass function."""
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        contestants = []
        raceclass_url = urllib.parse.quote(raceclass, safe="")
        async with ClientSession() as session:
            async with session.get(
                f"{EVENT_SERVICE_URL}/events/{event_id}/contestants?raceclass={raceclass_url}",
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
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
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

    async def search_contestants_by_name(
        self, token: str, event_id: str, search_text: str
    ) -> list:
        """Search contestant by name - first or last function."""
        contestants = []
        servicename = "search_contestants_by_name"
        request_body = {"name": search_text}
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        async with ClientSession() as session:
            async with session.post(
                f"{EVENT_SERVICE_URL}/events/{event_id}/contestants/search",
                headers=headers,
                json=request_body,
            ) as resp:
                if resp.status == 200:
                    contestants = await resp.json()
                    logging.debug(f"result - got response {resp}")
                elif resp.status == 401:
                    raise web.HTTPBadRequest(reason=f"401 Unathorized - {servicename}")
                else:
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"{resp.status} Error - {body['detail']}"
                    )
        return contestants

    async def update_contestant(
        self, token: str, event_id: str, contestant: dict
    ) -> str:
        """Update contestants function."""
        servicename = "update_contestant"
        request_body = copy.deepcopy(contestant)
        logging.debug(f"update_contestants, got request_body {request_body}")

        # validation - if racer is in start-list, no changes are allowed
        current_contestant = await ContestantsAdapter().get_contestant(
            token, event_id, contestant["id"]
        )
        start_entries = await StartAdapter().get_start_entries_by_bib(
            token, event_id, current_contestant["bib"]
        )
        if start_entries:
            raise web.HTTPBadRequest(
                reason=f"Startnr {current_contestant['bib']} kan ikke endres fordi løper er i startliste."
            )

        url = f"{EVENT_SERVICE_URL}/events/{event_id}/contestants/{contestant['id']}"
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )

        async with ClientSession() as session:
            async with session.put(url, headers=headers, json=request_body) as resp:
                res = resp.status
                if res == 204:
                    logging.debug(f"result - got response {resp}")
                elif resp.status == 401:
                    raise web.HTTPBadRequest(reason=f"401 Unathorized - {servicename}")
                else:
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )

        return str(resp.status)
