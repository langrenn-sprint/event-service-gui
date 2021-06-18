"""Module for login adapter."""
import logging

from aiohttp import ClientSession
from aiohttp import hdrs
from multidict import MultiDict

# TODO - hente fra configuration
EVENT_SERVICE_URL = "http://localhost:8082"


class LoginAdapter:
    """Class representing login."""

    async def login(self, username: str, password: str) -> str:
        """Get all innstillinger function."""
        # Perform login
        result = ""
        request_body = {
            "username": username,
            "password": password,
        }
        headers = MultiDict(
            {
                hdrs.CONTENT_TYPE: "application/json",
            },
        )
        async with ClientSession() as session:
            async with session.post(
                f"{EVENT_SERVICE_URL}/login", headers=headers, json=request_body
            ) as resp:
                result = resp.status
                logging.info(f"do login - got response {result}")
                if result == 200:
                    body = await resp.json()
                    logging.info(f"Request body - {body}")
                    token = body["token"]
                    logging.info(f"got token - {token}")
        return result
