"""Middleware that renews the token of active users (#205)."""

import logging
from http import HTTPStatus

from aiohttp import hdrs, web
from aiohttp.typedefs import Handler
from aiohttp_session import get_session

from .adapters import UserAdapter
from .adapters.user_adapter import store_token, token_needs_renewal
from .views.utils import LOGIN_AGAIN, login_location, raise_login_expired, return_path

# Requests that never renew the token.
SKIP_PATHS = ("/ping", "/ready", "/login", "/logout")
SKIP_PREFIXES = ("/static/", "/files/")


def skip_token_renewal(path: str) -> bool:
    """Return True for paths that should not renew the token."""
    return path.rstrip("/") in SKIP_PATHS or path.startswith(SKIP_PREFIXES)


def is_page_request(request: web.Request) -> bool:
    """Return True if the browser loads the response as a page.

    Browsers ask for text/html when they load a page or post a form, while
    XMLHttpRequest and fetch from the pages send "Accept: */*".
    """
    return "text/html" in request.headers.get(hdrs.ACCEPT, "")


@web.middleware
async def token_renewal_middleware(
    request: web.Request, handler: Handler
) -> web.StreamResponse:
    """Renew the token in the session when half its lifetime has passed.

    Only a logged-in user with a token that has not expired is renewed, so
    an active user stays logged in, while a session without activity still
    expires with the token. If user-service answers 401 (maximum session
    length reached, user deleted), the user is logged out and sent to the
    login page, and back to this page after login. A request from a page's
    JavaScript gets 401 with JSON instead, as from check_login_api, so the
    page can say so: XMLHttpRequest and fetch would follow the redirect and
    get the login page. Other errors keep the current token, and renewal is
    tried again on the next request.
    """
    if skip_token_renewal(request.path):
        return await handler(request)
    session = await get_session(request)
    if not UserAdapter().isloggedin(session) or not token_needs_renewal(session):
        return await handler(request)

    status, token = await UserAdapter().renew_token(session["token"])
    if status == HTTPStatus.OK:
        store_token(session, token)
        logging.debug("Renewed token")
    elif status == HTTPStatus.UNAUTHORIZED:
        logging.info("Token renewal refused, logging out")
        session.invalidate()
        if not is_page_request(request):
            raise_login_expired()
        raise web.HTTPSeeOther(
            location=login_location(LOGIN_AGAIN, return_path(request))
        )
    else:
        logging.warning(f"Token renewal failed with status {status}, keeping token")
    return await handler(request)
