"""Resource module for liveness resources."""

import logging
import os

from aiohttp import web

CONFIG = os.getenv("CONFIG", "production")


class Ready(web.View):
    """Class representing ready resource."""

    async def get(self) -> web.Response:
        """Ready route function."""
        if CONFIG in {"test", "dev"}:
            pass
        else:  # pragma: no cover
            db = self.request.app["db"]
            result = await db.command("ping")
            logging.debug(f"result of db-ping: {result}")
            if result["ok"] == 1:
                return web.Response(text="OK")
            raise web.HTTPInternalServerError from None

        return web.Response(text="OK")


class Ping(web.View):
    """Class representing ping resource."""

    @staticmethod
    async def get() -> web.Response:
        """Ping route function."""
        return web.Response(text="OK")
