"""Module for raceclasses adapter."""

from http import HTTPStatus
import logging
import os
import urllib.parse

from aiohttp import ClientSession, hdrs, web
from multidict import MultiDict

EVENTS_HOST_SERVER = os.getenv("EVENTS_HOST_SERVER", "localhost")
EVENTS_HOST_PORT = os.getenv("EVENTS_HOST_PORT", "8082")
EVENT_SERVICE_URL = f"http://{EVENTS_HOST_SERVER}:{EVENTS_HOST_PORT}"


class RaceclassesAdapter:
    """Class representing raceclasses."""

    async def create_raceclass(
        self, token: str, event_id: str, request_body: dict
    ) -> str:
        """Create new raceclass function."""
        servicename = "create_raceclass"
        result = ""
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )

        async with ClientSession() as session, session.post(
            f"{EVENT_SERVICE_URL}/events/{event_id}/raceclasses",
            headers=headers,
            json=request_body,
        ) as resp:
            if resp.status == HTTPStatus.CREATED:
                logging.debug(f"create raceclass - got response {resp}")
                location = resp.headers[hdrs.LOCATION]
                result = location.split(os.path.sep)[-1]
            elif resp.status == HTTPStatus.UNAUTHORIZED:
                err_msg = f"401 Unathorized - {servicename}"
                raise web.HTTPBadRequest(reason=err_msg)
            else:
                body = await resp.json()
                logging.error(f"{servicename} failed - {resp.status} - {body}")
                raise web.HTTPBadRequest(
                    reason=f"Error - {resp.status}: {body['detail']}."
                )
        return result

    async def delete_all_raceclasses(self, token: str, event_id: str) -> str:
        """Delete all raceclasses in one event function."""
        servicename = "delete_all_raceclasses"
        headers = {
            hdrs.AUTHORIZATION: f"Bearer {token}",
        }

        async with ClientSession() as session, session.delete(
            f"{EVENT_SERVICE_URL}/events/{event_id}/raceclasses",
            headers=headers,
        ) as resp:
            res = resp.status
            logging.debug(f"delete all result - got response {resp}")
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

    async def delete_raceclass(
        self, token: str, event_id: str, raceclass_id: str
    ) -> str:
        """Delete one raceclass function."""
        servicename = "delete_raceclass"
        headers = {
            hdrs.AUTHORIZATION: f"Bearer {token}",
        }

        async with ClientSession() as session, session.delete(
            f"{EVENT_SERVICE_URL}/events/{event_id}/raceclasses/{raceclass_id}",
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

    async def get_raceclass(self, token: str, event_id: str, raceclass_id: str) -> dict:
        """Get all raceclass function."""
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        raceclass = {}
        async with ClientSession() as session, session.get(
            f"{EVENT_SERVICE_URL}/events/{event_id}/raceclasses/{raceclass_id}",
            headers=headers,
        ) as resp:
            logging.debug(f"get_raceclass - got response {resp.status}")
            if resp.status == HTTPStatus.OK:
                raceclass = await resp.json()
            else:
                servicename = "get_raceclass"
                body = await resp.json()
                logging.error(f"{servicename} failed - {resp.status} - {body}")
                raise web.HTTPBadRequest(
                    reason=f"Error - {resp.status}: {body['detail']}."
                )
        return raceclass

    async def get_raceclass_by_name(self, token: str, event_id: str, name: str) -> dict:
        """Get raceclass by name function."""
        raceclasses = await self.get_raceclasses(token, event_id)
        for raceclass in raceclasses:
            if raceclass["name"] == name:
                return raceclass
        return {}

    async def get_raceclass_by_ageclass(
        self, token: str, event_id: str, ageclass: str
    ) -> dict:
        """Get raceclass by ageclass function."""
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        raceclass = {}
        ageclass_url = urllib.parse.quote(ageclass, safe="")
        async with ClientSession() as session, session.get(
            f"{EVENT_SERVICE_URL}/events/{event_id}/raceclasses?ageclass-name={ageclass_url}",
            headers=headers,
        ) as resp:
            logging.debug(f"get_raceclass_by_ageclass - got response {resp.status}")
            if resp.status == HTTPStatus.OK:
                raceclass = await resp.json()
            else:
                servicename = "get_raceclass_by_ageclass"
                body = await resp.json()
                logging.error(f"{servicename} failed - {resp.status} - {body}")
                raise web.HTTPBadRequest(
                    reason=f"Error - {resp.status}: {body['detail']}."
                )
        return raceclass[0]

    async def get_raceclasses(self, token: str, event_id: str) -> list:
        """Get all raceclasses function."""
        raceclasses = []
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        async with ClientSession() as session, session.get(
            f"{EVENT_SERVICE_URL}/events/{event_id}/raceclasses", headers=headers
        ) as resp:
            logging.debug(f"get_raceclasses - got response {resp.status}")
            if resp.status == HTTPStatus.OK:
                all_raceclasses = await resp.json()
                for raceclass in all_raceclasses:
                    logging.debug(f"Raceclasses order: {raceclass['order']}.")

                    try:
                        if raceclass["event_id"] == event_id:
                            raceclasses.append(raceclass)
                    except Exception:
                        logging.exception("Error - data quality")
            else:
                servicename = "get_raceclasses"
                body = await resp.json()
                logging.error(f"{servicename} failed - {resp.status} - {body}")
                raise web.HTTPBadRequest(
                    reason=f"Error - {resp.status}: {body['detail']}."
                )
        return raceclasses

    async def update_raceclass(
        self, token: str, event_id: str, my_id: str, new_data: dict
    ) -> int:
        """Update klasser function."""
        servicename = "update_raceclass"
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        async with ClientSession() as session, session.put(
            f"{EVENT_SERVICE_URL}/events/{event_id}/raceclasses/{my_id}",
            headers=headers,
            json=new_data,
        ) as resp:
            logging.debug(f"update_raceclass - got response {resp.status}")
            if resp.status == HTTPStatus.NO_CONTENT:
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
        return resp.status
