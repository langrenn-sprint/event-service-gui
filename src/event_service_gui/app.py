"""Package for exposing validation endpoint."""
import logging
import os

from aiohttp import web
import aiohttp_jinja2
import jinja2

from .views import (
    Main,
    Ping,
)

LOGGING_LEVEL = os.getenv("LOGGING_LEVEL", "INFO")


async def create_app() -> web.Application:
    """Create an web application."""
    app = web.Application()
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

    # Set up backend session

    # app["session"] = ClientSession()

    app.add_routes(
        [
            web.view("/", Main),
            web.view("/ping", Ping),
            web.static("/static", static_path),
        ]
    )
    return app
