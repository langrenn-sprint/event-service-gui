"""Module for events adapter."""

from http import HTTPStatus
import json
import logging
import os
from pathlib import Path

from aiohttp import ClientSession, hdrs, web
from multidict import MultiDict

COMPETITION_FORMAT_HOST_SERVER = os.getenv(
    "COMPETITION_FORMAT_HOST_SERVER", "localhost"
)
COMPETITION_FORMAT_HOST_PORT = os.getenv("COMPETITION_FORMAT_HOST_PORT", "8094")
COMPETITION_FORMAT_SERVICE_URL = (
    f"http://{COMPETITION_FORMAT_HOST_SERVER}:{COMPETITION_FORMAT_HOST_PORT}"
)


class CompetitionFormatAdapter:
    """Class representing events."""

    async def create_competition_format(self, token: str, request_body: dict) -> str:
        """Generate create_competition_format standard values."""
        servicename = "create_competition_format"
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        url = f"{COMPETITION_FORMAT_SERVICE_URL}/competition-formats"
        async with ClientSession() as session, session.post(
            url, headers=headers, json=request_body
        ) as resp:
            res = resp.status
            logging.debug(f"create_competition_format result - got response {resp}")
            if res == HTTPStatus.CREATED:
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
        return f"Opprettet competition format {resp.status}."

    async def delete_competition_format(self, token: str, my_id: str) -> str:
        """Delete one competition_format."""
        servicename = "delete_competition_format"
        headers = MultiDict(
            [
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        url = f"{COMPETITION_FORMAT_SERVICE_URL}/competition-formats/{my_id}"
        async with ClientSession() as session, session.delete(
            url, headers=headers
        ) as resp:
            res = resp.status
            logging.debug(f"delete_competition_format result - got response {resp}")
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
        return f"Slettet competition format {resp.status}."

    async def get_competition_formats(self, token: str) -> list:
        """Get competition_formats function."""
        competition_formats = []
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )

        async with ClientSession() as session, session.get(
            f"{COMPETITION_FORMAT_SERVICE_URL}/competition-formats", headers=headers
        ) as resp:
            logging.debug(f"get_competition_formats - got response {resp.status}")
            if resp.status == HTTPStatus.OK:
                competition_formats = await resp.json()
                logging.debug(
                    f"competition_formats - got response {competition_formats}"
                )
            elif resp.status == HTTPStatus.UNAUTHORIZED:
                err_msg = f"Login expired: {resp}"
                raise Exception(err_msg)
            else:
                servicename = "get_competition_formats"
                body = await resp.json()
                logging.error(f"{servicename} failed - {resp.status} - {body}")
                raise web.HTTPBadRequest(
                    reason=f"Error - {resp.status}: {body['detail']}."
                )
        return competition_formats

    def get_default_competition_format(self, format_type: str) -> dict:
        """Get default settings from config file."""
        config_files_directory = f"{Path.cwd()}/event_service_gui/config"
        config_file_name = Path(
            f"{config_files_directory}/competition_format_individual_sprint.json"
        )  # Default value
        if format_type == "default_sprint_all_to_finals":
            config_file_name = Path(
                f"{config_files_directory}/competition_format_individual_sprint_all_to_finals.json"
            )
        elif format_type == "default_interval_start":
            config_file_name = Path(
                f"{config_files_directory}/competition_format_interval_start.json"
            )
        try:
            with config_file_name.open() as json_file:
                default_format = json.load(json_file)
        except Exception as e:
            error_text = f"Default competition format for {format_type} not found. File path {config_files_directory} - {e}"
            logging.exception(error_text)
            logging.exception(
                f"Current directory {Path.cwd()} - content {os.listdir()}"
            )
            raise Exception(error_text) from e
        return default_format

    async def update_competition_format(self, token: str, request_body: dict) -> str:
        """Generate update_competition_format standard values."""
        servicename = "update_competition_format"
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        url = (
            f"{COMPETITION_FORMAT_SERVICE_URL}/competition-formats/{request_body['id']}"
        )
        async with ClientSession() as session, session.put(
            url, headers=headers, json=request_body
        ) as resp:
            res = resp.status
            logging.debug(f"update_competition_format result - got response {resp}")
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
        return f"Oppdatert competition format {resp.status}."

    async def create_race_config(self, token: str, request_body: dict) -> str:
        """Generate create_race_config standard values."""
        servicename = "create_race_config"
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        url = f"{COMPETITION_FORMAT_SERVICE_URL}/race-configs"
        async with ClientSession() as session, session.post(
            url, headers=headers, json=request_body
        ) as resp:
            res = resp.status
            logging.debug(f"create_race_config result - got response {resp}")
            if res == HTTPStatus.CREATED:
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
        return f"Opprettet race-config {resp.status}."

    async def delete_race_config(self, token: str, my_id: str) -> str:
        """Delete one race_config."""
        servicename = "delete_race_config"
        headers = MultiDict(
            [
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        url = f"{COMPETITION_FORMAT_SERVICE_URL}/race-configs/{my_id}"
        async with ClientSession() as session, session.delete(
            url, headers=headers
        ) as resp:
            res = resp.status
            logging.debug(f"delete_race_config result - got response {resp}")
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
        return f"Slettet race-config {resp.status}."

    async def get_race_configs(self, token: str) -> list:
        """Get race_configs function."""
        race_configs = []
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )

        async with ClientSession() as session, session.get(
            f"{COMPETITION_FORMAT_SERVICE_URL}/race-configs", headers=headers
        ) as resp:
            logging.debug(f"get_race_configs - got response {resp.status}")
            if resp.status == HTTPStatus.OK:
                race_configs = await resp.json()
                logging.debug(f"race_configs - got response {race_configs}")
            elif resp.status == HTTPStatus.UNAUTHORIZED:
                err_msg = f"Login expired: {resp}"
                raise Exception(err_msg)
            else:
                servicename = "get_race_configs"
                body = await resp.json()
                logging.error(f"{servicename} failed - {resp.status} - {body}")
                raise web.HTTPBadRequest(
                    reason=f"Error - {resp.status}: {body['detail']}."
                )
        return race_configs

    async def update_race_config(self, token: str, request_body: dict) -> str:
        """Generate update_race_config standard values."""
        servicename = "update_race_config"
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        url = f"{COMPETITION_FORMAT_SERVICE_URL}/race-configs/{request_body['id']}"
        async with ClientSession() as session, session.put(
            url, headers=headers, json=request_body
        ) as resp:
            res = resp.status
            logging.debug(f"update_race_config result - got response {resp}")
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
        return f"Oppdatert race-config {resp.status}."
