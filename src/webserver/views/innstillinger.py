"""Resource module for resultat view."""
import logging

from aiohttp import web
import aiohttp_jinja2
from webserver.services import InnstillingerService


class Innstillinger(web.View):
    """Class representing the Innstillinger resource."""

    async def get(self) -> web.Response:
        """Get route function that returns all klasses."""
        _lopsinfo = await InnstillingerService().get_header_footer_info(
            self.request.app["db"],
        )
        logging.debug(_lopsinfo)

        innstillinger = await InnstillingerService().get_all_innstillinger(
            self.request.app["db"]
        )

        # check for updates
        try:
            oppdater = self.request.rel_url.query["Update"]
        except Exception:
            oppdater = ""  # noqa: F841

        # update and store to db
        if oppdater == "Oppdater":
            for innstilling in innstillinger:
                parameter = innstilling["Parameter"]
                innstilling["Verdi"] = self.request.rel_url.query[parameter]
            result = await InnstillingerService().create_innstillinger(
                self.request.app["db"], innstillinger
            )
            logging.debug(result)

        """Get route function."""
        return await aiohttp_jinja2.render_template_async(
            "innstillinger.html",
            self.request,
            {
                "lopsinfo": _lopsinfo,
                "innstillinger": innstillinger,
            },
        )

    async def post(self) -> web.Response:
        """Post route function that creates a collection of klasses."""
        body = await self.request.json()
        logging.debug(f"Got request-body {body} of type {type(body)}")
        result = await InnstillingerService().create_innstillinger(
            self.request.app["db"], body
        )
        return web.Response(status=result)

    async def put(self) -> web.Response:
        """Post route function."""
        # TODO: legge inn database-kall
        raise web.HTTPNotImplemented
