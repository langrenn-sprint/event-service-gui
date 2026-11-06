"""Module for user adapter."""

import base64
import binascii
import json
import logging
import os
import time
from http import HTTPStatus
from typing import TypeGuard

from aiohttp import ClientError, ClientSession, hdrs, web
from aiohttp_session import Session
from multidict import MultiDict

from .ids import require_id

USERS_HOST_SERVER = os.getenv("USERS_HOST_SERVER")
USERS_HOST_PORT = os.getenv("USERS_HOST_PORT")
USER_SERVICE_URL = f"http://{USERS_HOST_SERVER}:{USERS_HOST_PORT}"

# A token that expires within this many seconds counts as expired, so a
# request does not reach the backend with a token that runs out on the way.
TOKEN_EXPIRY_MARGIN_SECONDS = 10

# Messages when user-service answers 403: only admin may manage users.
NO_ACCESS_CREATE = "Du har ikke tilgang til å opprette brukere. Krever rollen admin."
NO_ACCESS_DELETE = "Du har ikke tilgang til å slette brukere. Krever rollen admin."
NO_ACCESS_READ = "Du har ikke tilgang til å se brukere. Krever rollen admin."
NO_ACCESS_ACTIVATION = (
    "Du har ikke tilgang til å lage aktiveringslenker. Krever rollen admin."
)

# The shortest password user-service accepts for a new password.
MIN_PASSWORD_LENGTH = 10
PASSWORD_TOO_SHORT = f"Passordet må ha minst {MIN_PASSWORD_LENGTH} tegn."
# Answer to POST /login when the user has not set a password yet.
NOT_ACTIVATED = "Brukeren er ikke aktivert. Bruk aktiveringslenken du har fått."
INVALID_ACTIVATION = (
    "Aktiveringslenken er ugyldig, brukt eller utløpt. Be admin om en ny lenke."
)


class UserAdapter:
    """Class representing user."""

    async def create_user(
        self,
        token: str,
        role: str,
        username: str,
        password: str,
    ) -> tuple[str, dict | None]:
        """Create a user, with a password or with an activation code.

        Without password, user-service makes an activation code, so the user
        can set the password.

        Returns:
            The id of the new user, and for a user without password the
            activation: {"user_id", "code", "expires"}.

        """
        servicename = "create_user"
        w_id = ""
        activation = None
        request_body = {"role": role, "username": username}
        if password:
            request_body["password"] = password
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ],
        )
        async with (
            ClientSession() as session,
            session.post(
                f"{USER_SERVICE_URL}/users",
                headers=headers,
                json=request_body,
            ) as resp,
        ):
            if resp.status == HTTPStatus.CREATED:
                logging.debug(f"create user - got response {resp.status}")
                location = resp.headers[hdrs.LOCATION]
                w_id = location.split(os.path.sep)[-1]
                if not password:
                    activation = await resp.json()
            elif resp.status == HTTPStatus.UNAUTHORIZED:
                raise web.HTTPBadRequest(reason=f"401 Unathorized - {servicename}")
            elif resp.status == HTTPStatus.FORBIDDEN:
                raise web.HTTPForbidden(reason=NO_ACCESS_CREATE)
            elif resp.status == HTTPStatus.UNPROCESSABLE_ENTITY:
                raise web.HTTPBadRequest(reason=PASSWORD_TOO_SHORT)
            else:
                logging.error(f"create_user failed - {resp.status}")
                raise web.HTTPBadRequest(reason="Create user failed.")

        return w_id, activation

    async def create_activation(self, token: str, user_id: str) -> dict:
        """Give the user a new activation code, e.g. to reset the password.

        Earlier codes stop working; a password the user has keeps working
        until the new one is set.

        Returns:
            The activation: {"user_id", "code", "expires"}.

        """
        servicename = "create_activation"
        headers = MultiDict([(hdrs.AUTHORIZATION, f"Bearer {token}")])
        async with (
            ClientSession() as session,
            session.post(
                f"{USER_SERVICE_URL}/users/{require_id(user_id)}/activation",
                headers=headers,
            ) as resp,
        ):
            if resp.status == HTTPStatus.CREATED:
                return await resp.json()
            if resp.status == HTTPStatus.UNAUTHORIZED:
                raise web.HTTPBadRequest(reason=f"401 Unathorized - {servicename}")
            if resp.status == HTTPStatus.FORBIDDEN:
                raise web.HTTPForbidden(reason=NO_ACCESS_ACTIVATION)
            if resp.status == HTTPStatus.NOT_FOUND:
                raise web.HTTPBadRequest(reason="Fant ikke brukeren.")
            logging.error(f"{servicename} failed - {resp.status}")
            raise web.HTTPBadRequest(reason="Kunne ikke lage aktiveringslenke.")

    async def activate(self, code: str, password: str, username: str = "") -> int:
        """Set the password with an activation code. Needs no token.

        With a username, user-service only accepts the code for that user.

        Returns:
            The status from user-service: 204 when the password is set, 400
            for an unknown, used or expired code, 422 for a too short password.

        """
        async with (
            ClientSession() as session,
            session.post(
                f"{USER_SERVICE_URL}/activate",
                json={"code": code, "password": password}
                | ({"username": username} if username else {}),
            ) as resp,
        ):
            if resp.status not in (
                HTTPStatus.NO_CONTENT,
                HTTPStatus.BAD_REQUEST,
                HTTPStatus.UNPROCESSABLE_ENTITY,
            ):
                logging.error(f"activate failed - {resp.status}")
            return resp.status

    async def delete_user(self, token: str, w_id: str) -> int:
        """Delete a user.

        Returns:
            204 when deleted, or 409 when it is the user who is logged in:
            user-service does not let a user delete themselves.

        """
        servicename = "delete_user"
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ],
        )
        url = f"{USER_SERVICE_URL}/users/{require_id(w_id)}"
        async with ClientSession() as session:
            async with session.delete(url, headers=headers) as resp:
                pass
            logging.info(f"Delete user: {w_id} - res {resp.status}")
            if resp.status in (HTTPStatus.NO_CONTENT, HTTPStatus.CONFLICT):
                logging.debug(f"result - got response {resp}")
            elif resp.status == HTTPStatus.UNAUTHORIZED:
                raise web.HTTPBadRequest(reason=f"401 Unathorized - {servicename}")
            elif resp.status == HTTPStatus.FORBIDDEN:
                raise web.HTTPForbidden(reason=NO_ACCESS_DELETE)
            else:
                logging.error(f"delete_user failed - {resp.status}, {resp}")
                raise web.HTTPBadRequest(reason="Delete user failed.")
        return resp.status

    async def get_all_users(self, token: str) -> list:
        """Get all users function.

        Raises an error instead of returning an empty list when the users
        cannot be read, e.g. web.HTTPForbidden when the user is not admin.
        """
        servicename = "get_all_users"
        users = []
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ],
        )

        async with (
            ClientSession() as session,
            session.get(
                f"{USER_SERVICE_URL}/users",
                headers=headers,
            ) as resp,
        ):
            logging.info(f"get_all_users - got response {resp.status}")
            if resp.status == HTTPStatus.OK:
                users = await resp.json()
                logging.debug(f"users - got response {users}")
            elif resp.status == HTTPStatus.UNAUTHORIZED:
                raise web.HTTPBadRequest(reason=f"401 Unathorized - {servicename}")
            elif resp.status == HTTPStatus.FORBIDDEN:
                raise web.HTTPForbidden(reason=NO_ACCESS_READ)
            else:
                logging.error(f"Error {resp.status} getting users: {resp} ")
                raise web.HTTPBadRequest(reason="Get users failed.")
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
            ],
        )
        async with (
            ClientSession() as session,
            session.post(
                f"{USER_SERVICE_URL}/login",
                headers=headers,
                json=request_body,
            ) as resp,
        ):
            result = resp.status
            logging.info(f"do login - got response {result}")
            if result == HTTPStatus.OK:
                body = await resp.json()
                token = body["token"]

                # store token to session variable
                store_token(cookiestorage, token)
                cookiestorage["name"] = username
                cookiestorage["loggedin"] = True
        return result

    async def renew_token(self, token: str) -> tuple[int, str]:
        """Renew a valid token with POST /token/renew in user-service.

        Returns:
            The HTTP status and the new token ("" unless the status is 200).
            Status 0 means that user-service could not be reached.

        """
        headers = MultiDict([(hdrs.AUTHORIZATION, f"Bearer {token}")])
        try:
            async with (
                ClientSession() as session,
                session.post(
                    f"{USER_SERVICE_URL}/token/renew", headers=headers
                ) as resp,
            ):
                if resp.status != HTTPStatus.OK:
                    return resp.status, ""
                body = await resp.json()
                new_token = body.get("token", "") if isinstance(body, dict) else ""
                if not isinstance(new_token, str) or not new_token:
                    logging.error("renew_token - no token in response")
                    return 0, ""
                return resp.status, new_token
        except (ClientError, TimeoutError, ValueError):
            logging.exception("renew_token - could not reach user-service")
            return 0, ""

    def isloggedin(self, cookiestorage: Session) -> bool:
        """Check if user is logged in with a token that has not expired.

        A token without a readable `exp` claim counts as expired.
        """
        if not cookiestorage.get("loggedin"):
            return False
        exp = get_claims_from_token(str(cookiestorage.get("token", ""))).get("exp")
        if not _is_number(exp):
            return False
        return exp - TOKEN_EXPIRY_MARGIN_SECONDS > time.time()


def store_token(cookiestorage: Session, token: str) -> None:
    """Store a new token from user-service in the session.

    The time the token was received is stored too: the token has no `iat`
    claim, and the time is needed to know when half its lifetime has passed.
    """
    cookiestorage["token"] = token
    cookiestorage["role"] = get_role_from_token(token)
    cookiestorage["token_received_at"] = time.time()


def token_needs_renewal(cookiestorage: Session) -> bool:
    """Return True if half the lifetime of the token in the session has passed.

    The lifetime is from when the token was received to its `exp`. A session
    from before the receive time was stored is renewed once to get it.
    """
    exp = get_claims_from_token(str(cookiestorage.get("token", ""))).get("exp")
    if not _is_number(exp):
        return False
    received_at = cookiestorage.get("token_received_at")
    if not _is_number(received_at):
        return True
    return time.time() >= received_at + (exp - received_at) / 2


def _is_number(value: object) -> TypeGuard[float]:
    return isinstance(value, int | float) and not isinstance(value, bool)


def get_claims_from_token(token: str) -> dict:
    """Return the claims of a JWT, or an empty dict if they cannot be read.

    The signature is not verified: the token comes directly from user-service
    in the login response, and the session cookie it is stored in is encrypted.
    The claims are only used to decide what the GUI shows and when to ask the
    user to log in; the backend services still authorize every request with
    the token.
    """
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload))
    except (IndexError, ValueError, binascii.Error, AttributeError):
        logging.warning("Could not read claims from token")
        return {}
    return claims if isinstance(claims, dict) else {}


def get_role_from_token(token: str) -> str:
    """Return the role claim of a JWT, or empty string if not found."""
    role = get_claims_from_token(token).get("role", "")
    return role if isinstance(role, str) else ""
