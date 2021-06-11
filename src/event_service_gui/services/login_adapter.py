"""Module for login adapter."""
import logging
from typing import List

from aiohttp import ClientSession

# TODO - hente fra configuration
EVENT_SERVICE_URL = "http://localhost:8082/"


class LoginAdapter:
    """Class representing login."""

    async def get_all_login(self) -> List:
        """Get all innstillinger function."""
        login = []
        async with ClientSession() as session:
            async with session.get(EVENT_SERVICE_URL + "login") as resp:
                logging.debug(f"get_all_login - got response {resp.status}")
                if resp.status == "200":
                    login = await resp.json()
        return login
