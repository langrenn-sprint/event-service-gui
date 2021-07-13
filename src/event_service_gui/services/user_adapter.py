"""Module for user adapter."""
import logging
import os
from typing import List

from aiohttp import ClientSession, hdrs, web
from aiohttp_session import Session
from multidict import MultiDict

USER_SERVICE_HOST = os.getenv("USER_SERVICE_HOST", "localhost")
USER_SERVICE_PORT = os.getenv("USER_SERVICE_PORT", "8084")
USER_SERVICE_URL = f"http://{USER_SERVICE_HOST}:{USER_SERVICE_PORT}"


class UserAdapter:
    """Class representing user."""

    async def create_user(
        self,
        token: str,
        role: str,
        username: str,
        password: str,
        cookiestorage: Session,
    ) -> str:
        """Create user function."""
        id = ""
        request_body = {
            "role": role,
            "username": username,
            "password": password,
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
                    logging.error(f"create_user failed - {resp.status}")
                    raise web.HTTPBadRequest(reason="Create user failed.")

        return id

    async def delete_user(self, token: str, id: str) -> str:
        """Delete user function."""
        headers = MultiDict(
            {
                hdrs.CONTENT_TYPE: "application/json",
                hdrs.AUTHORIZATION: f"Bearer {token}",
            }
        )
        url = f"{USER_SERVICE_URL}/users/{id}"
        async with ClientSession() as session:
            async with session.delete(url, headers=headers) as response:
                pass
            logging.info(f"Delete user: {id} - res {response.status}")
            if response.status == 204:
                logging.debug(f"result - got response {response}")
            else:
                logging.error(f"delete_user failed - {response.status}, {response}")
                raise web.HTTPBadRequest(reason="Delete user failed.")
        return response.status

    async def get_all_users(self, token: str) -> List:
        """Get all users function."""
        users = []
        headers = MultiDict(
            {
                hdrs.CONTENT_TYPE: "application/json",
                hdrs.AUTHORIZATION: f"Bearer {token}",
            }
        )

        async with ClientSession() as session:
            async with session.get(
                f"{USER_SERVICE_URL}/users", headers=headers
            ) as resp:
                logging.info(f"get_all_users - got response {resp.status}")
                if resp.status == 200:
                    users = await resp.json()
                    logging.debug(f"users - got response {users}")
                elif resp.status == 401:
                    logging.info("TO-DO Performing new login")
                    # Perform login
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
