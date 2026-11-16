"""How the adapters report a missing or expired login (401)."""

import re

from aiohttp import web

# How the adapters report 401 from a backend service, at the start of the
# message: "401 Unathorized - get_event", "Error - 401: Unauthorized.",
# "get_contestant_by_bib failed - 401 - …" or "create_time_event failed - 401-…".
# Only the status in these places counts, not a 401 elsewhere in the details.
_LOGIN_ERROR_STATUS = re.compile(r"^(?:401\b|Error - 401:|\S+ failed - 401\b)")


def is_login_error(e: Exception) -> bool:
    """Return True if the error is a missing or expired login (401).

    The adapters report 401 with the status first ("401 Unathorized - …",
    "Error - 401: …", "<service> failed - 401 - …") or as "Login expired: …".
    Services that turn errors into messages for the user must let these
    through, so the views can send the user to the login page.
    """
    text = str(e.reason) if isinstance(e, web.HTTPException) else str(e)
    return bool(_LOGIN_ERROR_STATUS.match(text)) or "Login expired" in text
