"""Module for system status adapter.

Reads instance information from environment variables and the system status
file written by the deploy repo (see langrenn-sprint/deploy#13).
"""

import json
import logging
import os
from pathlib import Path

DEFAULT_INSTANCE_ROLE = "unknown"


class SystemStatusAdapter:
    """Class representing the system status file and instance settings."""

    def get_instance(self) -> dict:
        """Get instance name and role from environment variables.

        Returns:
            Dict with name (may be empty) and role (lower case, "unknown" if not set).
        """
        name = os.getenv("INSTANCE_NAME", "").strip()
        role = os.getenv("INSTANCE_ROLE", "").strip().lower() or DEFAULT_INSTANCE_ROLE
        return {"name": name, "role": role}

    def get_status(self) -> dict | None:
        """Read and parse the system status file.

        Returns:
            The parsed status, or None if SYSTEM_STATUS_FILE is not set, or the
            file is missing, unreadable or not a JSON object.
        """
        status_file = os.getenv("SYSTEM_STATUS_FILE", "").strip()
        if not status_file:
            return None
        try:
            with Path(status_file).open(encoding="utf-8") as f:
                status = json.load(f)
        except FileNotFoundError:
            logging.debug(f"System status file not found: {status_file}")
            return None
        except (OSError, ValueError) as e:
            logging.warning(f"Could not read system status file {status_file}: {e}")
            return None
        if not isinstance(status, dict):
            logging.warning(f"System status file {status_file} is not a JSON object")
            return None
        return status
