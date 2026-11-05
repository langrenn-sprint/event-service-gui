"""Conftest module."""

from collections.abc import Generator
from http import HTTPStatus
import os
import time
from pathlib import Path
from typing import Any

import pytest
import requests
from aiohttp.test_utils import TestClient as _TestClient
from dotenv import load_dotenv
from requests.exceptions import ConnectionError as _ConnectionError

from event_service_gui import create_app

load_dotenv()
HOST_PORT = int(os.getenv("HOST_PORT", "8080"))
LOG_FILE = "docker-compose-logs.txt"


@pytest.fixture
async def client(aiohttp_client: Any) -> _TestClient:
    """Instantiate server and start it."""
    app = await create_app()
    return await aiohttp_client(app)


def is_responsive(url: Any) -> Any:
    """Return true if response from service is 200."""
    url = f"{url}/ping"
    try:
        response = requests.get(url, timeout=20)
        if response.status_code == HTTPStatus.OK:
            time.sleep(2)  # sleep extra 2 sec
            return True
    except _ConnectionError:
        return False


@pytest.fixture(scope="session")
def http_service(
    request: pytest.FixtureRequest, docker_ip: Any, docker_services: Any
) -> Generator[str]:
    """Ensure that HTTP service is up and responsive.

    If any test failed, the container logs are written to LOG_FILE and to
    the terminal (so they are also in the CI job log). This runs before
    docker_services tears the containers down, as it depends on it.
    """
    # `port_for` takes a container port and returns the corresponding host port
    port = docker_services.port_for("event-service-gui", HOST_PORT)
    url = f"http://{docker_ip}:{port}"
    docker_services.wait_until_responsive(
        timeout=30.0, pause=0.1, check=lambda: is_responsive(url)
    )
    yield url

    if request.session.testsfailed:
        logs = docker_services._docker_compose.execute(  # noqa: SLF001
            "logs --no-color --timestamps"
        ).decode(errors="replace")
        log_file = Path(str(request.config.rootpath)) / LOG_FILE
        log_file.write_text(logs)
        terminal = request.config.pluginmanager.get_plugin("terminalreporter")
        if terminal:
            terminal.write_sep("=", "docker compose logs")
            terminal.write_line(logs)
            terminal.write_line(f"Container logs written to {log_file}")


@pytest.fixture(scope="session")
def docker_compose_file(pytestconfig: Any) -> Any:
    """Override default location of docker-compose.yml file."""
    return os.path.join(str(pytestconfig.rootdir), "./", "docker-compose.yml")


@pytest.fixture(scope="session")
def docker_setup() -> list[str]:
    """Start the services, building the image unless CI has prebuilt it.

    In CI the image is built in a separate step (with OCI labels) and
    tagged as the image in docker-compose.yml. Setting IMAGE_PREBUILT=1
    makes the tests use that image, so the published image is exactly
    the one that was tested.
    """
    if os.environ.get("IMAGE_PREBUILT") == "1":
        return ["up --wait"]
    return ["up --build --wait"]


@pytest.fixture(scope="session")
def docker_cleanup() -> str:
    """Remove the containers, networks and anonymous volumes after the tests.

    The container logs are kept in LOG_FILE if a test failed, see http_service.
    """
    return "down -v"
