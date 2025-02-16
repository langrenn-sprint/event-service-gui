"""Resource module for logout view."""

import logging

from aiohttp import web
from aiohttp_session import get_session


class Logout(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get route function that return the index page."""
        try:
            session = await get_session(self.request)
            session.invalidate()
            informasjon = "Du er nå logget ut. Velkommen tilbake!"

        except Exception as e:
            logging.error(f"Error: {e}")
            informasjon = f"Det har oppstått en feil - {e.args}."

        return web.HTTPSeeOther(location=f"/?informasjon={informasjon}")
