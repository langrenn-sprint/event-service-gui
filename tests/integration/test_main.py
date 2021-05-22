"""Integration test cases for the ready route."""
from aiohttp import hdrs
from aiohttp.test_utils import TestClient as _TestClient
import pytest


@pytest.mark.integration
async def test_get_main_page(client: _TestClient) -> None:
    """Should return OK."""
    resp = await client.get("/")
    assert resp.status == 200
    assert resp.headers[hdrs.CONTENT_TYPE] == "text/html"
    body = await resp.text()
    assert len(body) > 0


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
