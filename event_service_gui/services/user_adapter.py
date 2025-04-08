"""Module for user adapter."""

import logging
import os

from aiohttp import ClientSession, hdrs, web
from aiohttp_session import Session
from multidict import MultiDict

USERS_HOST_SERVER = os.getenv("USERS_HOST_SERVER")
USERS_HOST_PORT = os.getenv("USERS_HOST_PORT")
USER_SERVICE_URL = f"http://{USERS_HOST_SERVER}:{USERS_HOST_PORT}"


class UserAdapter:
    """Class representing user."""

    async def create_user(
        self,
        token: str,
        role: str,
        username: str,
        password: str,
    ) -> str:
        """Create user function."""
        servicename = "create_user"
        w_id = ""
        request_body = {
            "role": role,
            "username": username,
            "password": password,
        }
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        async with ClientSession() as session:
            async with session.post(
                f"{USER_SERVICE_URL}/users", headers=headers, json=request_body
            ) as resp:
                if resp.status == 201:
                    logging.debug(f"create user - got response {resp}")
                    location = resp.headers[hdrs.LOCATION]
                    w_id = location.split(os.path.sep)[-1]
                elif resp.status == 401:
                    raise web.HTTPBadRequest(reason=f"401 Unathorized - {servicename}")
                else:
                    logging.error(f"create_user failed - {resp.status}")
                    raise web.HTTPBadRequest(reason="Create user failed.")

        return w_id

    async def delete_user(self, token: str, w_id: str) -> int:
        """Delete user function."""
        servicename = "delete_user"
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        url = f"{USER_SERVICE_URL}/users/{w_id}"
        async with ClientSession() as session:
            async with session.delete(url, headers=headers) as resp:
                pass
            logging.info(f"Delete user: {w_id} - res {resp.status}")
            if resp.status == 204:
                logging.debug(f"result - got response {resp}")
            elif resp.status == 401:
                raise web.HTTPBadRequest(reason=f"401 Unathorized - {servicename}")
            else:
                logging.error(f"delete_user failed - {resp.status}, {resp}")
                raise web.HTTPBadRequest(reason="Delete user failed.")
        return resp.status

    async def get_all_users(self, token: str) -> list:
        """Get all users function."""
        users = []
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )

        async with ClientSession() as session:
            async with session.get(
                f"{USER_SERVICE_URL}/users", headers=headers
            ) as resp:
                logging.info(f"get_all_users - got response {resp.status}")
                if resp.status == 200:
                    users = await resp.json()
                    logging.debug(f"users - got response {users}")
                else:
                    logging.error(f"Error {resp.status} getting users: {resp} ")
        return users

    async def login(self, username: str, password: str, cookiestorage: Session) -> int:
        """Perform login function."""
        result = 0
        request_body = {
            "username": username,
            "password": password,
        }
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
            ]
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
                    cookiestorage["name"] = username
                    cookiestorage["loggedin"] = True
        return result

    def isloggedin(self, cookiestorage: Session) -> bool:
        """Check if user is logged in function."""
        try:
            result = cookiestorage["loggedin"]
        except Exception:
            result = False
        return result
