"""Module for photos adapter."""

import copy
import logging
import os
from http import HTTPStatus

from aiohttp import ClientSession, hdrs, web
from multidict import MultiDict

PHOTOS_HOST_SERVER = os.getenv("PHOTOS_HOST_SERVER", "localhost")
PHOTOS_HOST_PORT = os.getenv("PHOTOS_HOST_PORT", "8092")
PHOTO_SERVICE_URL = f"http://{PHOTOS_HOST_SERVER}:{PHOTOS_HOST_PORT}"


class PhotosAdapter:
    """Class representing photos."""

    async def get_all_photos(
        self, token: str, event_id: str, starred: bool, limit: int | None = None
    ) -> list:
        """Get all photos function."""
        photos = []
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        url = f"{PHOTO_SERVICE_URL}/photos?eventId={event_id}"
        if starred:
            url += f"&starred={starred}"
        if limit:
            url += f"&limit={limit}"

        async with (
            ClientSession() as session,
            session.get(url, headers=headers) as resp,
        ):
            if resp.status == HTTPStatus.OK:
                photos = await resp.json()
                logging.debug(f"photos - got response {photos}")
            elif resp.status == HTTPStatus.UNAUTHORIZED:
                err_msg = f"Login expired: {resp}"
                raise Exception(err_msg)
            else:
                logging.error(f"Error {resp.status} getting photos: {resp} ")

        return photos

    async def get_photo(self, token: str, my_id: str) -> dict:
        """Get photo function."""
        photo = {}
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )

        async with (
            ClientSession() as session,
            session.get(f"{PHOTO_SERVICE_URL}/photos/{my_id}", headers=headers) as resp,
        ):
            logging.debug(f"get_photo {my_id} - got response {resp.status}")
            if resp.status == HTTPStatus.OK:
                photo = await resp.json()
                logging.debug(f"photo - got response {photo}")
            elif resp.status == HTTPStatus.UNAUTHORIZED:
                err_msg = f"Login expired: {resp}"
                raise Exception(err_msg)
            else:
                servicename = "get_photo"
                body = await resp.json()
                logging.debug(f"{servicename} failed - {resp.status} - {body}")
                raise web.HTTPBadRequest(
                    reason=f"Error - {resp.status}: {body['detail']}."
                )
        return photo

    async def get_photos_by_race_id(
        self,
        token: str,
        race_id: str,
        limit: int | None = None,
    ) -> list:
        """Get all photos function."""
        photos = []
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        url = f"{PHOTO_SERVICE_URL}/photos?raceId={race_id}"
        if limit:
            url += f"&limit={limit}"

        async with (
            ClientSession() as session,
            session.get(url, headers=headers) as resp,
        ):
            if resp.status == HTTPStatus.OK:
                photos = await resp.json()
                logging.debug(f"photos - got response {photos}")
            elif resp.status == HTTPStatus.UNAUTHORIZED:
                err_msg = f"Login expired: {resp}"
                raise Exception(err_msg)
            else:
                logging.error(f"Error {resp.status} getting photos: {resp} ")
        return photos

    async def get_photos_by_raceclass(
        self,
        token: str,
        event_id: str,
        raceclass: str,
        starred: bool | None = False,
        limit: int | None = None,
    ) -> list:
        """Get all photos function."""
        photos = []
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        url = f"{PHOTO_SERVICE_URL}/photos?eventId={event_id}&raceclass={raceclass}"
        if starred:
            url += f"&starred={starred}"
        if limit:
            url += f"&limit={limit}"

        async with (
            ClientSession() as session,
            session.get(url, headers=headers) as resp,
        ):
            logging.debug(f"get_photos_by_raceclass - got response {resp.status}")
            if resp.status == HTTPStatus.OK:
                photos = await resp.json()
                logging.debug(f"photos - got response {photos}")
            elif resp.status == HTTPStatus.UNAUTHORIZED:
                err_msg = f"Login expired: {resp}"
                raise Exception(err_msg)
            else:
                logging.error(f"Error {resp.status} getting photos: {resp} ")
        return photos

    async def get_photo_by_g_base_url(self, token: str, g_base_url: str) -> dict:
        """Get photo by google id function."""
        photo = {}
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )

        async with (
            ClientSession() as session,
            session.get(
                f"{PHOTO_SERVICE_URL}/photos?gBaseUrl={g_base_url}", headers=headers
            ) as resp,
        ):
            logging.debug(
                f"get_photo_by_g_base_url {g_base_url} - got response {resp.status}"
            )
            if resp.status == HTTPStatus.OK:
                photo = await resp.json()
            elif resp.status == HTTPStatus.UNAUTHORIZED:
                err_msg = f"Login expired: {resp}"
                raise Exception(err_msg)
            else:
                servicename = "get_photo_by_g_base_url"
                body = await resp.json()
                logging.debug(f"{servicename} failed - {resp.status} - {body}")
                raise web.HTTPBadRequest(
                    reason=f"Error - {resp.status}: {body['detail']}."
                )
        return photo

    async def create_photo(self, token: str, photo: dict) -> str:
        """Create new photo function."""
        servicename = "create_photo"
        result = ""
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        request_body = copy.deepcopy(photo)

        async with (
            ClientSession() as session,
            session.post(
                f"{PHOTO_SERVICE_URL}/photos", headers=headers, json=request_body
            ) as resp,
        ):
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

    async def delete_photo(self, token: str, my_id: str) -> int:
        """Delete photo function."""
        servicename = "delete_photo"
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        url = f"{PHOTO_SERVICE_URL}/photos/{my_id}"
        async with (
            ClientSession() as session,
            session.delete(url, headers=headers) as resp,
        ):
            logging.debug(f"Delete photo: {my_id} - res {resp.status}")
            if resp.status == HTTPStatus.NO_CONTENT:
                logging.debug(f"result - got response {resp}")
            else:
                logging.error(f"{servicename} failed - {resp.status} - {resp}")
                raise web.HTTPBadRequest(reason=f"Error - {resp.status}: {resp}.")
        return resp.status

    async def update_photo(self, token: str, my_id: str, request_body: dict) -> int:
        """Update photo function."""
        servicename = "update_photo"
        result = int(HTTPStatus.NO_CONTENT)
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )

        async with (
            ClientSession() as session,
            session.put(
                f"{PHOTO_SERVICE_URL}/photos/{my_id}",
                headers=headers,
                json=request_body,
            ) as resp,
        ):
            result = resp.status
            if resp.status == HTTPStatus.NO_CONTENT:
                logging.debug(f"update photo - got response {resp}")
            elif resp.status == HTTPStatus.UNAUTHORIZED:
                err_msg = f"401 Unathorized - {servicename}"
                raise web.HTTPBadRequest(reason=err_msg)
            else:
                body = await resp.json()
                logging.error(f"{servicename} failed - {resp.status} - {body}")
                raise web.HTTPBadRequest(
                    reason=f"Error - {resp.status}: {body['detail']}."
                )
            logging.debug(f"Updated photo: {my_id} - res {resp.status}")
        return result
