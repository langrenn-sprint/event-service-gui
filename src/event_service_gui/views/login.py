"""Resource module for login view."""
import logging

from aiohttp import web
import aiohttp_jinja2


class Login(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get route function that return the index page."""
        logging.debug(f"Login: {self}")
        return await aiohttp_jinja2.render_template_async(
            "login.html",
            self.request,
            {
                "lopsinfo": "Langrenn startside",
            },
        )
