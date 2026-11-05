"""Package for exposing validation endpoint."""

import base64
import binascii
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

import aiohttp_jinja2
import jinja2
from aiohttp import web
from aiohttp_session import get_session, setup
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from dotenv import load_dotenv

from .middleware import token_renewal_middleware
from .services import SystemStatusService
from .views import (
    Contestants,
    Control,
    CsvList,
    Events,
    Login,
    Logout,
    Main,
    Ping,
    PrintContestants,
    Raceclasses,
    Raceplans,
    Seeding,
    Settings,
    System,
    Tasks,
    Users,
)
from .views.utils import ADMIN_ROLE

load_dotenv()
LOGGING_LEVEL = os.getenv("LOGGING_LEVEL", "INFO")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "27017"))
DB_NAME = os.getenv("DB_NAME", "test")
DB_USER = os.getenv("DB_USER")
ERROR_FILE = str(os.getenv("ERROR_FILE"))
DB_PASSWORD = os.getenv("DB_PASSWORD")
PROJECT_ROOT = f"{Path.cwd()}/event_service_gui"

FERNET_KEY_LENGTH = 32
FERNET_KEY_HELP = (
    "Set FERNET_KEY to 32 url-safe base64-encoded bytes, e.g. generated with: "
    "python3 -c 'import base64, os; "
    "print(base64.urlsafe_b64encode(os.urandom(32)).decode())'"
)


def get_session_secret_key() -> bytes:
    """Return the key that encrypts the session cookie, from FERNET_KEY.

    There is no default: a key in the source code would let anyone make a
    valid session cookie. A missing or invalid key stops the app.
    """
    fernet_key = os.getenv("FERNET_KEY", "").strip()
    if not fernet_key:
        msg = f"FERNET_KEY is not set. {FERNET_KEY_HELP}"
        raise RuntimeError(msg)
    try:
        secret_key = base64.urlsafe_b64decode(fernet_key)
    except (binascii.Error, ValueError):
        secret_key = b""
    if len(secret_key) != FERNET_KEY_LENGTH:
        msg = f"FERNET_KEY is not valid. {FERNET_KEY_HELP}"
        raise RuntimeError(msg)
    return secret_key


def get_session_storage() -> EncryptedCookieStorage:
    """Return the session cookie storage.

    max_age is the maximum session length (JWT_MAX_SESSION_SECONDS, same as in
    user-service), so the session survives a browser restart. The cookie is
    only sent over https when SESSION_COOKIE_SECURE is true, which should be
    set when the GUI runs behind https.
    """
    max_age = int(os.getenv("JWT_MAX_SESSION_SECONDS", "86400"))
    secure = os.getenv("SESSION_COOKIE_SECURE", "false").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    return EncryptedCookieStorage(
        get_session_secret_key(),
        max_age=max_age,
        secure=secure,
        httponly=True,
        samesite="Lax",
    )


async def handler(request) -> web.Response:
    """Create a session handler."""
    session = await get_session(request)
    text = f"Last visited: {session.get('last_visit', None)}"
    return web.Response(text=text)


async def instance_context_processor(request: web.Request) -> dict:
    """Add instance banner and admin flag to the context of all templates."""
    instance_banner = None
    try:
        instance_banner = SystemStatusService().get_banner()
    except Exception:
        logging.exception("Error creating instance banner")
    is_admin = False
    try:
        session = await get_session(request)
        is_admin = session.get("role") == ADMIN_ROLE
    except Exception:
        logging.exception("Error reading role from session")
    return {"instance_banner": instance_banner, "is_admin": is_admin}


async def create_app() -> web.Application:
    """Create an web application."""
    app = web.Application()

    # session handling
    setup(app, get_session_storage())
    # after the session middleware, so it can read and update the session
    app.middlewares.append(token_renewal_middleware)
    app.router.add_get("/secret", handler)

    # Set up logging - errors to separate file
    logging.basicConfig(level=LOGGING_LEVEL)
    logging.getLogger().setLevel(
        LOGGING_LEVEL
    )  # always applies, even if handlers pre-exist
    file_handler = RotatingFileHandler(ERROR_FILE, maxBytes=1024 * 1024, backupCount=5)
    file_handler.setLevel(logging.ERROR)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    logging.getLogger().addHandler(file_handler)

    # Set up template path
    template_path = Path(PROJECT_ROOT) / "templates"
    aiohttp_jinja2.setup(
        app,
        enable_async=True,
        loader=jinja2.FileSystemLoader(str(template_path)),
        context_processors=[instance_context_processor],
    )
    logging.debug(f"template_path: {template_path}")

    app.add_routes(
        [
            web.view("/", Main),
            web.view("/csv", CsvList),
            web.view("/contestants", Contestants),
            web.view("/control", Control),
            web.view("/events", Events),
            web.view("/login", Login),
            web.view("/logout", Logout),
            web.view("/ping", Ping),
            web.view("/print_contestants", PrintContestants),
            web.view("/raceclasses", Raceclasses),
            web.view("/raceplans", Raceplans),
            web.view("/seeding", Seeding),
            web.view("/settings", Settings),
            web.view("/system", System),
            web.view("/tasks", Tasks),
            web.view("/users", Users),
        ]
    )

    # Set up static path
    static_dir = Path(PROJECT_ROOT) / "static"
    logging.debug(f"static_dir: {static_dir}")
    app.router.add_static("/static/", path=str(static_dir), name="static")

    return app
