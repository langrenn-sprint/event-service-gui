"""Resource module for liveness resources."""
from aiohttp import web


class Ready(web.View):
    """Class representing ready resource."""

    async def get(self) -> web.Response:
        """Ready route function."""
        db = self.request.app["db"]
        result = await db.command("ping")
        print(result)
        if result["ok"] == 1:
            return web.Response(text="OK")
        raise web.HTTPInternalServerError


class Ping(web.View):
    """Class representing ping resource."""

    @staticmethod
    async def get() -> web.Response:
        """Ping route function."""
        return web.Response(text="OK")
