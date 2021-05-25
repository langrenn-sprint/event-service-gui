"""Package for exposing validation endpoint."""
import logging
import os

from aiohttp import web
import aiohttp_jinja2
import jinja2
import motor.motor_asyncio

from .views import (
    Innstillinger,
    Main,
    Ping,
)

LOGGING_LEVEL = os.getenv("LOGGING_LEVEL", "INFO")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 27017))
DB_NAME = os.getenv("DB_NAME", "test")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")


async def create_app() -> web.Application:
    """Create an web application."""
    app = web.Application()
    # Set up logging
    logging.basicConfig(level=LOGGING_LEVEL)
    # Set up static path
    static_path = os.path.join(os.getcwd(), "webserver/static")
    # Set up template path
    template_path = os.path.join(os.getcwd(), "webserver/templates")
    aiohttp_jinja2.setup(
        app,
        enable_async=True,
        loader=jinja2.FileSystemLoader(template_path),
    )
    logging.debug(f"template_path: {template_path}")
    logging.debug(f"static_path: {static_path}")
    # Set up database connection:
    client = motor.motor_asyncio.AsyncIOMotorClient(DB_HOST, DB_PORT)
    db = client.DB_NAME
    app["db"] = db
    app.add_routes(
        [
            web.view("/", Main),
            web.view("/innstillinger", Innstillinger),
            web.view("/ping", Ping),
            web.static("/static", static_path),
        ]
    )
    return app
