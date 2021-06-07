"""Integration test cases for the ready route."""
from typing import Any

from aiohttp import hdrs
from aiohttp.test_utils import TestClient as _TestClient
from aioresponses import aioresponses
import pytest


@pytest.fixture
def mock_aioresponse() -> Any:
    """Set up aioresponses as fixture."""
    with aioresponses(passthrough=["http://127.0.0.1"]) as m:
        yield m


@pytest.fixture(scope="function")
def mocks(mock_aioresponse: Any) -> Any:
    """Patch the calls to aiohttp.Client.get."""
    # Set up the mocks
    mock_aioresponse.get(
        "",
        body="""
        [{
            "id": "1",
            "name": "Skagen sprint"
        }, {
            "id": "2",
            "name": "Ragde sprint"
        }]
        """,
    )


# --- Bad cases ---
@pytest.mark.integration
async def test_get_main_page_accept_header_not_supported(
    client: _TestClient,
) -> None:
    """Should return 406."""
    headers = {hdrs.ACCEPT: "doesnotexist"}
    resp = await client.get("/", headers=headers)
    assert resp.status == 406
    body = await resp.text()
    assert "406: Not Acceptable" in body
