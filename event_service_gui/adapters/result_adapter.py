"""Module for results adapter."""

import logging
import os

from aiohttp import ClientSession, hdrs, web
from multidict import MultiDict

RACE_HOST_SERVER = os.getenv("RACE_HOST_SERVER", "localhost")
RACE_HOST_PORT = os.getenv("RACE_HOST_PORT", "8088")
RACE_SERVICE_URL = f"http://{RACE_HOST_SERVER}:{RACE_HOST_PORT}"


class ResultAdapter:
    """Class representing result."""

    async def get_race_results(self, token: str, race_id: str, ids_only: bool) -> dict:
        """Get all finish results for one race."""
        headers = MultiDict(
            [
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        url = f"{RACE_SERVICE_URL}/races/{race_id}/race-results?idsOnly={ids_only}"
        results = []
        finish_results = {}
        async with ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                logging.debug(f"get_race_results - got response {resp.status}")
                if resp.status == 200:
                    results = await resp.json()
                else:
                    servicename = "get_race_results"
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        for result_set in results:
            if result_set["timing_point"] == "Finish":
                finish_results = result_set
        return finish_results

    async def update_race_results(
        self, token: str, race_id: str, new_race_results: dict
    ) -> str:
        """Update_race results."""
        servicename = "update_race_results"
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        url = (
            f"{RACE_SERVICE_URL}/races/{race_id}/race-results/{new_race_results['id']}"
        )
        async with ClientSession() as session:
            async with session.put(url, headers=headers, json=new_race_results) as resp:
                res = resp.status
                logging.debug(f"update_race_results - got response {resp}")
                if res == 204:
                    pass
                elif res == 401:
                    raise web.HTTPBadRequest(reason=f"401 Unathorized - {servicename}")
                else:
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return str(res)

    async def update_result_status(
        self, token: str, race_id: str, new_status: int
    ) -> str:
        """Update race result status function."""
        race_results = await ResultAdapter().get_race_results(
            token, race_id, ids_only=True
        )
        if race_results:
            race_results["status"] = new_status
            res = await ResultAdapter().update_race_results(
                token, race_id, race_results
            )
        else:
            return "403"  # cannot update status when there are no results
        return res
