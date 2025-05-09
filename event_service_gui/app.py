"""Package for exposing validation endpoint."""

import base64
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
    Tasks,
    Users,
)

load_dotenv()
LOGGING_LEVEL = os.getenv("LOGGING_LEVEL", "INFO")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "27017"))
DB_NAME = os.getenv("DB_NAME", "test")
DB_USER = os.getenv("DB_USER")
ERROR_FILE = str(os.getenv("ERROR_FILE"))
DB_PASSWORD = os.getenv("DB_PASSWORD")
PROJECT_ROOT = f"{Path.cwd()}/event_service_gui"


async def handler(request) -> web.Response:
    """Create a session handler."""
    session = await get_session(request)
    text = f"Last visited: {session.get('last_visit', None)}"
    return web.Response(text=text)


async def create_app() -> web.Application:
    """Create an web application."""
    app = web.Application()

    # sesson handling - secret_key must be 32 url-safe base64-encoded bytes
    fernet_key = os.getenv("FERNET_KEY", "23EHUWpP_tpleR_RjuX5hxndWqyc0vO-cjNUMSzbjN4=")
    secret_key = base64.urlsafe_b64decode(fernet_key)
    setup(app, EncryptedCookieStorage(secret_key))
    app.router.add_get("/secret", handler)

    # Set up logging - errors to separate file
    logging.basicConfig(level=LOGGING_LEVEL)
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
            web.view("/tasks", Tasks),
            web.view("/users", Users),
        ]
    )

    # Set up static path
    static_dir = Path(PROJECT_ROOT) / "static"
    logging.debug(f"static_dir: {static_dir}")
    app.router.add_static("/static/", path=str(static_dir), name="static")

    return app
