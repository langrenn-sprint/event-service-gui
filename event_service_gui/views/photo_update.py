"""Resource module for photo update through ajax."""

import logging

from aiohttp import web

from event_service_gui.services import FotoService

from .utils import (
    check_login_api,
    error_text,
    is_login_error,
    raise_login_expired,
)


class PhotoUpdate(web.View):
    """Class representing the simple photo update service."""

    async def post(self) -> web.Response:
        """Post route function that updates a collection of photos."""
        result = "200"
        user = await check_login_api(self)
        try:
            form = await self.request.post()
            action = form["action"]
            photo_id = str(form["photo_id"])
            if action == "star_on":
                res = await FotoService().star_photo(
                    user["token"], photo_id, starred=True
                )
                logging.debug(f"Starred photo - {res}")
            elif action == "star_off":
                res = await FotoService().star_photo(
                    user["token"], photo_id, starred=False
                )
                logging.debug(f"Un-Starred photo - {res}")
        except Exception as e:
            logging.exception("Un-Starred photo")
            if is_login_error(e):
                raise_login_expired(e)
            result = error_text(e)
        return web.Response(text=result)
