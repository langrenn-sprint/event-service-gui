"""Resource module for logout view."""

import logging

from aiohttp import web
from aiohttp_session import get_session

from .utils import error_text


class Logout(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get route function that return the index page."""
        try:
            session = await get_session(self.request)
            session.invalidate()
            informasjon = "Du er nå logget ut. Velkommen tilbake!"

        except Exception as e:
            logging.exception("Error")
            informasjon = error_text(e)

        raise web.HTTPSeeOther(location=f"/?informasjon={informasjon}")
