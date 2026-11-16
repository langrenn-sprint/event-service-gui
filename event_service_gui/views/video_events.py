"""Resource module for video_event resources."""

import json
import logging
from html import escape

from aiohttp import web

from event_service_gui.adapters import (
    ConfigAdapter,
    StatusAdapter,
)
from event_service_gui.adapters.config_adapter import NO_ACCESS_CONFIG

from .utils import (
    ADMIN_ROLE,
    check_login_api,
    is_login_error,
    raise_login_expired,
)


class VideoEvents(web.View):
    """Class representing the video_event view."""

    async def post(self) -> web.Response:
        """Post route function that updates video events."""
        response = {}
        user = await check_login_api(self)
        try:
            form = await self.request.post()
            event_id = str(form["event_id"])
            action = form["action"]
            if action in ["status", "toggle"]:
                # Only admin may start and stop the integration:
                refused = (
                    "integration_start" in form or "integration_stop" in form
                ) and user["role"] != ADMIN_ROLE
                if refused:
                    pass
                elif "integration_start" in form:
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
                if refused:
                    response["informasjon"] = NO_ACCESS_CONFIG
        # informasjon is shown as HTML, see get_integration_status:
        except web.HTTPForbidden as e:
            response["informasjon"] = escape(str(e.reason))
        except Exception as e:
            logging.exception("Video events update")
            if is_login_error(e):
                raise_login_expired(e)
            response["informasjon"] = escape(
                f"Det har oppstått en feil ved henting av video events. {e}"
            )
        json_response = json.dumps(response)
        return web.Response(body=json_response)


async def get_integration_status(token: str, event_id: str) -> str:
    """Get video analytics status messages, as HTML for the timing dashboard.

    The page shows the result with innerHTML, so the data from photo-service
    (time and message) is escaped (#229).
    """
    response = ""
    result_list = await StatusAdapter().get_status(token, event_id, 8)
    for res in result_list:
        time = str(res["time"])
        message = escape(str(res["message"]))
        info_time = f'<a title="{escape(time)}">{escape(time[-8:])}</a>'
        res_type = ""
        if res["type"] == "video_status_CAPTURE":
            res_type = "<img id=menu_icon src=../static/capture.png title=Video>"
        elif res["type"] == "video_status_DETECT":
            res_type = "<img id=menu_icon src=../static/detect.png title=Deteksjon>"
        elif res["type"] == "integration_status":
            res_type = "<img id=menu_icon src=../static/upload.png title=Opplasting>"
        if "Error" in res["message"]:
            response += f"{info_time} {res_type} - <span id=red>{message}</span><br>"
        else:
            response += f"{info_time} {res_type} - {message}<br>"
    return response
