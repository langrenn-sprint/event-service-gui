"""Module for events adapter."""

import copy
import datetime
from http import HTTPStatus
import json
import logging
import os
from pathlib import Path
from zoneinfo import ZoneInfo

from aiohttp import ClientSession, hdrs, web
from multidict import MultiDict

from .competition_format_adapter import CompetitionFormatAdapter

EVENTS_HOST_SERVER = os.getenv("EVENTS_HOST_SERVER", "localhost")
EVENTS_HOST_PORT = os.getenv("EVENTS_HOST_PORT", "8082")
EVENT_SERVICE_URL = f"http://{EVENTS_HOST_SERVER}:{EVENTS_HOST_PORT}"


class EventsAdapter:
    """Class representing events."""

    async def generate_classes(self, token: str, event_id: str) -> str:
        """Generate classes based upon registered contestants."""
        servicename = "generate_classes"
        headers = MultiDict(
            [
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        url = f"{EVENT_SERVICE_URL}/events/{event_id}/generate-raceclasses"
        async with ClientSession() as session, session.post(
            url, headers=headers
        ) as resp:
            res = resp.status
            logging.debug(f"generate_raceclasses result - got response {resp}")
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
        return "Opprettet klasser."

    async def get_all_events(self, token: str) -> list:
        """Get all events function."""
        events = []
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )

        async with ClientSession() as session, session.get(
            f"{EVENT_SERVICE_URL}/events", headers=headers
        ) as resp:
            logging.debug(f"get_all_events - got response {resp.status}")
            if resp.status == HTTPStatus.OK:
                events = await resp.json()
                logging.debug(f"events - got response {events}")
            elif resp.status == HTTPStatus.UNAUTHORIZED:
                err_msg = f"Login expired: {resp}"
                raise Exception(err_msg)

            else:
                logging.error(f"Error {resp.status} getting events: {resp} ")
        return events

    async def get_event(self, token: str, my_id: str) -> dict:
        """Get event function."""
        event = {}
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )

        async with ClientSession() as session, session.get(
            f"{EVENT_SERVICE_URL}/events/{my_id}", headers=headers
        ) as resp:
            logging.debug(f"get_event {my_id} - got response {resp.status}")
            if resp.status == HTTPStatus.OK:
                event = await resp.json()
                logging.debug(f"event - got response {event}")
            elif resp.status == HTTPStatus.UNAUTHORIZED:
                err_msg = f"Login expired: {resp}"
                raise Exception(err_msg)

            else:
                servicename = "get_event"
                body = await resp.json()
                logging.error(f"{servicename} failed - {resp.status} - {body}")
                raise web.HTTPBadRequest(
                    reason=f"Error - {resp.status}: {body['detail']}."
                )
        return event

    def get_global_setting(self, param_name: str) -> str:
        """Get global settings from .env file."""
        config_file = Path(
            f"{Path.cwd()}/event_service_gui/config/global_settings.json"
        )
        try:
            with config_file.open() as json_file:
                settings = json.load(json_file)
                global_setting = settings[param_name]
        except Exception as e:
            logging.exception(
                f"Global setting {param_name} not found. File path {config_file}"
            )
            raise Exception from e
        return global_setting

    def get_global_setting_int(self, param_name: str) -> int:
        """Get global settings from .env file."""
        string_value = self.get_global_setting(param_name)
        try:
            global_setting_int = int(string_value)
        except Exception as e:
            logging.exception(
                f"Error getting global_setting_int {param_name}. Value {string_value}"
            )
            raise Exception from e
        return global_setting_int

    def get_global_setting_bool(self, param_name: str) -> bool:
        """Get config boolean value."""
        string_value = self.get_global_setting(param_name)
        boolean_value = False
        if string_value in ["True", "true", "1"]:
            boolean_value = True
        return boolean_value

    def get_local_datetime_now(self, event: dict) -> datetime.datetime:
        """Return local datetime object, time zone adjusted from event info."""
        time_zone = event["timezone"]
        if time_zone:
            local_time_obj = datetime.datetime.now(ZoneInfo(time_zone))
        else:
            local_time_obj = datetime.datetime.now(datetime.UTC)
        return local_time_obj

    def get_local_time(self, event: dict, time_format: str) -> str:
        """Return local time string, time zone adjusted from event info."""
        local_time = ""
        time_zone = event["timezone"]
        time_now = (
            datetime.datetime.now(ZoneInfo(time_zone))
            if time_zone
            else datetime.datetime.now(datetime.UTC)
        )

        if time_format == "HH:MM":
            local_time = f"{time_now.strftime('%H')}:{time_now.strftime('%M')}"
        elif time_format == "log":
            local_time = f"{time_now.strftime('%Y')}-{time_now.strftime('%m')}-{time_now.strftime('%d')}T{time_now.strftime('%X')}"
        else:
            local_time = time_now.strftime("%X")
        return local_time

    def get_club_logo_url(self, club_name: str) -> str:
        """Get url to club logo - input is 4 first chars of club name."""
        config_file = Path(f"{Path.cwd()}/event_service_gui/config/sports_clubs.json")
        logo_url = ""
        if club_name:
            try:
                club_name_short = club_name[:4].ljust(4)
                with config_file.open() as json_file:
                    logo_urls = json.load(json_file)
                logo_url = logo_urls[club_name_short]
            except Exception:
                logging.exception(f"Club logo not found - {club_name}")
        return logo_url

    async def create_event(self, token: str, event: dict) -> str:
        """Create new event function."""
        servicename = "create_event"
        result = ""
        # add default values for selected competition format
        competition_formats = await CompetitionFormatAdapter().get_competition_formats(
            token
        )
        for cf in competition_formats:
            if cf["name"] == event["competition_format"]:
                event["datatype"] = cf["datatype"]
                if cf["datatype"] == "interval_start":
                    event["intervals"] = cf["intervals"]
                elif cf["datatype"] == "individual_sprint":
                    event["time_between_groups"] = cf["time_between_groups"]
                    event["time_between_rounds"] = cf["time_between_rounds"]
                    event["time_between_heats"] = cf["time_between_heats"]
                    event["max_no_of_contestants_in_race"] = cf[
                        "max_no_of_contestants_in_race"
                    ]
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        request_body = copy.deepcopy(event)

        async with ClientSession() as session, session.post(
            f"{EVENT_SERVICE_URL}/events", headers=headers, json=request_body
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

    async def delete_event(self, token: str, my_id: str) -> str:
        """Delete event function."""
        servicename = "delete_event"
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        url = f"{EVENT_SERVICE_URL}/events/{my_id}"
        async with ClientSession() as session, session.delete(
            url, headers=headers
        ) as resp:
            if resp.status == HTTPStatus.NO_CONTENT:
                logging.debug(f"result - got response {resp}")
            else:
                body = await resp.json()
                logging.error(f"{servicename} failed - {resp.status} - {body}")
                raise web.HTTPBadRequest(
                    reason=f"Error - {resp.status}: {body['detail']}."
                )
        return str(resp.status)

    async def update_event(self, token: str, my_id: str, request_body: dict) -> str:
        """Update event function."""
        servicename = "update_event"
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )

        async with ClientSession() as session, session.put(
            f"{EVENT_SERVICE_URL}/events/{my_id}", headers=headers, json=request_body
        ) as resp:
            result = resp.status
            if resp.status == HTTPStatus.NO_CONTENT:
                logging.debug(f"update event - got response {resp}")
            elif resp.status == HTTPStatus.UNAUTHORIZED:
                err_msg = f"401 Unathorized - {servicename}"
                raise web.HTTPBadRequest(reason=err_msg)
            else:
                body = await resp.json()
                logging.error(f"{servicename} failed - {resp.status} - {body}")
                raise web.HTTPBadRequest(
                    reason=f"Error - {resp.status}: {body['detail']}."
                )
        return str(result)
