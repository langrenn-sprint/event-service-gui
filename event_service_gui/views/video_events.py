"""Resource module for video_event resources."""

import json
import logging

from aiohttp import web

from event_service_gui.adapters import (
    ConfigAdapter,
    StatusAdapter,
)

from .utils import (
    check_login,
)


class VideoEvents(web.View):
    """Class representing the video_event view."""

    async def post(self) -> web.Response:
        """Post route function that updates video events."""
        response = {}
        try:
            user = await check_login(self)
            form = await self.request.post()
            event_id = str(form["event_id"])
            await check_login(self)
            action = form["action"]
            if action in ["status", "toggle"]:
                if "integration_start" in form:
                    await ConfigAdapter().update_config(
                        user["token"], event_id, "VIDEO_STORAGE_MODE", "pull_detections"
                    )
                    await ConfigAdapter().update_config(
                        user["token"], event_id, "INTEGRATION_SERVICE_START", "True"
                    )
                elif "integration_stop" in form:
                    await ConfigAdapter().update_config(
                        user["token"], event_id, "INTEGRATION_SERVICE_START", "False"
                    )
                response["photo_queue_latest"] = await ConfigAdapter().get_config(
                    user["token"], event_id, "GOOGLE_LATEST_PHOTO"
                )
                response[
                    "integration_service_available"
                ] = await ConfigAdapter().get_config(
                    user["token"], event_id, "INTEGRATION_SERVICE_AVAILABLE"
                )
                response[
                    "integration_service_running"
                ] = await ConfigAdapter().get_config(
                    user["token"], event_id, "INTEGRATION_SERVICE_RUNNING"
                )
                response["informasjon"] = await get_integration_status(
                    user["token"], event_id
                )
        except Exception as e:
            if "401" in str(e):
                response["informasjon"] = (
                    "401 unathorized: Logg inn for å hente events."
                )
            else:
                response["informasjon"] = (
                    f"Det har oppstått en feil ved henting av video events. {e}"
                )
            logging.exception("Video events update")
        json_response = json.dumps(response)
        return web.Response(body=json_response)


async def get_integration_status(token: str, event_id: str) -> str:
    """Get video analytics status messages."""
    response = ""
    result_list = await StatusAdapter().get_status(token, event_id, 8)
    for res in result_list:
        info_time = f"<a title={res['time']}>{res['time'][-8:]}</a>"
        res_type = ""
        if res["type"] == "video_status_CAPTURE":
            res_type = "<img id=menu_icon src=../static/capture.png title=Video>"
        elif res["type"] == "video_status_DETECT":
            res_type = "<img id=menu_icon src=../static/detect.png title=Deteksjon>"
        elif res["type"] == "integration_status":
            res_type = "<img id=menu_icon src=../static/upload.png title=Opplasting>"
        if "Error" in res["message"]:
            response += (
                f"{info_time} {res_type} - <span id=red>{res['message']}</span><br>"
            )
        else:
            response += f"{info_time} {res_type} - {res['message']}<br>"
    return response
