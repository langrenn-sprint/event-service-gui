"""Module for system status service.

Business logic for the instance banner and the system page, based on the
status file format defined in langrenn-sprint/deploy#13.
"""

import datetime
import logging
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from event_service_gui.adapters import ServiceHealthAdapter, SystemStatusAdapter

PRODUCTION_ROLE = "production"
SUPPORTED_SCHEMA_VERSION = 1
MAX_AGE = datetime.timedelta(minutes=15)
DISK_FREE_WARNING_RATIO = 0.10
DISK_FREE_ERROR_RATIO = 0.05
MEMORY_USED_WARNING_RATIO = 0.85
MEMORY_USED_ERROR_RATIO = 0.95
SWAP_USED_WARNING_RATIO = 0.50
DISPLAY_TIMEZONE = "Europe/Oslo"

ROLE_LABELS = {
    "production": "Produksjon",
    "standby": "Reserve",
    "test": "Test",
    "unknown": "Ukjent (INSTANCE_ROLE er ikke satt)",
}
BANNER_LABELS = {
    "standby": "RESERVEINSTANS",
    "test": "TESTINSTANS",
    "unknown": "UKJENT INSTANS (INSTANCE_ROLE er ikke satt)",
}

LEVEL_ERROR = "error"
LEVEL_WARNING = "warning"

SERVICE_RUNNING = "running"
SERVICE_STATE_LABELS = {
    "running": "Kjører",
    "exited": "Stoppet",
    "restarting": "Restarter",
    "paused": "Pauset",
    "created": "Ikke startet",
    "dead": "Død",
    "removing": "Fjernes",
    "missing": "Mangler",
}
HEALTH_OK = "ok"
HEALTH_LABELS = {"ok": "OK", "failed": "Feil", "timeout": "Tidsavbrudd"}
BACKUP_RESULT_LABELS = {"ok": "OK", "failed": "FEILET"}
UPLOAD_STATUS_LABELS = {"ok": "OK", "failed": "Feilet", "disabled": "Av"}
NO_REVISION_TITLE = "Imaget mangler OCI-label org.opencontainers.image.revision"
GITHUB_SOURCE = re.compile(r"^https://github\.com/[\w.-]+/[\w.-]+$")
GIT_REVISION = re.compile(r"^[0-9a-f]{7,40}$")


def _display_tz() -> datetime.tzinfo | None:
    try:
        return ZoneInfo(DISPLAY_TIMEZONE)
    except ZoneInfoNotFoundError:  # pragma: no cover
        return None


def parse_time(value: object) -> datetime.datetime | None:
    """Parse an ISO 8601 timestamp, return None if missing or invalid.

    Timestamps without offset are interpreted as UTC.
    """
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.datetime.fromisoformat(value)
    except ValueError:
        logging.debug(f"Invalid timestamp in system status: {value}")
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.UTC)
    return parsed


def format_time(value: datetime.datetime | None, fmt: str = "%d.%m.%Y %H:%M:%S") -> str:
    """Format a timestamp in local (Norwegian) time."""
    if value is None:
        return ""
    tz = _display_tz()
    return (value.astimezone(tz) if tz else value).strftime(fmt)


def format_age(age: datetime.timedelta | None) -> str:
    """Format an age as a short Norwegian text, e.g. "2 t 5 min"."""
    if age is None:
        return ""
    seconds = int(age.total_seconds())
    if seconds < 0:
        return "i fremtiden"
    minutes, _ = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    if days:
        return f"{days} d {hours} t"
    if hours:
        return f"{hours} t {minutes} min"
    if minutes:
        return f"{minutes} min"
    return f"{seconds} s"


def format_bytes(value: object) -> str:
    """Format a byte count as a human readable size."""
    if not isinstance(value, int | float) or isinstance(value, bool):
        return ""
    size = float(value)
    for unit in ("B", "kB", "MB", "GB", "TB"):
        if abs(size) < 1024 or unit == "TB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return ""  # pragma: no cover


def _service_usage(service: dict, machine_memory: float | None) -> dict:
    """Memory and CPU of a service (from docker stats), NO_VALUE if not running.

    The memory is easiest to judge as a share of the machine's memory
    (memory_share). docker's memory_percent is not used: it is relative to the
    container's limit, which is the machine's memory unless the container has
    its own. An own limit is shown as memory_limit_text.
    """
    memory = _number(service.get("memory_bytes"))
    limit = _number(service.get("memory_limit_bytes"))
    cpu = _number(service.get("cpu_percent"))

    share = ""
    limit_text = ""
    if memory is not None:
        if machine_memory:
            share = format_percent(memory / machine_memory * 100)
        # Without the machine's memory an own limit cannot be told apart, as
        # docker gives the machine's memory as limit when there is none.
        if limit and not machine_memory:
            limit_text = (
                f"{format_percent(memory / limit * 100)} av minnet"
                f" containeren kan bruke ({format_mib(limit)})"
            )
        # An own limit differs from the machine's memory (docker rounds it).
        elif (
            limit
            and machine_memory
            and abs(limit - machine_memory) > 0.02 * machine_memory
        ):
            limit_text = (
                f"{format_percent(memory / limit * 100)} av grensen"
                f" ({format_mib(limit)})"
            )

    return {
        "memory_text": format_mib(memory) or NO_VALUE,
        "memory_share": share,
        "memory_limit_text": limit_text,
        "cpu_text": format_percent(cpu) if cpu is not None else NO_VALUE,
    }


def _time_with_age(
    time: datetime.datetime | None, age: datetime.timedelta | None, empty: str
) -> str:
    """Format e.g. "05.11.2026 12:00:01 (4 min siden)", or empty if no time."""
    if time is None:
        return empty
    return f"{format_time(time)} ({format_age(age)} siden)"


NO_VALUE = "\u2013"  # en dash, shown when a service has no value
MIB = 1024**2
GIB = 1024**3


def format_mib(value: object) -> str:
    """Format a byte count as MiB or GiB, e.g. "523 MiB", "1.2 GiB"."""
    number = _number(value)
    if number is None:
        return ""
    if number == 0:
        return "0 MiB"
    if number >= GIB:
        return f"{number / GIB:.1f} GiB"
    mib = number / MIB
    return f"{mib:.1f} MiB" if mib < 10 else f"{mib:.0f} MiB"


def format_percent(value: float) -> str:
    """Format a percentage (0-100+), one decimal below 10, e.g. "0.4%", "12%"."""
    return f"{value:.1f}%" if value < 10 else f"{value:.0f}%"


def _number(value: object) -> int | float | None:
    """Return the value if it is a non-negative number (not bool), else None."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return value if value >= 0 else None


def _dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


class SystemStatusService:
    """Class representing service layer for instance and system status."""

    def __init__(
        self,
        adapter: SystemStatusAdapter | None = None,
        health_adapter: ServiceHealthAdapter | None = None,
    ) -> None:
        """Initialize the service, optionally with custom adapters."""
        self.adapter = adapter or SystemStatusAdapter()
        self.health_adapter = health_adapter or ServiceHealthAdapter()

    def get_banner(self) -> dict | None:
        """Get the banner to show on all pages, or None in production.

        The banner is based on the environment variables, so it works even if
        the status file is missing. If the status file says the instance is
        restored from a backup, the time of that backup is added.
        """
        instance = self.adapter.get_instance()
        role = instance["role"]
        if role == PRODUCTION_ROLE:
            return None

        label = BANNER_LABELS.get(role, f"INSTANS MED ROLLE «{role}»")
        text = f"{label}: {instance['name']}" if instance["name"] else label

        restore = _dict(_dict(self.adapter.get_status()).get("restore"))
        archive_time = parse_time(restore.get("archive_time"))
        if archive_time:
            text += f" - data fra backup {format_time(archive_time, '%d.%m %H:%M')}"

        return {"role": role, "text": text}

    async def get_live_system_info(self, now: datetime.datetime | None = None) -> dict:
        """Get the system info including a live health check of the services."""
        health = await self.health_adapter.check_services()
        return self.get_system_info(now=now, health=health)

    def get_system_info(
        self, now: datetime.datetime | None = None, health: list[dict] | None = None
    ) -> dict:
        """Get everything the system page shows, including warnings.

        Args:
            now: Current time, for calculating ages.
            health: Result of the live health check (ServiceHealthAdapter),
                merged into the services. None if not checked.
        """
        now = now or datetime.datetime.now(datetime.UTC)
        instance = self.adapter.get_instance()
        info: dict = {
            "instance": {
                **instance,
                "role_text": ROLE_LABELS.get(instance["role"], instance["role"]),
                "is_production": instance["role"] == PRODUCTION_ROLE,
            },
            "has_status": False,
            "warnings": [],
            "checked_at": format_time(now, "%H:%M:%S"),
            "services": None,
        }
        status = self.adapter.get_status()
        if status is None:
            info["services"] = self._merge_health(None, health, info["warnings"])
            return info

        info["has_status"] = True
        warnings: list[dict] = info["warnings"]

        schema_version = status.get("schema_version")
        if schema_version != SUPPORTED_SCHEMA_VERSION:
            warnings.append(
                {
                    "level": LEVEL_WARNING,
                    "text": f"Ukjent versjon av statusfila ({schema_version}), "
                    "noe informasjon kan mangle.",
                }
            )

        # Instance as seen by the deploy scripts
        file_instance = _dict(status.get("instance"))
        info["file_instance"] = {
            "name": file_instance.get("name") or "",
            "role": file_instance.get("role") or "",
        }

        # When the status was generated
        generated_at = parse_time(status.get("generated_at"))
        generated_age = now - generated_at if generated_at else None
        info["generated"] = {
            "time": format_time(generated_at),
            "age": format_age(generated_age),
            "text": _time_with_age(generated_at, generated_age, "ukjent"),
            "stale": generated_age is None or generated_age > MAX_AGE,
        }
        if generated_age is None:
            warnings.append(
                {"level": LEVEL_ERROR, "text": "Statusfila mangler tidspunkt."}
            )
        elif generated_age > MAX_AGE:
            warnings.append(
                {
                    "level": LEVEL_ERROR,
                    "text": f"Statusfila er ikke oppdatert på {format_age(generated_age)}"
                    " - backup/status-jobben kjører kanskje ikke.",
                }
            )

        info["backup"] = self._backup_info(_dict(status.get("backup")), now, warnings)
        info["restore"] = self._restore_info(status.get("restore"))
        info["mongodb"] = self._mongodb_info(_dict(status.get("mongodb")), warnings)
        info["disk"] = self._disk_info(_dict(status.get("disk")), warnings)
        info["memory"] = self._memory_info(status.get("memory"), warnings)
        machine_memory = _number(_dict(status.get("memory")).get("total_bytes"))
        info["services"] = self._merge_health(
            self._services_info(status.get("services"), warnings, machine_memory),
            health,
            warnings,
        )
        return info

    @staticmethod
    def _backup_info(
        backup: dict, now: datetime.datetime, warnings: list[dict]
    ) -> dict:
        last_success = _dict(backup.get("last_success"))
        success_time = parse_time(last_success.get("time"))
        success_age = now - success_time if success_time else None
        upload = _dict(backup.get("upload"))
        upload_status = upload.get("status") or ""
        last_result = backup.get("last_result") or ""

        if success_age is None:
            warnings.append(
                {"level": LEVEL_ERROR, "text": "Ingen vellykket backup er registrert."}
            )
        elif success_age > MAX_AGE:
            warnings.append(
                {
                    "level": LEVEL_ERROR,
                    "text": f"Siste vellykkede backup er {format_age(success_age)} gammel.",
                }
            )
        if last_result == "failed":
            error = backup.get("last_error") or "ukjent feil"
            warnings.append(
                {"level": LEVEL_ERROR, "text": f"Siste backup feilet: {error}"}
            )
        if upload_status == "failed":
            warnings.append(
                {
                    "level": LEVEL_WARNING,
                    "text": "Siste opplasting av backup til sky feilet.",
                }
            )

        upload_time = format_time(parse_time(upload.get("time")))
        last_attempt = format_time(parse_time(backup.get("last_attempt")))
        result_text = BACKUP_RESULT_LABELS.get(last_result, "")
        return {
            "last_attempt": last_attempt,
            "last_attempt_text": " \u2013 ".join(
                t for t in (last_attempt, result_text) if t
            ),
            "last_result": last_result,
            "failed": last_result == "failed",
            "last_error": backup.get("last_error") or "",
            "last_success": {
                "time": format_time(success_time),
                "age": format_age(success_age),
                "stale": success_age is None or success_age > MAX_AGE,
                "text": _time_with_age(success_time, success_age, "Ingen"),
                "file": last_success.get("file") or "",
                "size": format_bytes(last_success.get("size_bytes")),
                "duration_seconds": last_success.get("duration_seconds"),
            },
            "upload": {
                "status": upload_status,
                "status_text": UPLOAD_STATUS_LABELS.get(
                    upload_status, upload_status or "Ukjent"
                ),
                "failed": upload_status == "failed",
                "time": upload_time,
                "time_text": f"({upload_time})" if upload_time else "",
            },
        }

    @staticmethod
    def _restore_info(restore: object) -> dict | None:
        if not isinstance(restore, dict):
            return None
        return {
            "archive": restore.get("archive") or "",
            "archive_sha256": restore.get("archive_sha256") or "",
            "archive_time": format_time(parse_time(restore.get("archive_time"))),
            "restored_at": format_time(parse_time(restore.get("restored_at"))),
            "restored_on": restore.get("restored_on") or "",
        }

    @staticmethod
    def _mongodb_info(mongodb: dict, warnings: list[dict]) -> dict:
        available = mongodb.get("available") is True
        if not available:
            warnings.append(
                {"level": LEVEL_ERROR, "text": "Databasen (MongoDB) svarer ikke."}
            )
        databases = []
        raw_databases = mongodb.get("databases")
        for db in raw_databases if isinstance(raw_databases, list) else []:
            if not isinstance(db, dict):
                continue
            collections = _dict(db.get("collections"))
            databases.append(
                {
                    "name": db.get("name") or "",
                    "size": format_bytes(db.get("size_bytes")),
                    "collections": sorted(collections.items()),
                }
            )
        return {
            "available": available,
            "version": mongodb.get("version") or "",
            "databases": databases,
        }

    @staticmethod
    def _memory_info(memory: object, warnings: list[dict]) -> dict:
        """Memory of the machine; used = total - available (deploy#13).

        `memory` is null (or missing in older files) if it could not be read,
        then everything is shown as "ukjent" without warning.
        """
        memory = _dict(memory)
        total = _number(memory.get("total_bytes"))
        available = _number(memory.get("available_bytes"))
        swap_total = _number(memory.get("swap_total_bytes"))
        swap_free = _number(memory.get("swap_free_bytes"))

        used_text = "ukjent"
        used_ratio = None
        if total and available is not None:
            used = min(max(total - available, 0), total)
            used_ratio = used / total
            used_text = f"{format_mib(used)} av {format_mib(total)} ({used_ratio:.0%})"
            if used_ratio > MEMORY_USED_ERROR_RATIO:
                level = LEVEL_ERROR
            elif used_ratio > MEMORY_USED_WARNING_RATIO:
                level = LEVEL_WARNING
            else:
                level = ""
            if level:
                warnings.append(
                    {
                        "level": level,
                        "text": f"Lite ledig minne: {used_ratio:.0%} brukt "
                        f"({format_mib(total - used)} tilgjengelig).",
                    }
                )

        swap_text = "ukjent"
        swap_ratio = None
        if swap_total == 0:
            swap_text = "Ingen swap"
        elif swap_total and swap_free is not None:
            swap_used = min(max(swap_total - swap_free, 0), swap_total)
            swap_ratio = swap_used / swap_total
            swap_text = (
                f"{format_mib(swap_used)} av {format_mib(swap_total)}"
                f" ({swap_ratio:.0%})"
            )
            if swap_ratio > SWAP_USED_WARNING_RATIO:
                warnings.append(
                    {
                        "level": LEVEL_WARNING,
                        "text": f"Mye swap i bruk: {swap_ratio:.0%} - maskinen har "
                        "for lite minne og kan bli treg.",
                    }
                )

        return {
            "known": used_ratio is not None,
            "total": format_mib(total) or "ukjent",
            "used_text": used_text,
            "used_percent": f"{used_ratio:.0%}" if used_ratio is not None else "",
            "used_warning": used_ratio is not None
            and MEMORY_USED_WARNING_RATIO < used_ratio <= MEMORY_USED_ERROR_RATIO,
            "used_error": used_ratio is not None
            and used_ratio > MEMORY_USED_ERROR_RATIO,
            "swap_text": swap_text,
            "swap_percent": f"{swap_ratio:.0%}" if swap_ratio is not None else "",
            "swap_warning": swap_ratio is not None
            and swap_ratio > SWAP_USED_WARNING_RATIO,
        }

    @staticmethod
    def _disk_info(disk: dict, warnings: list[dict]) -> dict:
        total = disk.get("total_bytes")
        free = disk.get("free_bytes")
        free_ratio = None
        if (
            isinstance(total, int | float)
            and isinstance(free, int | float)
            and total > 0
        ):
            free_ratio = free / total
            if free_ratio < DISK_FREE_ERROR_RATIO:
                level = LEVEL_ERROR
            elif free_ratio < DISK_FREE_WARNING_RATIO:
                level = LEVEL_WARNING
            else:
                level = ""
            if level:
                warnings.append(
                    {
                        "level": level,
                        "text": f"Lite ledig diskplass: {free_ratio:.0%} ({format_bytes(free)}).",
                    }
                )
        free_text = format_bytes(free) or "ukjent"
        if free_ratio is not None:
            free_text += f" ({free_ratio:.0%})"
        return {
            "total": format_bytes(total),
            "free": format_bytes(free),
            "free_percent": f"{free_ratio:.0%}" if free_ratio is not None else "",
            "free_text": free_text,
            "low": free_ratio is not None and free_ratio < DISK_FREE_WARNING_RATIO,
        }

    @staticmethod
    def _services_info(
        services: object, warnings: list[dict], machine_memory: float | None = None
    ) -> list[dict] | None:
        """Containers in the deploy stack, or None if the file has no services.

        Every service that is not running gives an error, e.g. a container
        that has exited or a service in docker-compose.yml without container.
        """
        if not isinstance(services, list):
            return None
        result = []
        for service in services:
            if not isinstance(service, dict):
                continue
            name = service.get("name") or "(uten navn)"
            state = service.get("state") or "unknown"
            running = state == SERVICE_RUNNING
            if not running:
                text = (
                    f"Tjenesten {name} mangler (ingen container)."
                    if state == "missing"
                    else f"Tjenesten {name} kjører ikke (status: {state})."
                )
                warnings.append({"level": LEVEL_ERROR, "text": text})

            revision = service.get("revision")
            revision = revision if isinstance(revision, str) else ""
            source = service.get("source")
            source = source if isinstance(source, str) else ""
            revision_url = (
                f"{source}/commit/{revision}"
                if GITHUB_SOURCE.match(source) and GIT_REVISION.match(revision)
                else ""
            )
            image = service.get("image")
            image = image if isinstance(image, str) else ""
            # Tag of e.g. "mongo:7-jammy"; a ":" before the last "/" is a port.
            tag = image.rpartition(":")[2] if ":" in image else ""
            tag = "" if "/" in tag else tag
            version: dict[str, str | bool]
            if revision:
                version = {"text": revision[:7], "url": revision_url, "title": ""}
            elif tag:
                version = {"text": tag, "url": "", "title": image}
            else:
                version = {"text": "ukjent", "url": "", "title": NO_REVISION_TITLE}
            version["is_revision"] = bool(revision)
            result.append(
                {
                    "name": name,
                    "state": state,
                    "state_text": SERVICE_STATE_LABELS.get(state, state),
                    "running": running,
                    "image": image,
                    "image_tag": tag,
                    "image_created": format_time(
                        parse_time(service.get("image_created"))
                    ),
                    "started_at": format_time(parse_time(service.get("started_at"))),
                    "revision": revision[:7],
                    "revision_url": revision_url,
                    "source": source,
                    "version": version,
                    **_service_usage(service, machine_memory),
                    "health": None,
                }
            )
        return sorted(result, key=lambda s: s["name"])

    @staticmethod
    def _merge_health(
        services: list[dict] | None, health: list[dict] | None, warnings: list[dict]
    ) -> list[dict] | None:
        """Add the live health check to the services from the status file.

        A checked service that is not in the status file (or no status file)
        gets a row with unknown container status. A service that does not
        answer gives an error, unless the container is known not to run
        (that already gives an error).
        """
        if not health:
            return services
        result = list(services or [])
        by_name = {s["name"]: s for s in result}
        for check in health:
            name = check["name"]
            service = by_name.get(name)
            if service is None:
                service = {
                    "name": name,
                    "state": "unknown",
                    "state_text": "Ukjent",
                    "running": None,
                    "image": "",
                    "image_tag": "",
                    "image_created": "",
                    "started_at": "",
                    "revision": "",
                    "revision_url": "",
                    "source": "",
                    "version": {
                        "text": "",
                        "url": "",
                        "title": "",
                        "is_revision": False,
                    },
                    **_service_usage({}, None),
                }
                result.append(service)
            status = check["status"]
            ok = status == HEALTH_OK
            response_ms = check.get("response_ms")
            service["health"] = {
                "status": status,
                "status_text": HEALTH_LABELS.get(status, status),
                "ok": ok,
                "response_ms": response_ms,
                "text": (
                    f"{HEALTH_LABELS.get(status, status)} ({response_ms} ms)"
                    if response_ms is not None
                    else HEALTH_LABELS.get(status, status)
                ),
                "detail": check.get("detail") or "",
            }
            if not ok and service["running"] is not False:
                detail = check.get("detail") or HEALTH_LABELS.get(status, status)
                warnings.append(
                    {
                        "level": LEVEL_ERROR,
                        "text": f"Tjenesten {name} svarer ikke: {detail}.",
                    }
                )
        return sorted(result, key=lambda s: s["name"])
