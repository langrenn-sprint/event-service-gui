"""Module for status adapter."""

import copy
import logging
import os
from http import HTTPStatus

from aiohttp import ClientSession, hdrs, web
from dotenv import load_dotenv
from multidict import MultiDict

from .events_adapter import EventsAdapter

# get base settings
load_dotenv()
PHOTOS_HOST_SERVER = os.getenv("PHOTOS_HOST_SERVER", "localhost")
PHOTOS_HOST_PORT = os.getenv("PHOTOS_HOST_PORT", "8092")
PHOTO_SERVICE_URL = f"http://{PHOTOS_HOST_SERVER}:{PHOTOS_HOST_PORT}"


class StatusAdapter:
    """Class representing status."""

    async def get_status(self, token: str, event_id: str, count: int) -> list:
        """Get latest status messages."""
        status = []
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        servicename = "get_status"

        async with ClientSession() as session, session.get(
            f"{PHOTO_SERVICE_URL}/status?count={count}&eventId={event_id}",
            headers=headers,
        ) as resp:
            if resp.status == HTTPStatus.OK:
                status = await resp.json()
            elif resp.status == HTTPStatus.UNAUTHORIZED:
                informasjon = f"Login expired: {resp}"
                raise Exception(informasjon)
            else:
                body = await resp.json()
                informasjon = f"{servicename} failed - {resp.status} - {body['detail']}"
                logging.error(informasjon)
                raise Exception(informasjon)
        return status

    async def get_status_by_type(
        self, token: str, event: dict, status_type: str, count: int
    ) -> list:
        """Get latest status messages for a given type."""
        status = []
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        servicename = "get_status"

        async with ClientSession() as session, session.get(
            f"{PHOTO_SERVICE_URL}/status?count={count}&eventId={event['id']}&type={status_type}",
            headers=headers,
        ) as resp:
            if resp.status == HTTPStatus.OK:
                status = await resp.json()
            elif resp.status == HTTPStatus.UNAUTHORIZED:
                informasjon = f"Login expired: {resp}"
                raise Exception(informasjon)
            else:
                body = await resp.json()
                informasjon = f"{servicename} failed - {resp.status} - {body['detail']}"
                logging.error(informasjon)
                raise Exception(informasjon)
        return status

    async def create_status(
        self, token: str, event: dict, status_type: str, message: str
    ) -> str:
        """Create new status function."""
        servicename = "create_status"
        time = EventsAdapter().get_local_time(event, "log")
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        logging.info(message)
        status_dict = {
            "event_id": event["id"],
            "time": time,
            "type": status_type,
            "message": message,
        }
        request_body = copy.deepcopy(status_dict)

        async with ClientSession() as session, session.post(
            f"{PHOTO_SERVICE_URL}/status", headers=headers, json=request_body
        ) as resp:
            if resp.status == HTTPStatus.CREATED:
                logging.debug(f"result - got response {resp}")
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

    async def delete_all_status(self, token: str, event: dict) -> int:
        """Delete all status function."""
        servicename = "delete_status"
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        url = f"{PHOTO_SERVICE_URL}/status?event_id={event['id']}"
        async with ClientSession() as session, session.delete(
            url, headers=headers
        ) as resp:
            if resp.status == HTTPStatus.NO_CONTENT:
                logging.debug(f"result - got response {resp}")
            else:
                logging.error(f"{servicename} failed - {resp.status} - {resp}")
                raise web.HTTPBadRequest(reason=f"Error - {resp.status}: {resp}.")
        return resp.status
