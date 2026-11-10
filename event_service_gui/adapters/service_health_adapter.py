"""Module for service health adapter.

Live health check of the backend services the GUI talks to, see
langrenn-sprint/event-service-gui#203. The checks go from the GUI server to
the services, using the same *_HOST_SERVER / *_HOST_PORT settings as the
other adapters.
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass

import aiohttp

HEALTH_OK = "ok"
HEALTH_FAILED = "failed"
HEALTH_TIMEOUT = "timeout"
DEFAULT_TIMEOUT_SECONDS = 2.0


@dataclass(frozen=True)
class HealthCheck:
    """A service to check: name as in docker-compose.yml, settings prefix, paths."""

    name: str
    env_prefix: str
    paths: tuple[str, ...]


# Services without HTTP endpoint (integration-service, mongodb) are not here,
# they are shown with container status from system.json only.
HEALTH_CHECKS = (
    HealthCheck(
        "competition-format-service", "COMPETITION_FORMAT", ("/ping", "/ready")
    ),
    HealthCheck("event-service", "EVENTS", ("/ping", "/ready")),
    HealthCheck("photo-service", "PHOTOS", ("/ping", "/ready")),
    HealthCheck("race-service", "RACE", ("/ping", "/ready")),
    HealthCheck("user-service", "USERS", ("/ping", "/ready")),
)


class ServiceHealthAdapter:
    """Class representing live health checks of the backend services."""

    def __init__(
        self,
        checks: tuple[HealthCheck, ...] = HEALTH_CHECKS,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        """Initialize with the services to check and timeout per service."""
        self.checks = checks
        self.timeout = timeout

    def get_targets(self) -> list[tuple[HealthCheck, str]]:
        """Get the services to check, with base URL.

        Only services with *_HOST_SERVER set are checked. The adapters have
        defaults (localhost) for local development, but checking those in a
        container would only give false errors.
        """
        targets = []
        for check in self.checks:
            server = os.getenv(f"{check.env_prefix}_HOST_SERVER", "").strip()
            port = os.getenv(f"{check.env_prefix}_HOST_PORT", "").strip()
            if not server:
                continue
            url = f"http://{server}:{port}" if port else f"http://{server}"
            targets.append((check, url))
        return targets

    async def check_services(self) -> list[dict]:
        """Check all configured services in parallel.

        Returns:
            One dict per service: name, status (ok | failed | timeout),
            response_ms (int, None on timeout) and detail (empty if ok).
        """
        targets = self.get_targets()
        if not targets:
            return []
        client_timeout = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=client_timeout) as session:
            return list(
                await asyncio.gather(
                    *(self._check(session, check, url) for check, url in targets)
                )
            )

    async def _check(
        self, session: aiohttp.ClientSession, check: HealthCheck, url: str
    ) -> dict:
        start = time.monotonic()
        status = HEALTH_OK
        detail = ""
        try:
            async with asyncio.timeout(self.timeout):
                for path in check.paths:
                    async with session.get(f"{url}{path}") as resp:
                        if resp.status != 200:
                            status = HEALTH_FAILED
                            detail = f"{path} svarte {resp.status}"
                            break
        except TimeoutError:
            status = HEALTH_TIMEOUT
            detail = f"Ingen svar innen {self.timeout:g} s"
        except (aiohttp.ClientError, OSError) as e:
            status = HEALTH_FAILED
            detail = f"Får ikke kontakt ({type(e).__name__})"
        elapsed_ms = round((time.monotonic() - start) * 1000)
        if status != HEALTH_OK:
            logging.info(f"Health check of {check.name} at {url}: {status} {detail}")
        return {
            "name": check.name,
            "status": status,
            "response_ms": None if status == HEALTH_TIMEOUT else elapsed_ms,
            "detail": detail,
        }
