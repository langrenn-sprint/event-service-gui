"""Conftest module."""

import os
from os import environ as env
import time
from typing import Any

from aiohttp.test_utils import TestClient as _TestClient
import pytest
import requests  # type: ignore
from requests.exceptions import ConnectionError, Timeout  # type: ignore

from event_service_gui import create_app

HOST_PORT = int(env.get("HOST_PORT", "8080"))


@pytest.mark.integration
@pytest.fixture
async def client(aiohttp_client: Any) -> _TestClient:
    """Instantiate server and start it."""
    app = await create_app()
    return await aiohttp_client(app)


def is_responsive(url: Any) -> Any:
    """Return true if response from service is 200."""
    url = f"{url}/ping"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            time.sleep(2)  # sleep extra 2 sec
            return True
    except Timeout:
        return False
    except ConnectionError:
        return False


@pytest.mark.contract
@pytest.fixture(scope="session")
def http_service(docker_ip: Any, docker_services: Any) -> Any:
    """Ensure that HTTP service is up and responsive."""
    # `port_for` takes a container port and returns the corresponding host port
    port = docker_services.port_for("event-service-gui", HOST_PORT)
    url = "http://{}:{}".format(docker_ip, port)
    docker_services.wait_until_responsive(
        timeout=30.0, pause=0.1, check=lambda: is_responsive(url)
    )
    return url


@pytest.mark.contract
@pytest.fixture(scope="session")
def docker_compose_file(pytestconfig: Any) -> Any:
    """Override default location of docker-compose.yml file."""
    return os.path.join(str(pytestconfig.rootdir), "./", "docker-compose.yml")
