"""Package for exposing validation endpoint."""
import base64
import logging
import os
import time

from aiohttp import web
import aiohttp_jinja2
from aiohttp_session import get_session, setup
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from dotenv import load_dotenv
import jinja2
import motor.motor_asyncio

from .views import (
    Contestants,
    Dashboard,
    Events,
    Login,
    Logout,
    Main,
    Ping,
    Raceclasses,
    Raceplans,
    Tasks,
    Users,
)

load_dotenv()
LOGGING_LEVEL = os.getenv("LOGGING_LEVEL", "INFO")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 27017))
DB_NAME = os.getenv("DB_NAME", "test")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")


async def handler(request) -> web.Response:
    """Create a session handler."""
    session = await get_session(request)
    last_visit = session["last_visit"] if "last_visit" in session else None
    session["last_visit"] = time.time()
    text = "Last visited: {}".format(last_visit)
    return web.Response(text=text)


async def create_app() -> web.Application:
    """Create an web application."""
    app = web.Application()

    # sesson handling - secret_key must be 32 url-safe base64-encoded bytes
    # from cryptography import fernet
    # fernet_key = fernet.Fernet.generate_key() - avoid generating new key for every restart
    # print(f"Fernet_key: {fernet_key}")
    fernet_key = os.getenv("FERNET_KEY", "23EHUWpP_tpleR_RjuX5hxndWqyc0vO-cjNUMSzbjN4=")
    secret_key = base64.urlsafe_b64decode(fernet_key)
    setup(app, EncryptedCookieStorage(secret_key))
    app.router.add_get("/secret", handler)

    # Set up logging
    logging.basicConfig(level=LOGGING_LEVEL)
    # Set up static path
    static_path = os.path.join(os.getcwd(), "event_service_gui/static")
    # Set up template path
    template_path = os.path.join(os.getcwd(), "event_service_gui/templates")
    aiohttp_jinja2.setup(
        app,
        enable_async=True,
        loader=jinja2.FileSystemLoader(template_path),
    )
    logging.debug(f"template_path: {template_path}")
    logging.debug(f"static_path: {static_path}")

    # todo - remove: Set up database connection:
    client = motor.motor_asyncio.AsyncIOMotorClient(DB_HOST, DB_PORT)
    db = client.DB_NAME
    app["db"] = db

    app.add_routes(
        [
            web.view("/", Main),
            web.view("/contestants", Contestants),
            web.view("/dashboard", Dashboard),
            web.view("/events", Events),
            web.view("/login", Login),
            web.view("/logout", Logout),
            web.view("/ping", Ping),
            web.view("/raceclasses", Raceclasses),
            web.view("/raceplans", Raceplans),
            web.view("/tasks", Tasks),
            web.view("/users", Users),
            web.static("/static", static_path),
        ]
    )
    return app
