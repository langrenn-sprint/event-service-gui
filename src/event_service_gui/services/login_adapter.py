"""Module for login adapter."""
import logging
import os

from aiohttp import ClientSession, hdrs, web
from aiohttp_session import Session
from multidict import MultiDict

USER_SERVICE_HOST = os.getenv("USER_SERVICE_HOST", "localhost")
USER_SERVICE_PORT = os.getenv("USER_SERVICE_PORT", "8084")
USER_SERVICE_URL = f"http://{USER_SERVICE_HOST}:{USER_SERVICE_PORT}"


class LoginAdapter:
    """Class representing login."""

    async def create_user(
        self,
        token: str,
        username: str,
        password: str,
        role: str,
        cookiestorage: Session,
    ) -> int:
        """Create user function."""
        id = ""
        request_body = {
            "username": username,
            "password": password,
            "role": role,
        }
        headers = MultiDict(
            {
                hdrs.CONTENT_TYPE: "application/json",
                hdrs.AUTHORIZATION: f"Bearer {token}",
            },
        )
        async with ClientSession() as session:
            async with session.post(
                f"{USER_SERVICE_URL}/users", headers=headers, json=request_body
            ) as resp:
                if resp.status == 201:
                    logging.debug(f"create user - got response {resp}")
                    location = resp.headers[hdrs.LOCATION]
                    id = location.split(os.path.sep)[-1]
                else:
                    logging.error(f"create_event failed - {resp.status}")
                    raise web.HTTPBadRequest(reason="Create event failed.")

        return id

    async def login(self, username: str, password: str, cookiestorage: Session) -> int:
        """Perform login function."""
        result = 0
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
                f"{USER_SERVICE_URL}/login", headers=headers, json=request_body
            ) as resp:
                result = resp.status
                logging.info(f"do login - got response {result}")
                if result == 200:
                    body = await resp.json()
                    token = body["token"]

                    # store token to session variable
                    cookiestorage["token"] = token
                    cookiestorage["username"] = username
                    cookiestorage["password"] = password
                    cookiestorage["loggedin"] = True
        return result

    def isloggedin(self, cookiestorage: Session) -> bool:
        """Check if user is logged in function."""
        try:
            result = cookiestorage["loggedin"]
        except Exception:
            result = False
        return result
