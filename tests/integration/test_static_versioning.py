"""Integration test cases for versioned static URLs (cache busting).

The templates link CSS and JavaScript with url('static', filename=...),
which adds ?v=<hash of the file content> (append_version in app.py). A
changed file gets a new URL after a deploy, so browsers do not keep using
an old cached copy.
"""

import base64
import hashlib
import re
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import pytest
from aiohttp.test_utils import TestClient as _TestClient

TEMPLATES = Path("event_service_gui/templates")
STATIC = Path("event_service_gui/static")


def content_hash(filename: str) -> str:
    """The version aiohttp adds: urlsafe base64 of the SHA-256 of the file."""
    digest = hashlib.sha256((STATIC / filename).read_bytes()).digest()
    return base64.urlsafe_b64encode(digest).decode()


def static_urls(html: str) -> dict[str, str]:
    """Map file name to URL for all CSS/JS links to /static/ in a page."""
    urls = re.findall(r'(?:href|src)="(/static/[^"]+\.(?:css|js)[^"]*)"', html)
    return {urlparse(u).path.removeprefix("/static/"): u for u in urls}


@pytest.mark.integration
async def test_stylesheets_are_versioned(client: _TestClient) -> None:
    resp = await client.get("/login")
    assert resp.status == 200
    urls = static_urls(await resp.text())
    assert {"styles.css", "styles_new.css", "styles_whitelabel.css"} <= set(urls)
    for filename, url in urls.items():
        version = parse_qs(urlparse(url).query)["v"][0]
        assert unquote(version) == content_hash(filename), filename


@pytest.mark.integration
async def test_versioned_url_is_served(client: _TestClient) -> None:
    resp = await client.get("/login")
    url = static_urls(await resp.text())["styles.css"]
    resp = await client.get(url)
    assert resp.status == 200
    assert await resp.read() == (STATIC / "styles.css").read_bytes()


@pytest.mark.integration
def test_version_changes_with_content(tmp_path: Path) -> None:
    """Same content gives the same version, changed content a new one."""
    from aiohttp import web

    (tmp_path / "x.js").write_text("one")
    app = web.Application()
    resource = app.router.add_static(
        "/static/", path=str(tmp_path), name="static", append_version=True
    )
    first = str(resource.url_for(filename="x.js"))
    assert first == str(resource.url_for(filename="x.js"))
    (tmp_path / "x.js").write_text("two")
    assert str(resource.url_for(filename="x.js")) != first


@pytest.mark.integration
def test_no_unversioned_static_links_in_templates() -> None:
    """New CSS/JS links must use url('static', ...), not a fixed path."""
    pattern = re.compile(r'(?:href|src)="[^"{]*static/[^"]+\.(?:css|js)"')
    offenders = [
        f"{path.name}: {match}"
        for path in sorted(TEMPLATES.glob("*.html"))
        for match in pattern.findall(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []
