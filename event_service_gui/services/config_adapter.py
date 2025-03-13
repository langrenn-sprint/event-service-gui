"""Module for config adapter."""

import copy
from http import HTTPStatus
import json
import logging
import os
from pathlib import Path

from aiohttp import ClientSession, hdrs, web
from multidict import MultiDict

PHOTOS_HOST_SERVER = os.getenv("PHOTOS_HOST_SERVER", "localhost")
PHOTOS_HOST_PORT = os.getenv("PHOTOS_HOST_PORT", "8092")
PHOTO_SERVICE_URL = f"http://{PHOTOS_HOST_SERVER}:{PHOTOS_HOST_PORT}"


class ConfigAdapter:
    """Class representing config."""

    async def get_config(self, token: str, event: dict, key: str) -> str:
        """Get config by key function."""
        config = ""
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        servicename = "get_config"

        async with ClientSession() as session, session.get(
            f"{PHOTO_SERVICE_URL}/config?key={key}&eventId={event['id']}",
            headers=headers,
        ) as resp:
            if resp.status == HTTPStatus.OK:
                config = await resp.json()
            elif resp.status == HTTPStatus.UNAUTHORIZED:
                informasjon = f"Login expired: {resp}"
                raise Exception(informasjon)
            else:
                body = await resp.json()
                informasjon = f"{servicename} failed - {resp.status} - {body['detail']}"
                logging.error(informasjon)
                raise web.HTTPBadRequest(reason=informasjon)
        return config["value"]  # type: ignore

    async def get_all_configs(self, token: str, event: dict) -> list:
        """Get config by google id function."""
        config = []
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        servicename = "get_all_configs"
        if event:
            url = f"{PHOTO_SERVICE_URL}/configs?eventId={event['id']}"
        else:
            url = f"{PHOTO_SERVICE_URL}/configs"

        async with ClientSession() as session, session.get(
            url,
            headers=headers,
        ) as resp:
            if resp.status == HTTPStatus.OK:
                config = await resp.json()
            elif resp.status == HTTPStatus.UNAUTHORIZED:
                informasjon = f"Login expired: {resp}"
                raise Exception(informasjon)
            else:
                body = await resp.json()
                informasjon = f"{servicename} failed - {resp.status} - {body['detail']}"
                logging.error(informasjon)
                raise web.HTTPBadRequest(reason=informasjon)
        return config

    async def get_config_bool(self, token: str, event: dict, key: str) -> bool:
        """Get config boolean value."""
        string_value = await self.get_config(token, event, key)
        boolean_value = False
        if string_value in ["True", "true", "1"]:
            boolean_value = True

        return boolean_value

    async def get_config_int(self, token: str, event: dict, key: str) -> int:
        """Get config int value."""
        string_value = await self.get_config(token, event, key)
        return int(string_value)

    async def get_config_list(self, token: str, event: dict, key: str) -> list:
        """Get config list value."""
        string_value = await self.get_config(token, event, key)
        # convert from json string to list
        return json.loads(string_value)

    async def get_config_img_res_tuple(
        self, token: str, event: dict, key: str
    ) -> tuple:
        """Get config tuple value."""
        string_value = await self.get_config(token, event, key)
        try:
            tuple_value = tuple(map(int, string_value.split("x")))
        except ValueError:
            informasjon = f"Error - {key} is not a tuple."
            raise Exception(informasjon) from None
        return tuple_value

    async def create_config(self, token: str, event: dict, key: str, value: str) -> str:
        """Create new config function."""
        servicename = "create_config"
        result = ""
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        config = {
            "event_id": event["id"],
            "key": key,
            "value": value,
        }
        request_body = copy.deepcopy(config)

        async with ClientSession() as session, session.post(
            f"{PHOTO_SERVICE_URL}/config", headers=headers, json=request_body
        ) as resp:
            if resp.status == HTTPStatus.CREATED:
                logging.debug(f"result - got response {resp}")
                location = resp.headers[hdrs.LOCATION]
                result = location.split(os.path.sep)[-1]
            elif resp.status == HTTPStatus.UNAUTHORIZED:
                informasjon = f"Login expired: {resp}"
                raise Exception(informasjon)
            else:
                body = await resp.json()
                informasjon = f"{servicename} failed - {resp.status} - {body['detail']}"
                logging.error(informasjon)
                raise web.HTTPBadRequest(reason=informasjon)

        return result

    async def init_config(self, token: str, event: dict) -> None:
        """Load default config function - read from file."""
        PROJECT_ROOT = os.path.join(Path.cwd(), "result_service_gui")
        config_file = Path(f"{PROJECT_ROOT}/config/global_settings.json")

        current_configs = await ConfigAdapter().get_all_configs(token, event)

        try:
            with config_file.open() as json_file:
                settings = json.load(json_file)
                for key, value in settings.items():
                    updated = False
                    for config in current_configs:
                        if config["key"] == key:
                            await self.update_config(token, event, key, value)
                            updated = True
                            break
                    if not updated:
                        await self.create_config(token, event, key, value)
        except Exception as e:
            err_info = f"Error linitializing config from {config_file} - {e}"
            logging.error(err_info)
            raise Exception(err_info) from e

    async def update_config_list(
        self, token: str, event: dict, key: str, new_value: list
    ) -> str:
        """Update config list value."""
        new_value_str = json.dumps(new_value)
        return await self.update_config(token, event, key, new_value_str)

    async def update_config(
        self, token: str, event: dict, key: str, new_value: str
    ) -> str:
        """Update config function."""
        servicename = "update_config"
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        request_body = {
            "event_id": event["id"],
            "key": key,
            "value": new_value,
        }

        async with ClientSession() as session, session.put(
            f"{PHOTO_SERVICE_URL}/config", headers=headers, json=request_body
        ) as resp:
            if resp.status == HTTPStatus.NO_CONTENT:
                logging.debug(f"update config - got response {resp}")
            elif resp.status == HTTPStatus.UNAUTHORIZED:
                informasjon = f"Login expired: {resp}"
                raise Exception(informasjon)
            else:
                body = await resp.json()
                informasjon = f"{servicename} failed - {resp.status} - {body['detail']}"
                logging.error(informasjon)
                raise web.HTTPBadRequest(reason=informasjon)
        return str(resp.status)
